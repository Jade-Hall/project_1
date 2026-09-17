#==================================================
# 작성 목적: 로컬 LLM 멀티에이전트(Analyzer -> Solver -> Critic) 순차 실행 테스트.
# 기존 02_model_test_add.py(Local 단일 모델) / 03_cloud_api_test.py(Cloud API)와
# 같은 문항·같은 지표로 비교하기 위해 만들었다.
#
# 최종 비교 목표:
#   Local Single Model  vs  Local Multi-Agent  vs  Cloud API
#
# [주의] 이 스크립트는 기존 파일을 수정하지 않는다. questions.json도 읽기만 한다.
#==================================================

import json
import time
import traceback
from datetime import datetime
from pathlib import Path

from ollama import Client


#==================================================
# 설정 - 여기만 수정하면 된다
#==================================================

# ----- 질문 세트 선택 (이 값 하나만 바꾸면 된다) -----
#   False -> questions.json 의 cloud_test == true  (5문항, Cloud API 비교와 동일)
#   True  -> questions.json 의 local_test  == true  (10문항, Local 모델 비교와 동일)
USE_10_QUESTIONS = False

# 선택한 질문 세트를 전체적으로 몇 번 반복할지
REPEAT_COUNT = 2

# ----- 에이전트별 모델 -----
# `ollama ls` 에 나오는 "모델명:태그" 전체 이름을 그대로 입력할 것.
# 나중에 3B~4B급 양자화 모델로 교체 예정.
ANALYZER_MODEL = "model-a"
SOLVER_MODEL = "model-b"
CRITIC_MODEL = "model-c"

# ----- Ollama / 측정 설정 (01, 02번 스크립트와 동일하게 맞춤) -----
OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_TIMEOUT = 180
TEMPERATURE = 0.0          # 모델 비교 시 값을 고정해야 공정한 비교가 된다

COLD_QUESTION = "일어나라"   # 콜드 스타트용 질문 (기존 스크립트와 동일)
UNLOAD_BEFORE_START = True  # 시작 전에 떠 있는 모델을 전부 언로드할지

# 문항 세트 경로
base_dir = Path(__file__).parent
QUESTIONS_PATH = base_dir / "questions.json"

# 결과 저장 폴더 (기존: reports/test = local, reports/cloud = cloud API)
RESULT_DIR = base_dir / "reports" / "multiagent"


#==================================================
# 프롬프트 템플릿
#==================================================

ANALYZER_PROMPT_TEMPLATE = """너는 문제 분석 담당이다.

다음 질문을 분석하라.

- 사용자가 요구하는 핵심 내용
- 반드시 지켜야 하는 조건
- 출력 형식
- 계산이나 논리 추론이 필요한 경우 필요한 과정
- 주어진 정보만으로 판단할 수 없는 내용

아직 최종 답변은 작성하지 마라.

[질문]
{question}"""


SOLVER_PROMPT_TEMPLATE = """너는 문제 해결 담당이다.

[사용자 질문]
{question}

[Analyzer 분석]
{analysis}

Analyzer의 분석을 참고하되 내용을 직접 확인하여 답을 작성하라.
Analyzer의 분석이 틀렸다고 판단되면 그대로 따르지 말고 네가 직접 판단한 결과를 따르라.

사용자가 요구한 출력 형식과 조건을 반드시 지켜라.
불필요한 설명은 추가하지 마라."""


CRITIC_PROMPT_TEMPLATE = """너는 검증 담당이다.

[사용자 질문]
{question}

[Analyzer 분석]
{analysis}

[Solver 답변]
{solution}

Solver의 답변을 아래 항목에 대해 직접 독립적으로 검증하라.

- 사실 오류
- 계산 오류
- 논리 오류
- 조건 누락
- 출력 형식 위반
- 주어진 정보에 없는 내용의 임의 추측
- 질문 의도를 잘못 이해한 부분

오류가 있으면 고쳐라. 오류가 없으면 그대로 유지하라.

검토 과정, 수정한 이유, 판단 근거는 절대 출력하지 마라.
사용자 질문에 대한 최종 답변만 출력하라."""


# ollama 클라이언트 생성
client = Client(host=OLLAMA_HOST, timeout=OLLAMA_TIMEOUT)


#==================================================
# 0. 문항 세트 로드
# 질문은 새로 만들지 않고 기존 questions.json 을 그대로 사용한다.
#==================================================
with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
    all_questions = json.load(f)["questions"]

if USE_10_QUESTIONS:
    questions = [q for q in all_questions if q.get("local_test") is True]
    question_set = "10_questions"
else:
    questions = [q for q in all_questions if q.get("cloud_test") is True]
    question_set = "5_questions"

if not questions:
    raise SystemExit(
        f"[에러] {QUESTIONS_PATH} 에서 조건에 맞는 문항을 찾지 못했습니다. "
        f"(USE_10_QUESTIONS={USE_10_QUESTIONS})")

AGENT_MODELS = [ANALYZER_MODEL, SOLVER_MODEL, CRITIC_MODEL]
# 같은 모델을 여러 역할에 쓰는 경우 중복 제거 (cold 측정 / model_info 용)
UNIQUE_MODELS = list(dict.fromkeys(AGENT_MODELS))

print("=" * 70)
print("Multi-Agent Benchmark (Analyzer -> Solver -> Critic)")
print("=" * 70)
print(f"  질문 세트   : {question_set} ({len(questions)}문항) "
      f"{[q['id'] for q in questions]}")
print(f"  반복 횟수   : {REPEAT_COUNT}회  (총 {len(questions) * REPEAT_COUNT}개 테스트)")
print(f"  Analyzer    : {ANALYZER_MODEL}")
print(f"  Solver      : {SOLVER_MODEL}")
print(f"  Critic      : {CRITIC_MODEL}")
print(f"  temperature : {TEMPERATURE}")
print("=" * 70)


#==================================================
# 1~2. 현재 떠있는 모델 확인 후 전부 언로드
# (기존 01, 02번 스크립트와 동일한 절차)
#==================================================
if UNLOAD_BEFORE_START:
    running = client.ps()["models"]
    print("측정 전 로딩된 모델:", [m["model"] for m in running])
    for m in running:
        print(f"{m['model']}를 언로드합니다.")
        client.chat(model=m["model"], messages=[], keep_alive=0)
    print("언로드 후:", client.ps()["models"])


#==================================================
# 3. Cold 요청 (에이전트 모델별 순수 로딩 시간 측정)
# [참고] 모델 3개를 번갈아 쓰므로, VRAM이 부족하면 에이전트가 바뀔 때마다
#        모델이 스왑되어 load_duration 이 다시 발생할 수 있다.
#        그래서 각 요청의 load_duration 도 함께 기록한다.
#==================================================
cold_info = []
for model_name in UNIQUE_MODELS:
    try:
        cold = client.chat(model=model_name,
                           messages=[{"role": "user", "content": COLD_QUESTION}])
        entry = {
            "model": model_name,
            "cold_load_duration": cold["load_duration"] / 1e9,
            "cold_prompt_eval_duration": cold["prompt_eval_duration"] / 1e9,
            "cold_eval_duration": cold["eval_duration"] / 1e9,
            "question": COLD_QUESTION,
            "answer": cold["message"]["content"],
        }
        print(f"[Cold] {model_name}: load={entry['cold_load_duration']:.4f}s  "
              f"prompt_eval={entry['cold_prompt_eval_duration']:.4f}s  "
              f"eval={entry['cold_eval_duration']:.4f}s")
    except Exception as exc:
        entry = {"model": model_name, "error": f"{type(exc).__name__}: {exc}"}
        print(f"[Cold] {model_name}: 실패 - {entry['error']}")
    cold_info.append(entry)


#==================================================
# 4. 모델 기본 설정 확인 (에이전트 모델별)
#==================================================
def collect_model_info(model_name):
    """기존 02번 스크립트의 model_info 와 같은 항목을 수집한다."""
    info = {
        "model_name": model_name,
        "digest": None,
        "quantization_level": None,
        "max_context_length": None,
        "use_context_length": None,
        "temperature": TEMPERATURE,
    }
    try:
        for m in client.list()["models"]:
            if m["model"] == model_name:
                info["digest"] = m["digest"]
                info["quantization_level"] = m["details"]["quantization_level"]
                break

        shown = client.show(model_name)
        for key, value in shown["modelinfo"].items():
            if "context_length" in key:
                info["max_context_length"] = value
                break

        for m in client.ps()["models"]:
            if m["model"] == model_name:
                info["use_context_length"] = m["context_length"]
                break
    except Exception as exc:
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info


model_info = {}
for model_name in UNIQUE_MODELS:
    model_info[model_name] = collect_model_info(model_name)
    print(f"[model_info] {model_name}: "
          f"digest={model_info[model_name]['digest']}, "
          f"quant={model_info[model_name]['quantization_level']}, "
          f"max_ctx={model_info[model_name]['max_context_length']}, "
          f"use_ctx={model_info[model_name]['use_context_length']}")


#==================================================
# 5. Agent 호출 (기존 스크립트와 동일한 지표 계산식 사용)
#   total_time    = total_duration / 1e9
#   gen_speed     = eval_count / (eval_duration / 1e9)
#   prompt_speed  = prompt_eval_count / (prompt_eval_duration / 1e9)
#   VRAM_usage    = ps()의 size_vram / 1024**3
#==================================================
def get_vram_usage(model_name):
    try:
        for m in client.ps()["models"]:
            if m["model"] == model_name:
                return m["size_vram"] / (1024 ** 3)
    except Exception:
        pass
    return None


def call_agent(model_name, prompt):
    """
    한 Agent 를 호출하고 (응답 텍스트, 측정값) 을 돌려준다.
    예외는 호출한 쪽에서 처리한다.
    """
    wall_start = time.perf_counter()
    res = client.chat(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": TEMPERATURE},
    )
    wall_time = time.perf_counter() - wall_start

    metrics = {
        "model": model_name,
        "total_time": res["total_duration"] / 1e9,
        "gen_speed": res["eval_count"] / (res["eval_duration"] / 1e9),
        "prompt_speed": res["prompt_eval_count"] / (res["prompt_eval_duration"] / 1e9),
        "VRAM_usage": get_vram_usage(model_name),
        "load_duration": res["load_duration"] / 1e9,
        "prompt_eval_count": res["prompt_eval_count"],
        "eval_count": res["eval_count"],
        "wall_time": wall_time,
        "temperature": TEMPERATURE,
    }
    return res["message"]["content"], metrics


def run_pipeline(q):
    """
    Analyzer -> Solver -> Critic 을 반드시 순차 실행한다.
    중간 단계 출력은 최종 답변으로 덮어쓰지 않고 전부 보존한다.
    (나중에 'Solver가 틀렸는데 Critic이 고쳤는지' 등을 분석하기 위해 필요)
    """
    question = q["input_question"]

    record = {
        "id": q["id"],
        "question": question,

        # 3단계 출력 전부 보존
        "analyzer_output": None,
        "solver_output": None,
        "final_answer": None,

        # 단계별 소요 시간 (기존 total_time 과 같은 정의: total_duration 기준)
        "analyzer_time": None,
        "solver_time": None,
        "critic_time": None,
        "total_time": None,
        "wall_time": None,

        # 기존 단일 모델 결과와 같은 기준으로 채점하기 위한 항목들
        "title": q["title"],
        "difficulty": q["difficulty"],
        "category": q["category"],
        "temperature": TEMPERATURE,
        "expected_answer": q["expected_answer"],
        "evaluation_abilities": q["evaluation_abilities"],
        "content_checkpoints": q["content_checkpoints"],
        "format_criteria": q["format_criteria"],
        "obvious_wrong_criteria": q["obvious_wrong_criteria"],
        "scoring": q["scoring"],

        # 실제 채점 결과를 채워 넣을 자리
        "content_score": None,
        "format_score": None,
        "total_score": None,

        "models": {
            "analyzer": ANALYZER_MODEL,
            "solver": SOLVER_MODEL,
            "critic": CRITIC_MODEL,
        },
        "metrics": {"analyzer": None, "solver": None, "critic": None},
    }

    wall_start = time.perf_counter()

    stages = (
        ("analyzer", ANALYZER_MODEL),
        ("solver", SOLVER_MODEL),
        ("critic", CRITIC_MODEL),
    )
    analysis = None
    solution = None

    for stage, model_name in stages:
        if stage == "analyzer":
            prompt = ANALYZER_PROMPT_TEMPLATE.format(question=question)
        elif stage == "solver":
            prompt = SOLVER_PROMPT_TEMPLATE.format(question=question,
                                                   analysis=analysis)
        else:
            prompt = CRITIC_PROMPT_TEMPLATE.format(question=question,
                                                   analysis=analysis,
                                                   solution=solution)

        try:
            text, metrics = call_agent(model_name, prompt)
        except Exception as exc:
            # 한 Agent 가 실패해도 프로그램 전체를 멈추지 않는다.
            # 어느 단계에서 끊겼는지 기록하고 다음 질문으로 넘어간다.
            record["error_stage"] = stage
            record["error"] = f"{type(exc).__name__}: {exc}"
            record["traceback"] = traceback.format_exc(limit=3)
            record["wall_time"] = time.perf_counter() - wall_start
            return record

        record["metrics"][stage] = metrics
        record[f"{stage}_time"] = metrics["total_time"]

        if stage == "analyzer":
            analysis = text
            record["analyzer_output"] = text
        elif stage == "solver":
            solution = text
            record["solver_output"] = text
        else:
            record["final_answer"] = text

    record["total_time"] = (record["analyzer_time"]
                            + record["solver_time"]
                            + record["critic_time"])
    record["wall_time"] = time.perf_counter() - wall_start
    return record


#==================================================
# 6. 집계 / 저장
#==================================================
def safe_avg(values):
    vals = [v for v in values if isinstance(v, (int, float))]
    if not vals:
        return None
    return sum(vals) / len(vals)


def summarize(results):
    """기존 summary(num_questions / avg_total_time / avg_gen_speed /
    avg_prompt_speed)와 같은 형태 + 에이전트별 평균을 추가한다."""
    ok = [r for r in results if not r.get("error_stage")]

    gen_speeds, prompt_speeds, vrams = [], [], []
    for r in ok:
        for stage in ("analyzer", "solver", "critic"):
            m = r["metrics"].get(stage)
            if m:
                gen_speeds.append(m["gen_speed"])
                prompt_speeds.append(m["prompt_speed"])
                vrams.append(m["VRAM_usage"])

    return {
        "num_questions": len(results),
        "num_success": len(ok),
        "num_error": len(results) - len(ok),
        "avg_total_time": safe_avg([r["total_time"] for r in ok]),
        "avg_wall_time": safe_avg([r["wall_time"] for r in ok]),
        "avg_analyzer_time": safe_avg([r["analyzer_time"] for r in ok]),
        "avg_solver_time": safe_avg([r["solver_time"] for r in ok]),
        "avg_critic_time": safe_avg([r["critic_time"] for r in ok]),
        "avg_gen_speed": safe_avg(gen_speeds),
        "avg_prompt_speed": safe_avg(prompt_speeds),
        "avg_VRAM_usage": safe_avg(vrams),
    }


RESULT_DIR.mkdir(parents=True, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"result_multiagent_{len(questions)}q_{timestamp}.json"
result_path = RESULT_DIR / filename

result = {
    "experiment_info": {
        "question_set": question_set,
        "question_ids": [q["id"] for q in questions],
        "num_questions": len(questions),
        "repeat_count": REPEAT_COUNT,
        "analyzer_model": ANALYZER_MODEL,
        "solver_model": SOLVER_MODEL,
        "critic_model": CRITIC_MODEL,
        "temperature": TEMPERATURE,
        "pipeline": ["analyzer", "solver", "critic"],
        "ollama_host": OLLAMA_HOST,
        "questions_path": str(QUESTIONS_PATH),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "finished_at": None,
    },
    "model_info": model_info,
    "cold": cold_info,
    "runs": [],
    "summary": None,
}


def save_result():
    """중간에 멈춰도 결과가 남도록 매 문항마다 저장한다."""
    with open(result_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)


save_result()


#==================================================
# 7. 실행 - 선택한 질문 세트를 REPEAT_COUNT 회 반복
#==================================================
for repeat in range(1, REPEAT_COUNT + 1):
    print()
    print("-" * 70)
    print(f"Repeat {repeat} / {REPEAT_COUNT}")
    print("-" * 70)

    run = {"repeat": repeat, "results": [], "summary": None}
    result["runs"].append(run)

    for q in questions:
        print(f"  [{q['id']}] {q['title']}")
        try:
            record = run_pipeline(q)
        except Exception as exc:
            # 파이프라인 바깥에서 난 예외도 전체 실행을 멈추지 않는다
            record = {
                "id": q["id"],
                "question": q.get("input_question"),
                "analyzer_output": None,
                "solver_output": None,
                "final_answer": None,
                "analyzer_time": None,
                "solver_time": None,
                "critic_time": None,
                "total_time": None,
                "error_stage": "pipeline",
                "error": f"{type(exc).__name__}: {exc}",
            }

        run["results"].append(record)

        if record.get("error_stage"):
            print(f"        -> 실패 ({record['error_stage']}): {record['error']}")
        else:
            print(f"        -> 완료  A={record['analyzer_time']:.2f}s "
                  f"S={record['solver_time']:.2f}s "
                  f"C={record['critic_time']:.2f}s "
                  f"합계={record['total_time']:.2f}s")

        run["summary"] = summarize(run["results"])
        save_result()

    run["summary"] = summarize(run["results"])
    save_result()


#==================================================
# 8. 최종 저장
#==================================================
all_results = [r for run in result["runs"] for r in run["results"]]
result["summary"] = summarize(all_results)
result["experiment_info"]["finished_at"] = datetime.now().isoformat(timespec="seconds")
save_result()

total = result["summary"]
print()
print("=" * 70)
print(f"완료: 총 {total['num_questions']}개 테스트 "
      f"(성공 {total['num_success']} / 실패 {total['num_error']})")
if total["avg_total_time"] is not None:
    print(f"평균 total_time: {total['avg_total_time']:.4f}s  "
          f"(A={total['avg_analyzer_time']:.4f} "
          f"S={total['avg_solver_time']:.4f} "
          f"C={total['avg_critic_time']:.4f})")
    print(f"평균 gen_speed   : {total['avg_gen_speed']:.2f} tok/s")
    print(f"평균 prompt_speed: {total['avg_prompt_speed']:.2f} tok/s")
print(f"결과 저장 완료: {result_path}")
print("=" * 70)

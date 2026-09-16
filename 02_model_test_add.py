#==================================================
# 작성 목적: 선정한 모델의 테스트 진행 및 비교 목적
# (기존 단일 문항 테스트 스크립트를 questions.json의 10개 문항으로 확장)
#==================================================

import json, re
from pathlib import Path

from ollama import Client

# report를 저장하고자 하는 파일 경로
base_dir = Path(__file__).parent

# 본인이 테스트하고자 하는 모델 코드 입력
MODEL = "exaone3.5:latest"

# 콜드 스타트용 질문
COLD_QUESTION = "일어나라"

# 테스트 문항 세트 (2번 자료)
QUESTIONS_PATH = base_dir / "questions.json"

# 이번 테스트에서 사용할 temperature (모델 비교 시 값을 고정해야 공정한 비교가 됨)
TEMPERATURE = 0.7

# ollama 클라이언트 생성
client = Client(host="http://127.0.0.1:11434", timeout=180)


#==================================================
# 0. 문항 세트 로드
#==================================================
with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
    questions = json.load(f)["questions"]


#==================================================
# 1. 현재 떠있는 모델 확인
# [중요] "모델명:태크" 까지 붙여서 사용할 것
#==================================================
running = client.ps()["models"]
print("측정 전 로딩된 모델:", [m["model"] for m in running])


#==================================================
# 2. 전부 언로드
# 모델을 먼저 실행시켜도 전부 죽이고 시작
#==================================================
for m in running:
    print(f"{m['model']}를 언로드합니다.")
    client.chat(model=m["model"], messages=[], keep_alive=0)

# 언로드 확인
print("언로드 후:", client.ps()["models"])


#==================================================
# 3. Cold 요청 (순수 로딩 시간 측정)
# cold_load_duration - 최초 모델 로드 속도
# cold_prompt_eval_duration - 최초 질문에 대한 프롬프트 처리 속도
# cold_eval_duration - 최초 질문에 대한 전체 처리 속도
#==================================================
cold = client.chat(model=MODEL, messages=[{"role": "user", "content": COLD_QUESTION}])
cold_load_duration = cold["load_duration"] / 1e9
cold_prompt_eval_duration = cold["prompt_eval_duration"] / 1e9
cold_eval_duration = cold["eval_duration"] / 1e9
print("[Cold] load_duration(초):", cold_load_duration)
print("[Cold] prompt_eval_duration(초):", cold_prompt_eval_duration)
print("[Cold] eval_duration(초):", cold_eval_duration)


#==================================================
# 4. 모델 기본 설정 확인
# digest - 테스트 대상 모델의 digest값
# quantization_level - 테스트 대상 모델의 양자화 수준
# max_context_length - 모델의 최대 컨텍스트 길이
# use_context_length - 실제로 테스트 시에 사용하는 컨텍스트 길이
#==================================================
digest = None
quantization_level = None
for m in client.list()["models"]:
    if m["model"] == MODEL:
        digest = m["digest"]
        quantization_level = m["details"]["quantization_level"]
        print("측정 모델의 digest:", digest)
        print("측정 모델의 양자화 수준:", quantization_level)

# 모델의 최대 컨텍스트 길이 확인
max_context_length = None
info = client.show(MODEL)
for key, value in info["modelinfo"].items():
    if "context_length" in key:
        max_context_length = value
        print("모델의 최대 컨텍스트 길이:", max_context_length)

# 실제 로딩된 모델의 context_length
use_context_length = None
for m in client.ps()["models"]:
    if m["model"] == MODEL:
        use_context_length = m["context_length"]
        print("실행 중 context_length:", use_context_length)


#==================================================
# 5. Warm 요청 - questions.json의 각 문항을 순서대로 실행
# 문항마다: total_time, gen_speed, prompt_speed, VRAM_usage 를 측정하고
# 채점에 필요한 정답/체크포인트 정보도 결과에 함께 저장한다.
#==================================================
warm_results = []

for q in questions:
    warm = client.chat(
        model=MODEL,
        messages=[{"role": "user", "content": q["input_question"]}],
        options={"temperature": TEMPERATURE},
    )

    total_time = warm["total_duration"] / 1e9
    gen_speed = warm["eval_count"] / (warm["eval_duration"] / 1e9)
    prompt_speed = warm["prompt_eval_count"] / (warm["prompt_eval_duration"] / 1e9)

    vram_usage = None
    for m in client.ps()["models"]:
        if m["model"] == MODEL:
            vram_usage = m["size_vram"] / (1024**3)

    print(f"[{q['id']}] total_time={total_time:.4f}s  gen_speed={gen_speed:.2f} tok/s  "
          f"prompt_speed={prompt_speed:.2f} tok/s  VRAM={vram_usage:.2f} GB  temperature={TEMPERATURE}")

    warm_results.append({
        "id": q["id"],
        "title": q["title"],
        "difficulty": q["difficulty"],
        "category": q["category"],
        "question": q["input_question"],
        "answer": warm["message"]["content"],
        "total_time": total_time,
        "gen_speed": gen_speed,
        "prompt_speed": prompt_speed,
        "VRAM_usage": vram_usage,
        "temperature": TEMPERATURE,
        "expected_answer": q["expected_answer"],
        "evaluation_abilities": q["evaluation_abilities"],
        "content_checkpoints": q["content_checkpoints"],
        "format_criteria": q["format_criteria"],
        "obvious_wrong_criteria": q["obvious_wrong_criteria"],
        "scoring": q["scoring"],
        # 실제 채점 결과를 채워 넣을 자리 (수동 또는 별도 평가 스크립트로 채점 후 기입)
        "content_score": None,
        "format_score": None,
        "total_score": None,
    })


#==================================================
# 6. 전체 테스트 결과 JSON으로 저장
#==================================================
result = {
    "model_info": {
        "model_name": MODEL,
        "digest": digest,
        "quantization_level": quantization_level,
        "max_context_length": max_context_length,
        "use_context_length": use_context_length,
        "temperature": TEMPERATURE,
    },
    "cold": {
        "cold_load_duration": cold_load_duration,
        "cold_prompt_eval_duration": cold_prompt_eval_duration,
        "cold_eval_duration": cold_eval_duration,
        "question": COLD_QUESTION,
        "answer": cold["message"]["content"]
    },
    "warm_results": warm_results,
    "summary": {
        "num_questions": len(warm_results),
        "avg_total_time": sum(w["total_time"] for w in warm_results) / len(warm_results),
        "avg_gen_speed": sum(w["gen_speed"] for w in warm_results) / len(warm_results),
        "avg_prompt_speed": sum(w["prompt_speed"] for w in warm_results) / len(warm_results),
    }
}

safe_model_name = re.sub(r'[:/\\]', '_', MODEL)
filename = f"result_{safe_model_name}_{quantization_level}.json"
test_result_dir = base_dir / "reports" / "test"
test_result_dir.mkdir(parents=True, exist_ok=True)

with open(test_result_dir / filename, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"결과 저장 완료: {filename}")
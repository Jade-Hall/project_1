#==================================================
# 작성 목적: STEP 7 (Local LLM vs Cloud API 비교)의 Cloud API 측
# 로컬 ollama 스크립트(02_luna_chat.py 계열)와 동일한 골격으로,
# questions.json 중 "cloud_test": true 인 문항만 상용 API(OpenAI 기본)에
# 실행하고 동일한 형태의 결과 JSON을 만든다.
# (요청에 따라 cold 요청 단계는 생략하고, warm 문항만 바로 실행한다.)
#
# 로컬(Ollama)과 다른 점 (그래서 그대로 옮길 수 없는 부분):
#   - Cloud API는 "모델 언로드/재로딩" 개념이 없다 (상시 서비스형).
#   - Cloud API는 load_duration / prompt_eval_duration / eval_duration을
#     응답에 내려주지 않는다. 대신 스트리밍으로 직접 시간을 측정해
#     TTFT(첫 토큰까지 걸린 시간)를 "prompt 처리 + 네트워크" 구간의
#     근사치로, 그 이후 구간을 "생성" 구간의 근사치로 사용한다.
#     -> 정확한 서버 내부 처리 시간이 아니라 "체감 응답 속도" 근사치이니,
#        로컬 결과와 절대값으로 1:1 비교할 때는 이 차이를 감안할 것.
#   - VRAM/양자화/컨텍스트 길이 같은 하드웨어성 지표 대신,
#     토큰 사용량(prompt/completion) 및 그에 따른 "예상 비용(원가)"을 기록한다.
#     (STEP 7 요구사항: "추정 비용과 OpenAI API 사용량의 실제 사용 내역을 구분")
#
# 사용법 (PowerShell 기준):
#   1) questions.json을 questions 폴더에 둔다.
#   2) API 키를 환경변수로 설정한다 (코드/로그/스크린샷에 키가 남지 않도록,
#      코드 안에 직접 쓰지 않는다). 변수 이름은 반드시 OPENAI_API_KEY여야 하며,
#      OPEN_API_KEY처럼 철자가 하나라도 다르면 "설정 안 된 것"으로 인식한다.
#      따옴표도 앞뒤로 꼭 닫아줄 것.
#        PowerShell:  $env:OPENAI_API_KEY="sk-실제키"
#        cmd:         set OPENAI_API_KEY=sk-실제키
#        Mac/Linux:   export OPENAI_API_KEY="sk-실제키"
#   3) 제대로 설정됐는지 확인한다 (실제 키 값이 출력되어야 정상이고,
#      비어있거나 아무것도 안 나오면 아직 설정이 안 된 것).
#        PowerShell:  echo $env:OPENAI_API_KEY
#        cmd:         echo %OPENAI_API_KEY%
#        Mac/Linux:   echo $OPENAI_API_KEY
#   4) 키 확인이 끝났으면 같은 터미널 창에서 바로 이어서 실행한다.
#      (터미널 창을 새로 열면 환경변수가 사라지므로 2)부터 다시 설정해야 함)
#        uv run --with openai python 03_cloud_api_test.py
#      uv 대신 pip을 쓴다면: pip install openai (필요시 --break-system-packages)
#      후 python 03_cloud_api_test.py
#      (다른 provider로 바꾸고 싶으면 아래 "설정" 영역만 수정하면 됨)
#==================================================

import json
import os
import re
import time
from pathlib import Path

from openai import OpenAI, BadRequestError

# report를 저장하고자 하는 파일 경로 (스크립트와 같은 폴더 기준)
base_dir = Path(__file__).parent


#==================================================
# 설정 (여기만 바꾸면 다른 모델/다른 OpenAI 호환 API로 전환 가능)
#==================================================

# 본인이 테스트하고자 하는 모델 코드 입력
# 참고 (2026-09 기준, 반드시 https://platform.openai.com/docs/pricing 에서 최신값 재확인할 것):
#   - "gpt-4o-mini"   : 안정적인 구세대 저비용 모델. Chat Completions에서 temperature 등 표준 파라미터 사용 가능.
#   - "gpt-5.6-luna"  : 2026-09 기준 최신 저비용 라인업(reasoning 계열). reasoning 모델 특성상
#                       temperature 대신 reasoning_effort 등 별도 파라미터를 쓰거나, Chat Completions
#                       호환성이 제한적일 수 있으니 사용 전 공식 문서로 확인 권장.
MODEL = "gpt-5.6-luna"

# 모델별 1M 토큰당 가격 (달러, input/output). MODEL을 바꾸면 이 값도 함께 맞춰줄 것.
# 출처: OpenAI 공식 요금 페이지(https://platform.openai.com/docs/pricing) 확인 시점 2026-09.
PRICING_PER_1M_USD = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-5.6-luna": {"input": 0.20, "output": 1.20},
}
PRICE_INPUT_PER_1M = PRICING_PER_1M_USD.get(MODEL, {}).get("input")
PRICE_OUTPUT_PER_1M = PRICING_PER_1M_USD.get(MODEL, {}).get("output")

# 모델별 컨텍스트 길이 참고값 (API가 직접 내려주지 않으므로 수동 기재; 필요시 갱신)
MODEL_CONTEXT_INFO = {
    "gpt-4o-mini": {"max_context_length": 128_000, "max_output_tokens": 16_384},
    "gpt-4o": {"max_context_length": 128_000, "max_output_tokens": 16_384},
    "gpt-5.6-luna": {"max_context_length": 1_050_000, "max_output_tokens": 128_000},
}

# 테스트 문항 세트 (STEP 7 자료, 로컬 스크립트와 동일 파일 공유)
QUESTIONS_PATH = base_dir / "questions" / "questions.json"

# 이번 테스트에서만 실행할 문항 필터 (요청사항: cloud_test == true 인 것만)
RUN_ONLY_CLOUD_TEST = True

# 이번 테스트에서 사용할 temperature (모델 비교 시 값을 고정해야 공정한 비교가 됨)
TEMPERATURE = 0.0

# API 키는 코드에 직접 쓰지 않고 환경변수에서 읽는다.
#   export OPENAI_API_KEY="sk-..."
API_KEY = os.environ.get("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError(
        "환경변수 OPENAI_API_KEY가 설정되어 있지 않습니다. "
        "예) export OPENAI_API_KEY=sk-... 를 먼저 실행한 뒤 다시 실행하세요."
    )

# OpenAI 호환 엔드포인트를 쓰고 싶으면(Azure OpenAI, 다른 벤더 등) 환경변수로 base_url을 넘길 수 있음
BASE_URL = os.environ.get("OPENAI_BASE_URL") or None

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


#==================================================
# 유틸: 스트리밍 채팅 요청 1회를 보내고,
#   - answer: 전체 응답 텍스트
#   - ttft: 첫 토큰(첫 delta)까지 걸린 시간(초) - "prompt 처리 + 네트워크"의 근사치
#   - total_time: 요청 시작~완료까지 전체 시간(초)
#   - prompt_tokens / completion_tokens: 사용량
# 을 반환한다.
#==================================================
def run_streaming_chat(model: str, question: str, temperature: float):
    start = time.perf_counter()
    ttft = None
    chunks = []
    usage = None
    temperature_used = temperature

    def _create_stream(with_temperature: bool):
        kwargs = dict(
            model=model,
            messages=[{"role": "user", "content": question}],
            stream=True,
            stream_options={"include_usage": True},
        )
        if with_temperature:
            kwargs["temperature"] = temperature
        return client.chat.completions.create(**kwargs)

    try:
        stream = _create_stream(with_temperature=True)
    except BadRequestError as e:
        # 일부 모델(예: gpt-5.6 계열 reasoning 모델)은 temperature를 직접 지정하는 것을
        # 지원하지 않고 모델 기본값(보통 1)만 허용한다. 이 경우 temperature 없이 재시도한다.
        if "temperature" in str(e) and "unsupported_value" in str(e):
            print(f"⚠️  '{model}' 모델은 temperature={temperature} 지정을 지원하지 않아, "
                  f"모델 기본 temperature로 재요청합니다. (다른 모델과 비교 시 이 차이를 감안할 것)")
            temperature_used = None  # 모델 기본값이 적용됨 (정확한 값은 API가 알려주지 않음)
            stream = _create_stream(with_temperature=False)
        else:
            raise

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            if ttft is None:
                ttft = time.perf_counter() - start
            chunks.append(chunk.choices[0].delta.content)
        if getattr(chunk, "usage", None):
            usage = chunk.usage

    end = time.perf_counter()
    total_time = end - start
    if ttft is None:
        # 토큰을 하나도 못 받은 예외적인 경우 방지용 fallback
        ttft = total_time

    answer = "".join(chunks)
    prompt_tokens = usage.prompt_tokens if usage else None
    completion_tokens = usage.completion_tokens if usage else None

    return {
        "answer": answer,
        "ttft": ttft,
        "total_time": total_time,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "temperature_used": temperature_used,
    }


def estimate_cost_usd(prompt_tokens, completion_tokens):
    if prompt_tokens is None or completion_tokens is None:
        return None
    if PRICE_INPUT_PER_1M is None or PRICE_OUTPUT_PER_1M is None:
        return None
    return (prompt_tokens / 1_000_000) * PRICE_INPUT_PER_1M + \
           (completion_tokens / 1_000_000) * PRICE_OUTPUT_PER_1M


#==================================================
# 0. 문항 세트 로드 (cloud_test: true 인 것만 사용)
#==================================================
with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
    all_questions = json.load(f)["questions"]

if RUN_ONLY_CLOUD_TEST:
    questions = [q for q in all_questions if q.get("cloud_test") is True]
else:
    questions = all_questions

print(f"전체 문항 {len(all_questions)}개 중 cloud_test=true 문항 {len(questions)}개를 실행합니다.")
print("실행 대상 id:", [q["id"] for q in questions])


#==================================================
# 1. 모델 기본 설정 확인
# (로컬처럼 digest/양자화는 없으므로 "N/A (Cloud API)"로 표시)
#==================================================
digest = "N/A (Cloud API)"
quantization_level = "N/A (Cloud API)"
max_context_length = MODEL_CONTEXT_INFO.get(MODEL, {}).get("max_context_length")
max_output_tokens = MODEL_CONTEXT_INFO.get(MODEL, {}).get("max_output_tokens")
print("측정 모델:", MODEL)
print("모델의 최대 컨텍스트 길이(수동 기재값):", max_context_length)
print("모델의 최대 출력 토큰(수동 기재값):", max_output_tokens)
if PRICE_INPUT_PER_1M is None:
    print("⚠️ PRICING_PER_1M_USD에 이 모델의 가격이 없습니다. 비용은 계산되지 않습니다. "
          "스크립트 상단의 PRICING_PER_1M_USD를 채워주세요.")


#==================================================
# 2. Warm 요청 - questions.json에서 cloud_test=true인 문항을 순서대로 실행
# 문항마다: total_time, gen_speed, prompt_speed, cost_usd 를 측정하고
# 채점에 필요한 정답/체크포인트 정보도 결과에 함께 저장한다.
#==================================================
warm_results = []

for q in questions:
    warm = run_streaming_chat(MODEL, q["input_question"], TEMPERATURE)

    total_time = warm["total_time"]
    ttft = warm["ttft"]
    gen_duration = max(total_time - ttft, 0.0)

    prompt_tokens = warm["prompt_tokens"]
    completion_tokens = warm["completion_tokens"]

    gen_speed = (completion_tokens / gen_duration) if (completion_tokens and gen_duration > 0) else None
    # prompt_speed는 "네트워크 왕복 + 프롬프트 처리"를 합친 시간 기준의 근사치임 (실제 서버 내부 prompt eval 속도는 아님)
    prompt_speed = (prompt_tokens / ttft) if (prompt_tokens and ttft > 0) else None

    cost_usd = estimate_cost_usd(prompt_tokens, completion_tokens)
    temperature_used = warm["temperature_used"]

    print(f"[{q['id']}] total_time={total_time:.4f}s  ttft={ttft:.4f}s  "
          f"gen_speed={gen_speed if gen_speed is None else f'{gen_speed:.2f}'} tok/s  "
          f"prompt_speed={prompt_speed if prompt_speed is None else f'{prompt_speed:.2f}'} tok/s  "
          f"cost=${cost_usd if cost_usd is None else f'{cost_usd:.6f}'}  "
          f"temperature={'모델 기본값(고정 불가)' if temperature_used is None else temperature_used}")

    warm_results.append({
        "id": q["id"],
        "title": q["title"],
        "difficulty": q["difficulty"],
        "category": q["category"],
        "question": q["input_question"],
        "answer": warm["answer"],
        "total_time": total_time,
        "ttft": ttft,
        "gen_duration": gen_duration,
        "gen_speed": gen_speed,
        "prompt_speed": prompt_speed,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_usd": cost_usd,
        "temperature_requested": TEMPERATURE,
        "temperature_used": temperature_used,
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
# 3. 전체 테스트 결과 JSON으로 저장
#==================================================
def safe_avg(values):
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


result = {
    "model_info": {
        "provider": "openai",
        "model_name": MODEL,
        "digest": digest,
        "quantization_level": quantization_level,
        "max_context_length": max_context_length,
        "max_output_tokens": max_output_tokens,
        "temperature_requested": TEMPERATURE,
        "price_input_per_1m_usd": PRICE_INPUT_PER_1M,
        "price_output_per_1m_usd": PRICE_OUTPUT_PER_1M,
    },
    "warm_results": warm_results,
    "summary": {
        "num_questions": len(warm_results),
        "avg_total_time": safe_avg([w["total_time"] for w in warm_results]),
        "avg_gen_speed": safe_avg([w["gen_speed"] for w in warm_results]),
        "avg_prompt_speed": safe_avg([w["prompt_speed"] for w in warm_results]),
        "total_cost_usd": safe_avg([w["cost_usd"] for w in warm_results]) * len(warm_results)
            if all(w["cost_usd"] is not None for w in warm_results) and warm_results else None,
        "avg_cost_usd": safe_avg([w["cost_usd"] for w in warm_results]),
    }
}

safe_model_name = re.sub(r'[:/\\.]', '_', MODEL)
filename = f"result_{safe_model_name}_cloud.json"
test_result_dir = base_dir / "reports" / "cloud"
test_result_dir.mkdir(parents=True, exist_ok=True)

with open(test_result_dir / filename, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"결과 저장 완료: {filename}")
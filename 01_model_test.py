#==================================================
# 작성자: 송찬영
# 작성일: 2026.09.14
# 작성 목적: 선정한 모델의 테스트 진행 및 비교 목적으로 작성하였다.
# 이후의 코드들의 베이스로 사용될 수 있다.
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
# 예시 질문 1개
QUESTION = "프랑스의 수도는 어디인가요? 도시 이름만 한국어로 쓰고, 설명이나 문장부호는 붙이지 마세요."


METRIC_DESCRIPTIONS = {
    "digest": "모델 가중치의 SHA-256 해시값. 동일 이름이라도 내용이 바뀌면 달라짐 (버전 식별용)",
    "quantization_level": "양자화 수준 (예: F16=비양자화, Q4_K_M, Q8_0 등)",
    "max_context_length": "모델 카드/설정상 지원하는 최대 컨텍스트 길이 (토큰)",
    "use_context_length": "실제 로딩 시 적용된 컨텍스트 길이 (Modelfile의 num_ctx 값)",
    "cold_load_duration": "모델을 처음 메모리에 올리는 데 걸린 시간 (초). 완전 언로드 상태에서 측정",
    "cold_prompt_eval_duration": "최초 요청에서 입력 프롬프트를 처리(prefill)하는 데 걸린 시간 (초)",
    "cold_eval_duration": "최초 요청에서 응답 토큰을 생성(decode)하는 데 걸린 시간 (초)",
    "total_time": "Warm 상태에서 요청부터 응답 완료까지 전체 소요 시간 (초). load_duration은 거의 0에 가까움",
    "gen_speed": "Warm 상태의 토큰 생성 속도 (tokens/sec) = eval_count / eval_duration",
    "prompt_speed": "Warm 상태의 프롬프트 처리 속도 (tokens/sec) = prompt_eval_count / prompt_eval_duration. 단, 이전 요청과 프롬프트가 동일하면 캐시로 인해 왜곡될 수 있음",
    "vram_usage": "Warm 요청 직후 ollama.ps()가 보고한 VRAM 점유량 (GB). 모델 가중치+KV캐시 추정치",
}

# ollama 클라이언트 생성
client = Client(host="http://127.0.0.1:11434", timeout=180)

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
# cold_eval_duration: - 최초 질문에 대한 전체 처리 속도
# ==================================================
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
# 5. Warm 요청 (각종 지표를 확인하는 부분)
# total_time - 전체 응답 시간
# gen_speed - 토큰 생성 속도
# prompt_speed - 프롬프트 처리 속도
# VRAM_usage - VRAM 사용량
#==================================================
warm = client.chat(model=MODEL, messages=[{"role": "user", "content": QUESTION}])

# 전체 응답 시간
total_time = warm["total_duration"] / 1e9
# 토큰 생성 속도
gen_speed = warm["eval_count"] / (warm["eval_duration"] / 1e9)
# 프롬프트 처리 속도
prompt_speed = warm["prompt_eval_count"] / (warm["prompt_eval_duration"] / 1e9)
print("전체 응답 시간:", total_time, "sec")
print("토큰 생성 속도:", gen_speed, "tok/s")
print("프롬프트 처리 속도:", prompt_speed, "tok/s")

# 모델의 VRAM 사용량 계산
vram_usage = None
for m in client.ps()["models"]:
    if m["model"] == MODEL:
        vram_usage = m["size_vram"] / (1024**3)
        print(f"[warm 이후] VRAM 사용량: {vram_usage:.2f} GB")


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
    },
    "cold": {
        "cold_load_duration": cold_load_duration,
        "cold_prompt_eval_duration": cold_prompt_eval_duration,
        "cold_eval_duration": cold_eval_duration,
        "question": COLD_QUESTION,
        "answer": cold["message"]["content"]
    },
    "warm": {
        "total_time": total_time,
        "gen_speed": gen_speed,
        "prompt_speed": prompt_speed,
        "VRAM_usage": vram_usage,
        "question": QUESTION,
        "answer": warm["message"]["content"]
    }
}

safe_model_name = re.sub(r'[:/\\]', '_', MODEL)
filename = f"result_{safe_model_name}_{quantization_level}.json"
test_result_dir = base_dir / "reports" / "test"
test_result_dir.mkdir(parents=True, exist_ok=True)

with open(test_result_dir/filename, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"결과 저장 완료: {filename}")
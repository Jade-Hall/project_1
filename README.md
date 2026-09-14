# Project1 - 집현전

## Quick Start

1. **터미널 → 새 터미널**에서 PowerShell을 엽니다. Ollama 앱도 실행합니다.
2. 아래 명령을 한 줄씩 입력합니다. `.venv`를 직접 활성화하지 않아도 됩니다.

```powershell
uv sync
uv run python --version
```

Python `3.12.x`가 나오면 준비됐습니다. 최초 실행에는 Python과 패키지 다운로드가 필요할 수 있습니다.

## 파일 실행

### `01_model_test.py`

#### 실행 전 유의 사항
`ollama ls`를 통해서 나오는 모델의 태그를 포함한 전체 이름을 `MODEL`에 입력해야 합니다.

**예시**

```commandline
C:\Users\xxxxx\Documents\kanana\kanana-1.5-8b-base>ollama ls
NAME                             ID              SIZE      MODIFIED
kanana-1.5-8b-full:latest        4997c7cee514    16 GB     2 hours ago
kanana-1.5-8b-q8:latest          0112116bbd53    8.5 GB    3 hours ago
kanana-1.5-8b-q4:latest          ce1614ddb0be    5.0 GB    5 hours ago
gemma3:4b                        a2af6cc3eb7f    3.3 GB    5 days ago
qwen3:4b-instruct-2507-q4_K_M    0edcdef34593    2.5 GB    5 days ago
```
이런 경우에 가장 위의 모델을 실행하고자 한다면 `kanana-1.5-8b-full:latest`를 입력해야 합니다.

파일 실행 명령
```python
uv run python .\01_model_test.py
```

실행 결과 파일: `/reports/test/result_{모델명:태그}_{양자화 수준}.json`

#### 측정한 정량 평가 지표
"digest": "모델 가중치의 SHA-256 해시값. 동일 이름이라도 내용이 바뀌면 달라짐 (버전 식별용)"
"quantization_level": "양자화 수준 (예: F16=비양자화, Q4_K_M, Q8_0 등)"
"max_context_length": "모델 카드/설정상 지원하는 최대 컨텍스트 길이 (토큰)"
"use_context_length": "실제 로딩 시 적용된 컨텍스트 길이 (Modelfile의 num_ctx 값)"
"cold_load_duration": "모델을 처음 메모리에 올리는 데 걸린 시간 (초). 완전 언로드 상태에서 측정"
"cold_prompt_eval_duration": "최초 요청에서 입력 프롬프트를 처리(prefill)하는 데 걸린 시간 (초)"
"cold_eval_duration": "최초 요청에서 응답 토큰을 생성(decode)하는 데 걸린 시간 (초)"
"total_time": "Warm 상태에서 요청부터 응답 완료까지 전체 소요 시간 (초). load_duration은 거의 0에 가까움"
"gen_speed": "Warm 상태의 토큰 생성 속도 (tokens/sec) = eval_count / eval_duration"
"prompt_speed": "Warm 상태의 프롬프트 처리 속도 (tokens/sec) = prompt_eval_count / prompt_eval_duration. 단, 이전 요청과 프롬프트가 동일하면 캐시로 인해 왜곡될 수 있음"
"vram_usage": "Warm 요청 직후 ollama.ps()가 보고한 VRAM 점유량 (GB). 모델 가중치+KV캐시 추정치"
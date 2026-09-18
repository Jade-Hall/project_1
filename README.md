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

### `02_model_test_add.py`

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
uv run python .\02_model_test_add.py
```

실행 결과 파일: `/reports/test/result_{모델명:태그}_{양자화 수준}.json`

### `03_cloud_api_test.py`

파일 실행 명령(PowerShell 기준):

   1) questions.json을 questions 폴더에 둔다.
   2) API 키를 환경변수로 설정한다 (코드/로그/스크린샷에 키가 남지 않도록,
      코드 안에 직접 쓰지 않는다). 변수 이름은 반드시 OPENAI_API_KEY여야 하며,
      OPEN_API_KEY처럼 철자가 하나라도 다르면 "설정 안 된 것"으로 인식한다.
      따옴표도 앞뒤로 꼭 닫아줄 것.
        ```
        PowerShell:  $env:OPENAI_API_KEY="sk-실제키"
        cmd:         set OPENAI_API_KEY=sk-실제키
        Mac/Linux:   export OPENAI_API_KEY="sk-실제키"
        ```
   3) 제대로 설정됐는지 확인한다 (실제 키 값이 출력되어야 정상이고,
      비어있거나 아무것도 안 나오면 아직 설정이 안 된 것).
        ```
        PowerShell:  echo $env:OPENAI_API_KEY
        cmd:         echo %OPENAI_API_KEY%
        Mac/Linux:   echo $OPENAI_API_KEY
        ```
   4) 키 확인이 끝났으면 같은 터미널 창에서 바로 이어서 실행한다.
      (터미널 창을 새로 열면 환경변수가 사라지므로 2)부터 다시 설정해야 함)
      ```
      uv run --with openai python 03_cloud_api_test.py
      uv 대신 pip을 쓴다면: pip install openai (필요시 --break-system-packages)
      후 python 03_cloud_api_test.py
      (다른 provider로 바꾸고 싶으면 아래 "설정" 영역만 수정하면 됨)
      ```

실행 결과 파일: `/reports/cloud/result_{모델명:태그}_cloud.json`


#### 질문지 답변 자료 위치
1. 로컬모델의 질문지 답변: results/local
2. 클라우드모델의 질문지 답변: results/cloud
3. (심화) 멀티모달, 클라우드 답변: results/avd

#### 문서 자료 위치
1. 평가지표: doc/metric
2. 로컬 1차 테스트: doc/local_test_1 
3. 로컬 2차 테스트: doc/local_test_2
4. 로컬-클라우드 테스트: docs/local_cloud_test
5. (심화) 멀티에이전트-클라우드 테스트: docs/adv_test
# LLM 모델 성능 비교

## 테스트 조건

| 항목 | 값 |
| --- | --- |
| 테스트 문항 수 | 10 |
| 모델별 반복 횟수 | 2 |
| Temperature | 0.0 |
| Context Length | 8192 |

모든 실행이 동일한 문항 세트를 사용했습니다.

## 모델별 종합 성능

| 모델 | Precision | Cold Load (s) | Avg Total Time (s) | Gen Speed (tok/s) | Prompt Speed (tok/s) | VRAM (GB) |
| --- | --- | --- | --- | --- | --- | --- |
| Llama 3.1 8B | F16 | 13.014 | 6.382 | 7.14 | 179.24 | 5.55 |
| Kanana 1.5 8B | F16 | 11.878 | 20.534 | 6.54 | 190.59 | 5.56 |
| EXAONE 7.8B | BF16 | 10.713 | 13.203 | 7.04 | 167.77 | 5.79 |

모든 값은 각 모델의 2회 실행 평균입니다.

### VRAM 값 산출 방식

- **Llama 3.1 8B**: 상수값 (문항 20개 전부 동일, 최소=최대) → 5.55 GB
- **Kanana 1.5 8B**: 상수값 (문항 20개 전부 동일, 최소=최대) → 5.56 GB
- **EXAONE 7.8B**: 상수값 (문항 20개 전부 동일, 최소=최대) → 5.79 GB

## 모델별 1차 / 2차 결과

| 모델 | Run | Cold Load (s) | Avg Total Time (s) | Avg Gen Speed (tok/s) | Avg Prompt Speed (tok/s) | 원본 파일 |
| --- | --- | --- | --- | --- | --- | --- |
| Llama 3.1 8B | 1 | 12.997 | 6.389 | 7.13 | 180.85 | result_llama3.1_8b-instruct-fp16_F16_1.json |
| Llama 3.1 8B | 2 | 13.030 | 6.374 | 7.14 | 177.63 | result_llama3.1_8b-instruct-fp16_F16_2.json |
| Kanana 1.5 8B | 1 | 11.740 | 19.993 | 6.78 | 190.02 | result_kanana-1.5-8b-full_latest_F16_1.json |
| Kanana 1.5 8B | 2 | 12.016 | 21.076 | 6.30 | 191.16 | result_kanana-1.5-8b-full_latest_F16_2.json |
| EXAONE 7.8B | 1 | 10.749 | 13.394 | 7.01 | 163.33 | result_exaone-7.8b-full_latest_BF16_1.json |
| EXAONE 7.8B | 2 | 10.676 | 13.011 | 7.08 | 172.21 | result_exaone-7.8b-full_latest_BF16_2.json |

## 성능 특성 요약

### Cold Load (모델 최초 적재)

- EXAONE 7.8B 10.713 / Kanana 1.5 8B 11.878 / Llama 3.1 8B 13.014 (s)
    - 가장 낮음: **EXAONE 7.8B** — 최하위 Llama 3.1 8B 대비 2.301 s 차이 (21.5%)

### 생성 속도 (Gen Speed)

- Llama 3.1 8B 7.14 / EXAONE 7.8B 7.04 / Kanana 1.5 8B 6.54 (tok/s)
    - 가장 높음: **Llama 3.1 8B** — 최하위 Kanana 1.5 8B 대비 0.60 tok/s 차이 (8.3%)

### 프롬프트 처리 속도 (Prompt Speed)

- Kanana 1.5 8B 190.59 / Llama 3.1 8B 179.24 / EXAONE 7.8B 167.77 (tok/s)
    - 가장 높음: **Kanana 1.5 8B** — 최하위 EXAONE 7.8B 대비 22.82 tok/s 차이 (12.0%)

### VRAM 사용량

- Llama 3.1 8B 5.55 / Kanana 1.5 8B 5.56 / EXAONE 7.8B 5.79 (GB)
    - 가장 낮음: **Llama 3.1 8B** — 최하위 EXAONE 7.8B 대비 0.24 GB 차이 (4.3%)

### 1차 / 2차 측정값의 변동 정도

변동률 = (최댓값 − 최솟값) ÷ 2회 평균 × 100

| 모델 | Cold Load | Avg Total Time | Gen Speed | Prompt Speed |
| --- | --- | --- | --- | --- |
| Llama 3.1 8B | 0.25% | 0.22% | 0.16% | 1.80% |
| Kanana 1.5 8B | 2.32% | 5.28% | 7.31% | 0.60% |
| EXAONE 7.8B | 0.68% | 2.90% | 0.94% | 5.29% |
- 재현성이 가장 좋은 쪽은 **Llama 3.1 8B** (최대 변동 1.80%)입니다.
- 변동이 가장 큰 쪽은 **Kanana 1.5 8B** (최대 변동 7.31%)이므로, 이 모델의 수치는 2회 평균만으로 단정하기 어렵습니다.

### Avg Total Time 해석 시 주의

`avg_total_time` 은 요청부터 응답 완료까지의 전체 시간이므로 **모델이 답변을 얼마나 길게 생성했는지**에 직접 영향을 받습니다. 같은 속도로 생성하더라도 출력이 길면 total_time 은 그만큼 커집니다.

- `avg_total_time` 은 모델 간 **3.22배** 차이 (6.382 ~ 20.534 s)가 납니다.
- 반면 `avg_gen_speed` 는 **1.09배** 차이 (6.54 ~ 7.14 tok/s)에 그칩니다.
- 토큰당 생성 속도는 거의 비슷한데 전체 시간만 크게 벌어졌다는 것은, 그 격차가 **추론 속도가 아니라 출력 분량**에서 왔다는 뜻입니다.

실제로 답변 길이를 세어 보면 `avg_total_time` 순서와 그대로 일치합니다. (JSON에 출력 토큰 수가 없어 문자 수를 대리 지표로 사용)

| 모델 | 평균 답변 길이 (문자) | Avg Total Time (s) |
| --- | --- | --- |
| Llama 3.1 8B | 64.7 | 6.382 |
| EXAONE 7.8B | 166.9 | 13.203 |
| Kanana 1.5 8B | 230.2 | 20.534 |
- 답변 길이 차이(3.56배)가 전체 시간 차이(3.22배)와 거의 같은 크기입니다.
- 따라서 **avg_total_time 이 짧다는 이유만으로 그 모델의 추론이 그만큼 빠르다고 단정해서는 안 됩니다.** 짧게 답한 결과일 수 있습니다. 순수 생성 성능은 `avg_gen_speed` 로 판단해야 합니다.

### 답변 품질에 대하여

현재 결과 JSON의 `content_score`, `format_score`, `total_score` 가 아직 `null` 입니다. 따라서 이 문서는 **성능 지표 비교까지만** 다루며, 답변 품질의 우열은 판단하지 않습니다.

---

생성: `scripts/compare_model_reports.py` · 원본: `reports/test/*.json` (6개)
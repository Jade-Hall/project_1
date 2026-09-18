# LLM 모델 성능 비교

동일한 하드웨어와 동일한 문항 세트로 Llama 3.1 8B, Kanana 1.5 8B, EXAONE 7.8B 세 모델을 각 2회씩 실행해 적재 시간, 응답 속도, VRAM 사용량을 비교했습니다.

원본: test3.zip · reports/test/*.json (6개)

---

## 테스트 조건

| 항목 | 값 |
|---|---|
| 테스트 문항 수 | 10 |
| 모델별 반복 횟수 | 2 |
| Temperature | 0.0 |
| Context Length (적용값) | 8,192 |

모든 실행이 동일한 문항 세트를 사용했습니다.

| 모델 | Precision | 모델 최대 Context |
|---|---|---|
| Llama 3.1 8B | F16 | 131,072 |
| Kanana 1.5 8B | F16 | 32,768 |
| EXAONE 7.8B | BF16 | 32,768 |

세 모델 모두 최대 지원 context와 무관하게 8,192로 동일하게 제한해 실행했습니다.

---

## 모델별 종합 성능

| 모델 | Precision | Cold Load (s) | Avg Total (s) | Gen Speed (tok/s) | Prompt Speed (tok/s) | VRAM (GB) |
|---|---|---|---|---|---|---|
| Llama 3.1 8B | F16 | 14.312 | **7.591** (최저) | **7.44** (최고) | 184.46 | 5.82 (최고) |
| Kanana 1.5 8B | F16 | 12.576 | 19.646 (최고) | 6.85 (최저) | **194.47** (최고) | **5.56** (최저) |
| EXAONE 7.8B | BF16 | **11.315** (최저) | 13.043 | 7.10 | 172.22 (최저) | 5.79 |

모든 값은 각 모델의 2회 실행 평균입니다.

### VRAM 값 산출 방식

- Llama 3.1 8B: 상수값 (문항 20개 전부 동일, 최소=최대) → 5.82 GB
- Kanana 1.5 8B: 상수값 (문항 20개 전부 동일, 최소=최대) → 5.56 GB
- EXAONE 7.8B: 상수값 (문항 20개 전부 동일, 최소=최대) → 5.79 GB

---

## 모델별 1차 / 2차 결과

| 모델 | Run | Cold Load (s) | Avg Total (s) | Gen Speed (tok/s) | Prompt Speed (tok/s) | 원본 파일 |
|---|---|---|---|---|---|---|
| Llama 3.1 8B | 1 | 14.642 | 7.565 | 7.44 | 182.69 | result_llama3.1_8b-instruct-fp16_F16_1.json |
| Llama 3.1 8B | 2 | 13.981 | 7.618 | 7.44 | 186.23 | result_llama3.1_8b-instruct-fp16_F16_2.json |
| Kanana 1.5 8B | 1 | 12.671 | 19.663 | 6.84 | 194.03 | result_kanana-1.5-8b-full_latest_F16_1.json |
| Kanana 1.5 8B | 2 | 12.482 | 19.629 | 6.86 | 194.90 | result_kanana-1.5-8b-full_latest_F16_2.json |
| EXAONE 7.8B | 1 | 11.195 | 13.132 | 7.04 | 173.37 | result_exaone-7.8b-full_latest_BF16_1.json |
| EXAONE 7.8B | 2 | 11.436 | 12.955 | 7.16 | 171.08 | result_exaone-7.8b-full_latest_BF16_2.json |

---

## 성능 특성 요약

**Cold Load (모델 최초 적재)**
EXAONE 7.8B 11.315 / Kanana 1.5 8B 12.576 / Llama 3.1 8B 14.312 (s)
가장 낮음: EXAONE 7.8B — 가장 높은 Llama 3.1 8B 대비 2.997s 차이 (26.5%)

**생성 속도 (Gen Speed)**
Llama 3.1 8B 7.44 / EXAONE 7.8B 7.10 / Kanana 1.5 8B 6.85 (tok/s)
가장 높음: Llama 3.1 8B — 가장 낮은 Kanana 1.5 8B 대비 0.59 tok/s 차이 (8.6%)

**프롬프트 처리 속도 (Prompt Speed)**
Kanana 1.5 8B 194.47 / Llama 3.1 8B 184.46 / EXAONE 7.8B 172.22 (tok/s)
가장 높음: Kanana 1.5 8B — 가장 낮은 EXAONE 7.8B 대비 22.25 tok/s 차이 (12.9%)

**VRAM 사용량**
Kanana 1.5 8B 5.56 / EXAONE 7.8B 5.79 / Llama 3.1 8B 5.82 (GB)
가장 낮음: Kanana 1.5 8B — 가장 높은 Llama 3.1 8B 대비 0.26GB 차이 (4.7%)

### 1차 / 2차 측정값의 변동 정도

변동률 = (최댓값 − 최솟값) ÷ 2회 평균 × 100

| 모델 | Cold Load | Avg Total Time | Gen Speed | Prompt Speed |
|---|---|---|---|---|
| Llama 3.1 8B | 4.62% | 0.70% | 0.00% | 1.92% |
| Kanana 1.5 8B | **1.50%** | **0.17%** | 0.27% | **0.45%** |
| EXAONE 7.8B | 2.13% | 1.36% | 1.69% | 1.32% |

재현성이 가장 좋은 쪽은 Kanana 1.5 8B (최대 변동 1.50%, Cold Load 기준)입니다. Llama 3.1 8B는 Gen Speed 변동이 0%로 가장 안정적이지만 Cold Load 변동(4.62%)이 세 모델 중 가장 큽니다.

---

## Avg Total Time 해석 시 주의

avg_total_time은 요청부터 응답 완료까지의 전체 시간이므로 모델이 답변을 얼마나 길게 생성했는지에 직접 영향을 받습니다. 같은 속도로 생성하더라도 출력이 길면 total_time은 그만큼 커집니다.

> avg_total_time은 모델 간 **2.59배** 차이(7.591 ~ 19.646s)가 납니다. 반면 avg_gen_speed는 **1.09배** 차이(6.85 ~ 7.44 tok/s)에 그칩니다. 토큰당 생성 속도는 거의 비슷한데 전체 시간만 크게 벌어졌다는 것은, 그 격차가 추론 속도가 아니라 출력 분량에서 왔다는 뜻입니다.

실제로 답변 길이를 세어 보면 avg_total_time 순서와 그대로 일치합니다. (JSON에 출력 토큰 수가 없어 문자 수를 대리 지표로 사용)

| 모델 | 평균 답변 길이 (문자) | Avg Total Time (s) |
|---|---|---|
| Llama 3.1 8B | 64.7 | 7.591 |
| EXAONE 7.8B | 166.9 | 13.043 |
| Kanana 1.5 8B | 220.2 | 19.646 |

답변 길이 차이(3.40배)가 전체 시간 차이(2.59배)와 같은 방향, 비슷한 크기로 움직입니다. 따라서 avg_total_time이 짧다는 이유만으로 그 모델의 추론이 그만큼 빠르다고 단정해서는 안 됩니다. 짧게 답한 결과일 수 있습니다. 순수 생성 성능은 avg_gen_speed로 판단해야 합니다.

---

## 답변 품질에 대하여

본 보고서는 성능 지표(속도·VRAM) 비교까지만 다룹니다. 같은 데이터로 채점한 답변 품질 비교는 별도 문서(`LLM_답변_품질_비교`)에서 다룹니다.

---

*생성: 3개 모델 × 10문항 × 2회 실행, result_\*.json 6개 파일의 cold/warm_results 수치 집계 · 원본: test3.zip (reports/test/\*.json)*

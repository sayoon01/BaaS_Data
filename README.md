# BaaS_Data

GV60 전기차 충전 이력 데이터를 바탕으로 **배터리 충전 성능 저하(Degradation) 추세**를 분석하는 데이터 저장소입니다.

이 프로젝트는 “Fast(급속) vs Slow(완속) 충전이 배터리 성능 변화율에 어떤 차이를 만드는지”를 정량적으로 비교하는 것을 목표로 합니다.

## 이 프로젝트가 하는 일

- GV60 원천 CSV에서 충전 구간을 추출하고, 충전 세션 단위 통계 데이터를 생성합니다.
- 충전 전류/온도 조건 차이를 보정하기 위한 참조값(reference value)과 보정 slope 지표를 계산합니다.
- 차량별 관측 기간을 고려해 월 단위 degradation rate를 계산합니다.
- Fast/Slow 충전군의 평균·분산·중앙값을 비교하고 시각화 결과를 생성합니다.

## 분석 대상/결과물

### 입력 데이터
- `GV60/ev_statistics_fast_slow_stats.csv`: 충전 구간 통계 원본
- `GV60/ev_statistics_fast_slow_stats_v2.csv` ~ `v6.csv`: 파이프라인 단계별 가공 데이터

### 주요 산출물
- `GV60/analysis_results/statistics_summary.csv`: 지표별 요약 통계
- `GV60/analysis_results/vehicle_analysis.csv`: 차량별 상세 분석
- `GV60/analysis_results/fast_vs_slow_comparison.csv`: Fast/Slow 비교표
- `GV60/analysis_results/observation_period_analysis.csv`: 관측 기간 기반 분석
- `GV60/analysis_results/fast_vs_slow_analysis.png`: 비교 시각화
- `GV60/analysis_results/analysis_report.txt`: 자동 생성 분석 리포트

## 핵심 분석 개념

- **Slope 지표(1→3단계 보정)**
  - `slope_1`: 기본 충전 속도
  - `slope_2`: 전류 보정 반영
  - `slope_3`: 전류 + 온도 보정 반영(가장 표준화된 지표)
- **Degradation rate**
  - 시간 경과 대비 성능 변화율
  - 월별 정규화 값(`%/month`)을 사용해 관측 기간이 다른 차량을 공정 비교

## 저장소 구성

```text
BaaS_Data/
├─ README.md
└─ GV60/
   ├─ 실행가이드.md
   ├─ ev_statistics_fast_slow_stats*.csv
   ├─ degradation_rate_comparison.png
   └─ analysis_results/
      ├─ analyze_gv60_degradation.py
      ├─ analysis_report.txt
      ├─ statistics_summary.csv
      ├─ vehicle_analysis.csv
      ├─ fast_vs_slow_comparison.csv
      ├─ observation_period_analysis.csv
      └─ fast_vs_slow_analysis.png
```

## 실행/재현 가이드

전체 분석 절차와 실행 명령은 `GV60/실행가이드.md`를 기준으로 재현할 수 있습니다.

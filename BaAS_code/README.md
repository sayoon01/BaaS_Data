# EV 통계 분석 파이프라인 실행 가이드

## 파이프라인 개요

이 파이프라인은 전기차 배터리의 충전 성능 데이터를 분석하여 배터리 수명(degradation)을 평가하는 전체 프로세스입니다.

### 전체 흐름
1. **참조값 계산**: 차량 타입별 표준값 설정 → 정규화 기준 마련
2. **Slope 계산**: 충전 속도 측정 및 보정 → 성능 지표 생성
3. **Degradation 계산**: 시간에 따른 성능 변화 측정 → 수명 평가
4. **월별 정규화**: 관측 기간 차이 보정 → 공정한 비교
5. **시각화**: 결과 비교 및 분석 → 인사이트 도출

### 핵심 개념

**정규화(Normalization)**
- 차량 모델, 충전 전류, 온도 등 다양한 요인을 보정하여 공정한 비교 가능
- slope_1 → slope_2 → slope_3 순으로 보정 단계가 높아질수록 더 정확

**Degradation Rate**
- 배터리 성능이 시간에 따라 얼마나 감소하는지 측정
- 양수: 성능 감소 (정상적인 노화)
- 음수: 성능 증가 (비정상, 측정 오차 가능)

**월별 정규화**
- 관측 기간이 다른 차량들을 공정하게 비교하기 위한 필수 단계
- 예: 6개월 동안 10% 감소 = 1.67%/월, 12개월 동안 10% 감소 = 0.83%/월

---

## 실행 순서

다음 순서대로 실행하세요:

### 1. `calculate_ref_values.py`
**입력**: `ev_statistics_fast_slow_stats.csv`  
**출력**: `ev_statistics_fast_slow_stats_v2.csv`

**상세 설명**:

#### 목적
차량 타입별로 표준화된 참조값(reference value)을 계산하여, 이후 단계에서 충전 성능을 정규화하고 비교할 수 있는 기준점을 마련합니다.

#### 처리 과정
1. **charge_type 컬럼 생성**
   - `source_path`에서 'fast' 또는 'slow' 문자열을 찾아 충전 타입을 자동 분류
   - 이유: 원본 데이터에 charge_type이 없거나 불완전할 수 있어, 파일 경로에서 명확히 구분

2. **car_type별 참조값 계산**
   - 같은 차량 모델(KONA, IONIQ 등)끼리 그룹화
   - 이유: 차량 모델별로 배터리 용량, 충전 특성이 다르므로 모델별 기준값 필요
   
3. **참조값 종류**
   - **`fast_pack_current_ref`**: Fast 충전 시 해당 car_type의 평균 전류값
     - 용도: 실제 충전 전류를 표준 전류로 정규화하여 비교
   - **`fast_modul_temp_ref`**: Fast 충전 시 해당 car_type의 평균 모듈 온도
     - 용도: 온도 보정을 위한 기준 온도 (4개 모듈 온도의 평균)
   - **`slow_pack_current_ref`, `slow_modul_temp_ref`**: Slow 충전용 참조값
     - 이유: Fast와 Slow 충전은 전류와 온도 특성이 다르므로 별도 기준 필요

4. **각 행에 참조값 추가**
   - 모든 충전 기록에 해당 car_type의 참조값을 매핑
   - 이유: 이후 slope 계산 시 정규화에 사용

---

### 2. `calculate_slopes.py`
**입력**: `ev_statistics_fast_slow_stats_v2.csv`  
**출력**: `ev_statistics_fast_slow_stats_v3.csv`

**상세 설명**:

#### 목적
충전 속도(slope)를 계산하고, 전류와 온도 보정을 통해 표준화된 충전 성능 지표를 생성합니다.

#### 처리 과정

1. **조건 필터링**
   - `start_soc >= 20`: 시작 SOC가 20% 이상인 충전만 선택
     - 이유: SOC가 너무 낮으면 충전 특성이 달라질 수 있음
   - `soc_quan >= 15`: 충전량이 15% 이상인 충전만 선택
     - 이유: 충전량이 너무 적으면 측정 오차가 큼
   - `duration >= 180`: 충전 시간이 180초(3분) 이상인 충전만 선택
     - 이유: 너무 짧은 충전은 신뢰할 수 없음

2. **Fast 충전 Slope 계산 (3단계 보정)**
   
   **`fast_slope_1`**: 기본 충전 속도
   - 공식: `soc_quan / duration_hour`
   - 의미: 시간당 충전된 SOC 비율 (%/hour)
   - 용도: 가장 기본적인 충전 속도 지표
   
   **`fast_slope_2`**: 전류 보정된 충전 속도
   - 공식: `fast_slope_1 * fast_pack_current_ref / b_pack_current_avg`
   - 의미: 실제 전류가 표준 전류와 다를 때 보정
   - 이유: 전류가 낮으면 충전 속도가 느려지므로, 표준 전류 기준으로 정규화
   - 예: 표준 전류가 100A인데 실제 80A면, slope를 100/80 = 1.25배로 보정
   
   **`fast_slope_3`**: 전류 + 온도 보정된 충전 속도
   - 공식: `fast_slope_2 * (1 - 0.01 * (평균모듈온도 - fast_modul_temp_ref))`
   - 의미: 온도가 기준보다 높으면 충전 효율이 떨어지므로 보정
   - 이유: 배터리 온도가 높을수록 충전 효율이 감소 (약 1도당 1% 감소 가정)
   - 예: 기준 온도 25도, 실제 30도면 5도 차이 → 5% 감소 보정

3. **Slow 충전 Slope 계산**
   - Fast와 동일한 3단계 보정 적용
   - 단, Slow 충전용 참조값(`slow_pack_current_ref`, `slow_modul_temp_ref`) 사용
   - 이유: Slow 충전은 전류와 온도 특성이 Fast와 다름

#### 결과
- 각 충전 기록마다 3단계 보정된 slope 값 저장
- 보정 단계가 높을수록 더 정확한 성능 지표 (slope_3가 가장 정확)

---

### 3. `calculate_degradation.py`
**입력**: `ev_statistics_fast_slow_stats_v3.csv`  
**출력**: `ev_statistics_fast_slow_stats_v4.csv`

**상세 설명**:

#### 목적
각 차량의 배터리 성능 저하(degradation) 정도를 시간에 따라 측정합니다. 초기 충전 성능과 최근 충전 성능을 비교하여 배터리 수명을 평가합니다.

#### 처리 과정

1. **car_id별 그룹화**
   - 같은 차량의 모든 충전 기록을 하나로 묶음
   - 이유: 차량별로 개별적인 degradation 추적 필요

2. **Fast 충전 Degradation 계산**
   
   **시간 정렬**
   - `start_time` 기준으로 오름차순 정렬
   - 가장 과거 행: 첫 충전 기록 (초기 성능)
   - 가장 최신 행: 마지막 충전 기록 (현재 성능)
   
   **Degradation Rate 계산**
   - 공식: `(과거값 - 최신값) / 과거값 * 100`
   - 의미: 초기 대비 현재 성능이 몇 % 감소했는지
   - 예: slope_1이 30에서 27로 감소 → (30-27)/30 * 100 = 10% 감소
   - 양수: 성능 감소 (정상적인 degradation)
   - 음수: 성능 증가 (비정상, 측정 오차 가능)
   
   **3가지 Slope에 대해 각각 계산**
   - `fast_degradation_rate_1`: 기본 slope 기준
   - `fast_degradation_rate_2`: 전류 보정 slope 기준
   - `fast_degradation_rate_3`: 전류+온도 보정 slope 기준 (가장 정확)
   
   **날짜 정보 저장**
   - `first_fast_charging_date`: 첫 Fast 충전 날짜
   - `last_fast_charging_date`: 마지막 Fast 충전 날짜
   - 용도: 이후 월별 degradation rate 계산에 사용

3. **Slow 충전 Degradation 계산**
   - Fast와 동일한 방식으로 처리
   - Slow 충전만 따로 추적
   - 이유: Fast와 Slow 충전의 degradation 패턴이 다를 수 있음

4. **결과 구조**
   - 각 `car_id`당 한 행으로 집계
   - 이유: 차량별 전체 기간의 degradation을 요약
   - Fast와 Slow가 모두 있는 차량은 두 값 모두 저장
   - 하나만 있는 차량은 해당 값만 저장

#### 활용
- 배터리 수명 예측
- 차량별 성능 저하 비교
- 충전 방식(Fast/Slow)에 따른 degradation 차이 분석

---

### 4. `calculate_monthly_degradation.py`
**입력**: `ev_statistics_fast_slow_stats_v4.csv`  
**출력**: 
- `ev_statistics_fast_slow_stats_v5.csv` (전체 데이터)
- `ev_statistics_fast_slow_stats_v6.csv` (3개월 이상만 필터링)

**상세 설명**:

#### 목적
전체 기간의 degradation rate를 월별로 정규화하여, 관측 기간이 다른 차량들 간의 성능 저하를 공정하게 비교할 수 있도록 합니다.

#### 처리 과정

1. **날짜 차이 계산**
   - `last_charging_date - first_charging_date`를 일 단위로 계산
   - 일 단위를 30으로 나누어 개월 수로 변환
   - 예: 270일 차이 → 9개월

2. **월별 Degradation Rate 계산**
   
   **공식**: `degradation_rate_per_month = degradation_rate / (날짜차이 개월수)`
   
   **이유**:
   - 6개월 동안 10% 감소한 차량과 12개월 동안 10% 감소한 차량은 degradation 속도가 다름
   - 월별로 정규화하면: 6개월 차량은 10/6 = 1.67%/월, 12개월 차량은 10/12 = 0.83%/월
   - 이렇게 하면 차량 간 degradation 속도를 공정하게 비교 가능
   
   **6개 지표 모두 계산**:
   - `fast_degradation_rate_1_per_month`
   - `fast_degradation_rate_2_per_month`
   - `fast_degradation_rate_3_per_month`
   - `slow_degradation_rate_1_per_month`
   - `slow_degradation_rate_2_per_month`
   - `slow_degradation_rate_3_per_month`

3. **파일 분리**

   **v5 (전체 데이터)**
   - 모든 차량의 월별 degradation rate 저장
   - 관측 기간이 짧은 차량도 포함
   - 용도: 전체 데이터 분석
   
   **v6 (3개월 이상 필터링)**
   - Fast 또는 Slow 중 하나라도 3개월 이상인 차량만 선택
   - 이유: 관측 기간이 너무 짧으면 degradation 측정이 부정확할 수 있음
   - 3개월 이상 데이터만 사용하면 더 신뢰할 수 있는 분석 가능
   - 용도: 신뢰도 높은 데이터만으로 분석

4. **통계 출력**
   - 전체 기간 통계: v5 데이터 기준
   - 3개월 이상 통계: v6 데이터 기준
   - 각 지표별 평균, 표준편차, 샘플 수 출력
   - 용도: 두 그룹 간 degradation 패턴 비교

#### 활용
- 차량 모델별 월평균 degradation 비교
- Fast vs Slow 충전의 degradation 속도 비교
- 배터리 수명 예측 모델 개발

---

### 5. `plot_degradation_deviation.py`
**입력**: `ev_statistics_fast_slow_stats_v5.csv`, `ev_statistics_fast_slow_stats_v6.csv`  
**출력**: `degradation_rate_comparison.png`

**상세 설명**:

#### 목적
전체 데이터(v5)와 3개월 이상 데이터(v6)의 degradation rate 분포를 시각적으로 비교하여, 필터링이 분석 결과에 미치는 영향을 확인합니다.

#### 처리 과정

1. **데이터 읽기**
   - v5: 전체 차량 데이터 (관측 기간 무관)
   - v6: 3개월 이상 관측된 차량만 (신뢰도 높은 데이터)

2. **6개 지표 시각화**
   
   **지표 종류**:
   - `fast_degradation_rate_1_per_month`: Fast 기본 slope 기준
   - `fast_degradation_rate_2_per_month`: Fast 전류 보정 slope 기준
   - `fast_degradation_rate_3_per_month`: Fast 전류+온도 보정 slope 기준 (가장 정확)
   - `slow_degradation_rate_1_per_month`: Slow 기본 slope 기준
   - `slow_degradation_rate_2_per_month`: Slow 전류 보정 slope 기준
   - `slow_degradation_rate_3_per_month`: Slow 전류+온도 보정 slope 기준 (가장 정확)
   
   **박스플롯 구성**:
   - 2x3 서브플롯: 6개 지표를 각각 한 그래프에 표시
   - 각 그래프에 v5와 v6를 나란히 비교
   - 박스플롯 요소:
     - 중앙선: 중앙값 (median)
     - 박스: 25% ~ 75% 사분위수 (IQR)
     - 수염: 이상치를 제외한 범위
     - 점: 이상치 (outliers)
     - 평균선: 평균값 표시

3. **통계 정보 표시**
   - 각 그래프 제목에 다음 정보 포함:
     - v5: 평균, 표준편차, 샘플 수
     - v6: 평균, 표준편차, 샘플 수
   - 용도: 수치적 비교 가능

4. **통계 요약 테이블**
   - 콘솔에 모든 지표의 통계 요약 출력
   - 형식: 지표명, v5 평균/표준편차/n, v6 평균/표준편차/n
   - 용도: 정확한 수치 비교 및 보고서 작성

#### 분석 관점

**v5 vs v6 비교의 의미**:
- **v5 (전체)**: 모든 차량 포함, 샘플 수 많음, 하지만 관측 기간 짧은 차량 포함
- **v6 (3개월 이상)**: 신뢰도 높은 데이터만, 샘플 수 적음, 하지만 더 정확한 측정

**기대되는 차이**:
- v6가 더 안정적인 분포를 보일 수 있음 (이상치 제거 효과)
- v6의 평균이 v5와 다를 수 있음 (관측 기간이 긴 차량의 특성 반영)
- v6의 표준편차가 더 작을 수 있음 (신뢰도 높은 데이터만 포함)

#### 활용
- 데이터 품질 평가
- 필터링 기준의 적절성 검증
- 연구 보고서용 시각화 자료
- 차량 모델별 degradation 패턴 비교

---

## 실행 명령어

```bash
# 1단계: 참조값 계산
python calculate_ref_values.py

# 2단계: Slope 계산
python calculate_slopes.py

# 3단계: Degradation rate 계산
python calculate_degradation.py

# 4단계: 월별 Degradation rate 계산
python calculate_monthly_degradation.py

# 5단계: 시각화
python plot_degradation_deviation.py
```

---

## 파일 구조

```
ev_statistics_fast_slow_stats.csv          # 원본 데이터
    ↓ calculate_ref_values.py
ev_statistics_fast_slow_stats_v2.csv        # 참조값 추가
    ↓ calculate_slopes.py
ev_statistics_fast_slow_stats_v3.csv        # Slope 계산 (필터링됨)
    ↓ calculate_degradation.py
ev_statistics_fast_slow_stats_v4.csv        # Degradation rate (car_id별 집계)
    ↓ calculate_monthly_degradation.py
ev_statistics_fast_slow_stats_v5.csv        # 월별 Degradation rate (전체)
ev_statistics_fast_slow_stats_v6.csv        # 월별 Degradation rate (3개월 이상)
    ↓ plot_degradation_deviation.py
degradation_rate_comparison.png             # 비교 그래프
```

---

## 주요 컬럼 설명

### v2 추가 컬럼 (참조값)

**Fast 충전 참조값**
- `fast_pack_current_ref` (단위: A)
  - 의미: 해당 car_type의 Fast 충전 평균 전류값
  - 용도: 실제 충전 전류를 표준 전류로 정규화
  - 예: KONA의 평균 Fast 충전 전류가 75A라면, 모든 KONA의 Fast 충전에 75A 적용

- `fast_modul_temp_ref` (단위: °C)
  - 의미: 해당 car_type의 Fast 충전 평균 모듈 온도
  - 계산: (b_modul_1_temp_avg + b_modul_2_temp_avg + b_modul_3_temp_avg + b_modul_4_temp_avg) / 4의 평균
  - 용도: 온도 보정의 기준 온도
  - 예: KONA의 평균 Fast 충전 온도가 25°C라면, 25°C를 기준으로 온도 보정

**Slow 충전 참조값**
- `slow_pack_current_ref`, `slow_modul_temp_ref`
  - Fast와 동일한 개념이지만 Slow 충전 데이터 기준
  - 이유: Fast와 Slow는 충전 특성이 다르므로 별도 기준 필요

---

### v3 추가 컬럼 (Slope - 충전 속도)

**Fast Slope (단위: %/hour)**
- `fast_slope_1`: 기본 충전 속도
  - 공식: `soc_quan / duration_hour`
  - 의미: 시간당 충전된 SOC 비율
  - 보정 없음: 가장 단순한 지표

- `fast_slope_2`: 전류 보정 충전 속도
  - 공식: `fast_slope_1 * fast_pack_current_ref / b_pack_current_avg`
  - 의미: 표준 전류 기준으로 정규화된 충전 속도
  - 보정: 전류 차이 보정

- `fast_slope_3`: 전류+온도 보정 충전 속도 (가장 정확)
  - 공식: `fast_slope_2 * (1 - 0.01 * (평균모듈온도 - fast_modul_temp_ref))`
  - 의미: 표준 전류와 표준 온도 기준으로 정규화된 충전 속도
  - 보정: 전류 차이 + 온도 차이 보정
  - 용도: 가장 정확한 성능 지표, degradation 분석에 주로 사용

**Slow Slope**
- `slow_slope_1`, `slow_slope_2`, `slow_slope_3`
  - Fast와 동일한 개념이지만 Slow 충전 데이터 기준

---

### v4 추가 컬럼 (Degradation Rate - car_id별 집계)

**Fast 충전 Degradation**
- `first_fast_charging_date`: 첫 Fast 충전 날짜
- `last_fast_charging_date`: 마지막 Fast 충전 날짜
- `fast_degradation_rate_1` (단위: %)
  - 의미: fast_slope_1 기준 전체 기간 동안의 성능 감소율
  - 공식: `(첫_slope_1 - 마지막_slope_1) / 첫_slope_1 * 100`
- `fast_degradation_rate_2`: fast_slope_2 기준 (전류 보정)
- `fast_degradation_rate_3`: fast_slope_3 기준 (전류+온도 보정, 가장 정확)

**Slow 충전 Degradation**
- `first_slow_charging_date`, `last_slow_charging_date`
- `slow_degradation_rate_1`, `slow_degradation_rate_2`, `slow_degradation_rate_3`
  - Fast와 동일한 개념이지만 Slow 충전 데이터 기준

**참고**
- v4는 각 car_id당 한 행으로 집계됨 (차량별 요약)
- Fast와 Slow가 모두 있는 차량은 두 값 모두 저장
- 하나만 있는 차량은 해당 값만 저장 (다른 값은 NaN)

---

### v5/v6 추가 컬럼 (월별 Degradation Rate)

**Fast 월별 Degradation Rate (단위: %/month)**
- `fast_degradation_rate_1_per_month`
  - 공식: `fast_degradation_rate_1 / (날짜차이 개월수)`
  - 의미: 월평균 성능 감소율 (기본 slope 기준)
- `fast_degradation_rate_2_per_month`: 전류 보정 기준
- `fast_degradation_rate_3_per_month`: 전류+온도 보정 기준 (가장 정확)

**Slow 월별 Degradation Rate**
- `slow_degradation_rate_1_per_month`, `slow_degradation_rate_2_per_month`, `slow_degradation_rate_3_per_month`
  - Fast와 동일한 개념

**v5 vs v6 차이**
- **v5**: 모든 차량 포함 (관측 기간 무관)
- **v6**: Fast 또는 Slow 중 하나라도 3개월 이상인 차량만 (신뢰도 높은 데이터)

**활용**
- 차량 모델별 월평균 degradation 비교
- Fast vs Slow 충전의 degradation 속도 비교
- 배터리 수명 예측 모델 개발

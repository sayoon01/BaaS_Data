import pandas as pd
import numpy as np
from datetime import datetime

# CSV 파일 읽기
print("CSV 파일 읽는 중...")
df = pd.read_csv('GV60/ev_statistics_fast_slow_stats_v4.csv')

print(f"원본 데이터 행 수: {len(df)}")

# 날짜 컬럼을 datetime으로 변환
date_columns = ['first_fast_charging_date', 'last_fast_charging_date', 
                'first_slow_charging_date', 'last_slow_charging_date']
for col in date_columns:
    df[col] = pd.to_datetime(df[col], errors='coerce')

# 새로운 컬럼 초기화
df['fast_degradation_rate_1_per_month'] = np.nan
df['fast_degradation_rate_2_per_month'] = np.nan
df['fast_degradation_rate_3_per_month'] = np.nan
df['slow_degradation_rate_1_per_month'] = np.nan
df['slow_degradation_rate_2_per_month'] = np.nan
df['slow_degradation_rate_3_per_month'] = np.nan

print("월별 degradation rate 계산 중...")

# Fast 충전 월별 degradation rate 계산
fast_mask = df['first_fast_charging_date'].notna() & df['last_fast_charging_date'].notna()
fast_count = fast_mask.sum()
print(f"  Fast 충전 데이터가 있는 행 수: {fast_count}")

if fast_count > 0:
    # 날짜 차이를 개월 수로 계산 (일 단위로 계산 후 30으로 나눔)
    fast_date_diff = (df.loc[fast_mask, 'last_fast_charging_date'] - 
                     df.loc[fast_mask, 'first_fast_charging_date']).dt.days / 30.0
    
    # 0으로 나누기 방지
    valid_fast_mask = fast_mask & (fast_date_diff > 0)
    
    # 월별 degradation rate 계산
    df.loc[valid_fast_mask, 'fast_degradation_rate_1_per_month'] = (
        df.loc[valid_fast_mask, 'fast_degradation_rate_1'] / 
        fast_date_diff[valid_fast_mask]
    )
    
    df.loc[valid_fast_mask, 'fast_degradation_rate_2_per_month'] = (
        df.loc[valid_fast_mask, 'fast_degradation_rate_2'] / 
        fast_date_diff[valid_fast_mask]
    )
    
    df.loc[valid_fast_mask, 'fast_degradation_rate_3_per_month'] = (
        df.loc[valid_fast_mask, 'fast_degradation_rate_3'] / 
        fast_date_diff[valid_fast_mask]
    )

# Slow 충전 월별 degradation rate 계산
slow_mask = df['first_slow_charging_date'].notna() & df['last_slow_charging_date'].notna()
slow_count = slow_mask.sum()
print(f"  Slow 충전 데이터가 있는 행 수: {slow_count}")

if slow_count > 0:
    # 날짜 차이를 개월 수로 계산 (일 단위로 계산 후 30으로 나눔)
    slow_date_diff = (df.loc[slow_mask, 'last_slow_charging_date'] - 
                     df.loc[slow_mask, 'first_slow_charging_date']).dt.days / 30.0
    
    # 0으로 나누기 방지
    valid_slow_mask = slow_mask & (slow_date_diff > 0)
    
    # 월별 degradation rate 계산
    df.loc[valid_slow_mask, 'slow_degradation_rate_1_per_month'] = (
        df.loc[valid_slow_mask, 'slow_degradation_rate_1'] / 
        slow_date_diff[valid_slow_mask]
    )
    
    df.loc[valid_slow_mask, 'slow_degradation_rate_2_per_month'] = (
        df.loc[valid_slow_mask, 'slow_degradation_rate_2'] / 
        slow_date_diff[valid_slow_mask]
    )
    
    df.loc[valid_slow_mask, 'slow_degradation_rate_3_per_month'] = (
        df.loc[valid_slow_mask, 'slow_degradation_rate_3'] / 
        slow_date_diff[valid_slow_mask]
    )

# v5 파일로 저장 (기존 컬럼 유지 + 새로운 컬럼 추가)
print("결과를 v5 파일에 저장 중...")
df.to_csv('GV60/ev_statistics_fast_slow_stats_v5.csv', index=False)
print(f"v5 파일 저장 완료: {len(df)} 행")

# 3개월 이상인 것만 필터링
print("\n3개월 이상인 데이터 필터링 중...")

# Fast 또는 Slow 중 하나라도 3개월 이상이면 포함
fast_3months = (
    (df['first_fast_charging_date'].notna() & df['last_fast_charging_date'].notna()) &
    ((df['last_fast_charging_date'] - df['first_fast_charging_date']).dt.days >= 90)
)

slow_3months = (
    (df['first_slow_charging_date'].notna() & df['last_slow_charging_date'].notna()) &
    ((df['last_slow_charging_date'] - df['first_slow_charging_date']).dt.days >= 90)
)

filtered_df = df[fast_3months | slow_3months].copy()

print(f"3개월 이상인 행 수: {len(filtered_df)}")

# v6 파일로 저장
print("결과를 v6 파일에 저장 중...")
filtered_df.to_csv('GV60/ev_statistics_fast_slow_stats_v6.csv', index=False)
print(f"v6 파일 저장 완료: {len(filtered_df)} 행")

print("\n완료!")
print(f"추가된 컬럼: fast_degradation_rate_1_per_month, fast_degradation_rate_2_per_month, "
      f"fast_degradation_rate_3_per_month, slow_degradation_rate_1_per_month, "
      f"slow_degradation_rate_2_per_month, slow_degradation_rate_3_per_month")

# 통계 정보 출력
print("\n=== 통계 정보 ===")

# Fast 충전 날짜 차이 계산 (전체 데이터프레임에 추가)
df['fast_date_diff_days'] = np.nan
if fast_count > 0:
    df.loc[fast_mask, 'fast_date_diff_days'] = (
        df.loc[fast_mask, 'last_fast_charging_date'] - 
        df.loc[fast_mask, 'first_fast_charging_date']
    ).dt.days

# Slow 충전 날짜 차이 계산 (전체 데이터프레임에 추가)
df['slow_date_diff_days'] = np.nan
if slow_count > 0:
    df.loc[slow_mask, 'slow_date_diff_days'] = (
        df.loc[slow_mask, 'last_slow_charging_date'] - 
        df.loc[slow_mask, 'first_slow_charging_date']
    ).dt.days

# Fast 충전 3개월 이상/미만 구분
fast_3months_above = fast_mask & (df['fast_date_diff_days'] >= 90)
fast_3months_below = fast_mask & (df['fast_date_diff_days'] < 90) & (df['fast_date_diff_days'] > 0)

# Slow 충전 3개월 이상/미만 구분
slow_3months_above = slow_mask & (df['slow_date_diff_days'] >= 90)
slow_3months_below = slow_mask & (df['slow_date_diff_days'] < 90) & (df['slow_date_diff_days'] > 0)

print(f"Fast 충전 3개월 이상: {fast_3months_above.sum()} 행")
print(f"Slow 충전 3개월 이상: {slow_3months_above.sum()} 행")

# ========== 전체 기간 통계 (필터링 없음) ==========
print("\n" + "="*60)
print("전체 기간 통계 (필터링 없음)")
print("="*60)

# Fast 전체 통계
if df['fast_degradation_rate_1_per_month'].notna().sum() > 0:
    print(f"\n[Fast] 전체 월별 degradation rate 통계:")
    print(f"  fast_degradation_rate_1_per_month: 평균={df['fast_degradation_rate_1_per_month'].mean():.4f}%/월 (n={df['fast_degradation_rate_1_per_month'].notna().sum()})")
    print(f"  fast_degradation_rate_2_per_month: 평균={df['fast_degradation_rate_2_per_month'].mean():.4f}%/월 (n={df['fast_degradation_rate_2_per_month'].notna().sum()})")
    print(f"  fast_degradation_rate_3_per_month: 평균={df['fast_degradation_rate_3_per_month'].mean():.4f}%/월 (n={df['fast_degradation_rate_3_per_month'].notna().sum()})")

# Slow 전체 통계
if df['slow_degradation_rate_1_per_month'].notna().sum() > 0:
    print(f"\n[Slow] 전체 월별 degradation rate 통계:")
    print(f"  slow_degradation_rate_1_per_month: 평균={df['slow_degradation_rate_1_per_month'].mean():.4f}%/월 (n={df['slow_degradation_rate_1_per_month'].notna().sum()})")
    print(f"  slow_degradation_rate_2_per_month: 평균={df['slow_degradation_rate_2_per_month'].mean():.4f}%/월 (n={df['slow_degradation_rate_2_per_month'].notna().sum()})")
    print(f"  slow_degradation_rate_3_per_month: 평균={df['slow_degradation_rate_3_per_month'].mean():.4f}%/월 (n={df['slow_degradation_rate_3_per_month'].notna().sum()})")

# ========== 3개월 이상 통계 ==========
print("\n" + "="*60)
print("3개월 이상 통계")
print("="*60)

# Fast 3개월 이상 통계
if fast_3months_above.sum() > 0:
    fast_above_df = df.loc[fast_3months_above]
    if fast_above_df['fast_degradation_rate_1_per_month'].notna().sum() > 0:
        print(f"\n[Fast] 3개월 이상 월별 degradation rate 통계:")
        print(f"  fast_degradation_rate_1_per_month: 평균={fast_above_df['fast_degradation_rate_1_per_month'].mean():.4f}%/월 (n={fast_above_df['fast_degradation_rate_1_per_month'].notna().sum()})")
        print(f"  fast_degradation_rate_2_per_month: 평균={fast_above_df['fast_degradation_rate_2_per_month'].mean():.4f}%/월 (n={fast_above_df['fast_degradation_rate_2_per_month'].notna().sum()})")
        print(f"  fast_degradation_rate_3_per_month: 평균={fast_above_df['fast_degradation_rate_3_per_month'].mean():.4f}%/월 (n={fast_above_df['fast_degradation_rate_3_per_month'].notna().sum()})")

# Slow 3개월 이상 통계
if slow_3months_above.sum() > 0:
    slow_above_df = df.loc[slow_3months_above]
    if slow_above_df['slow_degradation_rate_1_per_month'].notna().sum() > 0:
        print(f"\n[Slow] 3개월 이상 월별 degradation rate 통계:")
        print(f"  slow_degradation_rate_1_per_month: 평균={slow_above_df['slow_degradation_rate_1_per_month'].mean():.4f}%/월 (n={slow_above_df['slow_degradation_rate_1_per_month'].notna().sum()})")
        print(f"  slow_degradation_rate_2_per_month: 평균={slow_above_df['slow_degradation_rate_2_per_month'].mean():.4f}%/월 (n={slow_above_df['slow_degradation_rate_2_per_month'].notna().sum()})")
        print(f"  slow_degradation_rate_3_per_month: 평균={slow_above_df['slow_degradation_rate_3_per_month'].mean():.4f}%/월 (n={slow_above_df['slow_degradation_rate_3_per_month'].notna().sum()})")

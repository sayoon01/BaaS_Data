import pandas as pd
import numpy as np
from datetime import datetime

# CSV 파일 읽기
print("CSV 파일 읽는 중...")
df = pd.read_csv('GV60/ev_statistics_fast_slow_stats_v3.csv')

# start_time을 datetime으로 변환
df['start_time'] = pd.to_datetime(df['start_time'])

print(f"원본 데이터 행 수: {len(df)}")
print(f"고유한 car_id 수: {df['car_id'].nunique()}")

# 결과를 저장할 리스트
results = []

# 각 car_id별로 처리
print("car_id별 degradation rate 계산 중...")
for car_id in df['car_id'].unique():
    car_df = df[df['car_id'] == car_id].copy()
    car_type = car_df['car_type'].iloc[0] if len(car_df) > 0 else None
    
    result = {
        'car_id': car_id,
        'car_type': car_type,
        'first_fast_charging_date': None,
        'last_fast_charging_date': None,
        'fast_degradation_rate_1': np.nan,
        'fast_degradation_rate_2': np.nan,
        'fast_degradation_rate_3': np.nan,
        'first_slow_charging_date': None,
        'last_slow_charging_date': None,
        'slow_degradation_rate_1': np.nan,
        'slow_degradation_rate_2': np.nan,
        'slow_degradation_rate_3': np.nan
    }
    
    # Fast 충전 데이터 처리
    fast_df = car_df[car_df['charge_type'] == 'fast'].copy()
    if len(fast_df) > 0:
        # start_time으로 정렬
        fast_df = fast_df.sort_values('start_time')
        
        first_fast = fast_df.iloc[0]
        last_fast = fast_df.iloc[-1]
        
        result['first_fast_charging_date'] = first_fast['start_time']
        result['last_fast_charging_date'] = last_fast['start_time']
        
        # 감소율 계산: (과거값 - 최신값) / 과거값 * 100
        # 값이 감소하면 양수, 증가하면 음수
        if pd.notna(first_fast['fast_slope_1']) and pd.notna(last_fast['fast_slope_1']) and first_fast['fast_slope_1'] != 0:
            result['fast_degradation_rate_1'] = ((first_fast['fast_slope_1'] - last_fast['fast_slope_1']) / first_fast['fast_slope_1']) * 100
        
        if pd.notna(first_fast['fast_slope_2']) and pd.notna(last_fast['fast_slope_2']) and first_fast['fast_slope_2'] != 0:
            result['fast_degradation_rate_2'] = ((first_fast['fast_slope_2'] - last_fast['fast_slope_2']) / first_fast['fast_slope_2']) * 100
        
        if pd.notna(first_fast['fast_slope_3']) and pd.notna(last_fast['fast_slope_3']) and first_fast['fast_slope_3'] != 0:
            result['fast_degradation_rate_3'] = ((first_fast['fast_slope_3'] - last_fast['fast_slope_3']) / first_fast['fast_slope_3']) * 100
    
    # Slow 충전 데이터 처리
    slow_df = car_df[car_df['charge_type'] == 'slow'].copy()
    if len(slow_df) > 0:
        # start_time으로 정렬
        slow_df = slow_df.sort_values('start_time')
        
        first_slow = slow_df.iloc[0]
        last_slow = slow_df.iloc[-1]
        
        result['first_slow_charging_date'] = first_slow['start_time']
        result['last_slow_charging_date'] = last_slow['start_time']
        
        # 감소율 계산: (과거값 - 최신값) / 과거값 * 100
        if pd.notna(first_slow['slow_slope_1']) and pd.notna(last_slow['slow_slope_1']) and first_slow['slow_slope_1'] != 0:
            result['slow_degradation_rate_1'] = ((first_slow['slow_slope_1'] - last_slow['slow_slope_1']) / first_slow['slow_slope_1']) * 100
        
        if pd.notna(first_slow['slow_slope_2']) and pd.notna(last_slow['slow_slope_2']) and first_slow['slow_slope_2'] != 0:
            result['slow_degradation_rate_2'] = ((first_slow['slow_slope_2'] - last_slow['slow_slope_2']) / first_slow['slow_slope_2']) * 100
        
        if pd.notna(first_slow['slow_slope_3']) and pd.notna(last_slow['slow_slope_3']) and first_slow['slow_slope_3'] != 0:
            result['slow_degradation_rate_3'] = ((first_slow['slow_slope_3'] - last_slow['slow_slope_3']) / first_slow['slow_slope_3']) * 100
    
    results.append(result)

# 결과를 DataFrame으로 변환
result_df = pd.DataFrame(results)

# 컬럼 순서 지정
result_df = result_df[[
    'car_id', 
    'car_type', 
    'first_fast_charging_date', 
    'last_fast_charging_date', 
    'fast_degradation_rate_1', 
    'fast_degradation_rate_2', 
    'fast_degradation_rate_3', 
    'first_slow_charging_date', 
    'last_slow_charging_date', 
    'slow_degradation_rate_1', 
    'slow_degradation_rate_2', 
    'slow_degradation_rate_3'
]]

# 결과 저장
print("결과를 파일에 저장 중...")
result_df.to_csv('GV60/ev_statistics_fast_slow_stats_v4.csv', index=False)

print("완료!")
print(f"총 {len(result_df)} 개의 car_id 처리됨")

# 통계 정보 출력
print("\n=== 통계 정보 ===")
print(f"Fast 충전 데이터가 있는 car_id 수: {result_df['first_fast_charging_date'].notna().sum()}")
print(f"Slow 충전 데이터가 있는 car_id 수: {result_df['first_slow_charging_date'].notna().sum()}")

if result_df['fast_degradation_rate_1'].notna().sum() > 0:
    print(f"\nFast degradation rate 통계:")
    print(f"  fast_degradation_rate_1: 평균={result_df['fast_degradation_rate_1'].mean():.4f}%")
    print(f"  fast_degradation_rate_2: 평균={result_df['fast_degradation_rate_2'].mean():.4f}%")
    print(f"  fast_degradation_rate_3: 평균={result_df['fast_degradation_rate_3'].mean():.4f}%")

if result_df['slow_degradation_rate_1'].notna().sum() > 0:
    print(f"\nSlow degradation rate 통계:")
    print(f"  slow_degradation_rate_1: 평균={result_df['slow_degradation_rate_1'].mean():.4f}%")
    print(f"  slow_degradation_rate_2: 평균={result_df['slow_degradation_rate_2'].mean():.4f}%")
    print(f"  slow_degradation_rate_3: 평균={result_df['slow_degradation_rate_3'].mean():.4f}%")

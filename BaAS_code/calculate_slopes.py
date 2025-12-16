import pandas as pd
import numpy as np

# CSV 파일 읽기
print("CSV 파일 읽는 중...")
df = pd.read_csv('GV60/ev_statistics_fast_slow_stats_v2.csv')

print(f"원본 데이터 행 수: {len(df)}")

# 조건 필터링: start_soc >= 20, soc_quan >= 15, duration >= 180
print("조건 필터링 중...")
filtered_df = df[
    (df['start_soc'] >= 20) & 
    (df['soc_quan'] >= 15) & 
    (df['duration'] >= 180)
].copy()

print(f"필터링 후 행 수: {len(filtered_df)}")

# 새로운 컬럼 초기화
filtered_df['fast_slope_1'] = np.nan
filtered_df['fast_slope_2'] = np.nan
filtered_df['fast_slope_3'] = np.nan
filtered_df['slow_slope_1'] = np.nan
filtered_df['slow_slope_2'] = np.nan
filtered_df['slow_slope_3'] = np.nan

# 평균 모듈 온도 계산
filtered_df['avg_modul_temp'] = (
    filtered_df['b_modul_1_temp_avg'] + 
    filtered_df['b_modul_2_temp_avg'] + 
    filtered_df['b_modul_3_temp_avg'] + 
    filtered_df['b_modul_4_temp_avg']
) / 4

# 급속충전 구간 계산
print("급속충전 구간 slope 계산 중...")
fast_mask = filtered_df['charge_type'] == 'fast'
fast_count = fast_mask.sum()
print(f"  급속충전 행 수: {fast_count}")

if fast_count > 0:
    # fast_slope_1 = soc_quan / duration_hour
    filtered_df.loc[fast_mask, 'fast_slope_1'] = (
        filtered_df.loc[fast_mask, 'soc_quan'] / 
        filtered_df.loc[fast_mask, 'duration_hour']
    )
    
    # fast_slope_2 = fast_slope_1 * fast_pack_current_ref / b_pack_current_avg
    filtered_df.loc[fast_mask, 'fast_slope_2'] = (
        filtered_df.loc[fast_mask, 'fast_slope_1'] * 
        filtered_df.loc[fast_mask, 'fast_pack_current_ref'] / 
        filtered_df.loc[fast_mask, 'b_pack_current_avg']
    )
    
    # fast_slope_3 = fast_slope_2 * (1 - 0.01 * (avg_modul_temp - fast_modul_temp_ref))
    filtered_df.loc[fast_mask, 'fast_slope_3'] = (
        filtered_df.loc[fast_mask, 'fast_slope_2'] * 
        (1 - 0.01 * (
            filtered_df.loc[fast_mask, 'avg_modul_temp'] - 
            filtered_df.loc[fast_mask, 'fast_modul_temp_ref']
        ))
    )

# 완속충전 구간 계산
print("완속충전 구간 slope 계산 중...")
slow_mask = filtered_df['charge_type'] == 'slow'
slow_count = slow_mask.sum()
print(f"  완속충전 행 수: {slow_count}")

if slow_count > 0:
    # slow_slope_1 = soc_quan / duration_hour
    filtered_df.loc[slow_mask, 'slow_slope_1'] = (
        filtered_df.loc[slow_mask, 'soc_quan'] / 
        filtered_df.loc[slow_mask, 'duration_hour']
    )
    
    # slow_slope_2 = slow_slope_1 * slow_pack_current_ref / b_pack_current_avg
    # (사용자 요청에 fast_slope_1이라고 되어 있지만, 논리상 slow_slope_1이 맞는 것으로 수정)
    filtered_df.loc[slow_mask, 'slow_slope_2'] = (
        filtered_df.loc[slow_mask, 'slow_slope_1'] * 
        filtered_df.loc[slow_mask, 'slow_pack_current_ref'] / 
        filtered_df.loc[slow_mask, 'b_pack_current_avg']
    )
    
    # slow_slope_3 = slow_slope_2 * (1 - 0.01 * (avg_modul_temp - slow_modul_temp_ref))
    # (사용자 요청에 fast_slope_2라고 되어 있지만, 논리상 slow_slope_2가 맞는 것으로 수정)
    filtered_df.loc[slow_mask, 'slow_slope_3'] = (
        filtered_df.loc[slow_mask, 'slow_slope_2'] * 
        (1 - 0.01 * (
            filtered_df.loc[slow_mask, 'avg_modul_temp'] - 
            filtered_df.loc[slow_mask, 'slow_modul_temp_ref']
        ))
    )

# avg_modul_temp 컬럼 제거 (임시 계산용이었으므로)
filtered_df = filtered_df.drop(columns=['avg_modul_temp'])

# 결과 저장
print("결과를 파일에 저장 중...")
filtered_df.to_csv('GV60/ev_statistics_fast_slow_stats_v3.csv', index=False)

print("완료!")
print(f"총 {len(filtered_df)} 행 저장됨")
print(f"추가된 컬럼: fast_slope_1, fast_slope_2, fast_slope_3, slow_slope_1, slow_slope_2, slow_slope_3")

# 통계 정보 출력
print("\n=== 통계 정보 ===")
print(f"급속충전 행 수: {fast_count}")
print(f"완속충전 행 수: {slow_count}")
if fast_count > 0:
    print(f"\n급속충전 slope 통계:")
    print(f"  fast_slope_1: 평균={filtered_df.loc[fast_mask, 'fast_slope_1'].mean():.4f}")
    print(f"  fast_slope_2: 평균={filtered_df.loc[fast_mask, 'fast_slope_2'].mean():.4f}")
    print(f"  fast_slope_3: 평균={filtered_df.loc[fast_mask, 'fast_slope_3'].mean():.4f}")
if slow_count > 0:
    print(f"\n완속충전 slope 통계:")
    print(f"  slow_slope_1: 평균={filtered_df.loc[slow_mask, 'slow_slope_1'].mean():.4f}")
    print(f"  slow_slope_2: 평균={filtered_df.loc[slow_mask, 'slow_slope_2'].mean():.4f}")
    print(f"  slow_slope_3: 평균={filtered_df.loc[slow_mask, 'slow_slope_3'].mean():.4f}")

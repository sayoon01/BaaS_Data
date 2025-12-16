import pandas as pd
import numpy as np

# CSV 파일 읽기
print("CSV 파일 읽는 중...")
df = pd.read_csv('GV60/ev_statistics_fast_slow_stats.csv')

# source_path에서 charge_type 생성/업데이트 (charge_type이 없거나 비어있을 때만)
print("charge_type 컬럼 확인 중...")
if 'charge_type' not in df.columns or df['charge_type'].isna().all():
    print("charge_type이 없거나 모두 비어있어서 source_path에서 생성합니다...")
    df['charge_type'] = df['source_path'].apply(
        lambda x: 'fast' if 'fast' in str(x).lower() else ('slow' if 'slow' in str(x).lower() else None)
    )
else:
    print(f"기존 charge_type 사용: {df['charge_type'].value_counts().to_dict()}")

# car_type별로 그룹화하여 참조값 계산
print("car_type별 참조값 계산 중...")

# 각 car_type 그룹에 대해 fast/slow 참조값 계산
ref_values = {}

for car_type in df['car_type'].unique():
    if pd.isna(car_type):
        continue
    
    car_type_df = df[df['car_type'] == car_type]
    
    # Fast 그룹
    fast_df = car_type_df[car_type_df['charge_type'] == 'fast']
    if len(fast_df) > 0:
        fast_pack_current_ref = fast_df['b_pack_current_avg'].mean()
        fast_modul_temp_avg = (
            fast_df['b_modul_1_temp_avg'] + 
            fast_df['b_modul_2_temp_avg'] + 
            fast_df['b_modul_3_temp_avg'] + 
            fast_df['b_modul_4_temp_avg']
        ) / 4
        fast_modul_temp_ref = fast_modul_temp_avg.mean()
    else:
        fast_pack_current_ref = np.nan
        fast_modul_temp_ref = np.nan
    
    # Slow 그룹
    slow_df = car_type_df[car_type_df['charge_type'] == 'slow']
    if len(slow_df) > 0:
        slow_pack_current_ref = slow_df['b_pack_current_avg'].mean()
        slow_modul_temp_avg = (
            slow_df['b_modul_1_temp_avg'] + 
            slow_df['b_modul_2_temp_avg'] + 
            slow_df['b_modul_3_temp_avg'] + 
            slow_df['b_modul_4_temp_avg']
        ) / 4
        slow_modul_temp_ref = slow_modul_temp_avg.mean()
    else:
        slow_pack_current_ref = np.nan
        slow_modul_temp_ref = np.nan
    
    ref_values[car_type] = {
        'fast_pack_current_ref': fast_pack_current_ref,
        'fast_modul_temp_ref': fast_modul_temp_ref,
        'slow_pack_current_ref': slow_pack_current_ref,
        'slow_modul_temp_ref': slow_modul_temp_ref
    }
    
    print(f"  {car_type}: fast_pack_current_ref={fast_pack_current_ref:.2f}, "
          f"fast_modul_temp_ref={fast_modul_temp_ref:.2f}, "
          f"slow_pack_current_ref={slow_pack_current_ref:.2f}, "
          f"slow_modul_temp_ref={slow_modul_temp_ref:.2f}")

# 각 행에 해당 car_type의 참조값 추가
print("참조값을 각 행에 추가 중...")
df['fast_pack_current_ref'] = df['car_type'].map(lambda x: ref_values.get(x, {}).get('fast_pack_current_ref', np.nan))
df['fast_modul_temp_ref'] = df['car_type'].map(lambda x: ref_values.get(x, {}).get('fast_modul_temp_ref', np.nan))
df['slow_pack_current_ref'] = df['car_type'].map(lambda x: ref_values.get(x, {}).get('slow_pack_current_ref', np.nan))
df['slow_modul_temp_ref'] = df['car_type'].map(lambda x: ref_values.get(x, {}).get('slow_modul_temp_ref', np.nan))

# 결과를 원본 파일에 저장
print("결과를 파일에 저장 중...")
df.to_csv('GV60/ev_statistics_fast_slow_stats_v2.csv', index=False)

print("완료!")
print(f"총 {len(df)} 행 처리됨")
print(f"추가된 컬럼: fast_pack_current_ref, fast_modul_temp_ref, slow_pack_current_ref, slow_modul_temp_ref")

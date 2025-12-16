import pandas as pd

# 파일 경로 (필요하면 수정해서 사용하세요)
stats_path = "/mnt/hdd_c_disk_8T/ev_statistics_fast_slow_stats.csv"
map_path = "/mnt/hdd_c_disk_8T/car_model_map_standardized.csv"

# 1. CSV 읽기
df_stats = pd.read_csv(stats_path)  # ev_statistics_fast_slow_stats.csv
df_map = pd.read_csv(map_path)      # car_model_map_standardized.csv

# 2. car_model_map_standardized의 컬럼명을 맞춰주기
# dev_id -> car_id 로 이름 변경 (조인 키 일치)
df_map = df_map.rename(columns={"dev_id": "car_id", "car_model": "car_type"})

# 3. car_id 기준으로 left join (stats 기준)
df_merged = pd.merge(
    df_stats,
    df_map[["car_id", "car_type"]],
    on="car_id",
    how="left"
)

# 4. 매칭 안 된 경우 UNKNOWN으로 세팅
df_merged["car_type"] = df_merged["car_type"].fillna("UNKNOWN")

# 5. car_id, start_time 기준 정렬
df_merged = df_merged.sort_values(by=["car_id", "start_time"])

# 6. 같은 파일명으로 다시 저장 (인덱스 컬럼 X)
df_merged.to_csv(stats_path, index=False)
"""
GV60 데이터용 통계 집계 스크립트
- kind='charging'인 구간만 추출
- b_fast_charg_con_sts가 True면 'fast', b_slow_charg_con_sts가 True면 'slow'
"""
import os
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Optional, List as TypedList

import pandas as pd


REQUIRED_COLUMNS = [
    "dev_id",  # 차량 id
    "coll_dt",  # 실시간 시간
    "b_soc",  # 실시간 soc
    "b_modul_1_temp",  # 실시간 모듈1 온도
    "b_modul_2_temp",  # 실시간 모듈2 온도
    "b_modul_3_temp",  # 실시간 모듈3 온도
    "b_modul_4_temp",  # 실시간 모듈4 온도
    "b_pack_current",  # 실시간 팩 전류
    "b_pack_volt",  # 실시간 팩 전압
    "kind",  # 구간 플래그
    "b_fast_charg_con_sts",  # 급속 충전 연결 상태
    "b_slow_charg_con_sts",  # 완속 충전 연결 상태
]


def detect_charge_type_from_status(df_segment: pd.DataFrame) -> str:
    """
    구간 데이터에서 b_fast_charg_con_sts와 b_slow_charg_con_sts로 충전 타입 판단
    - b_fast_charg_con_sts가 True면 'fast'
    - b_slow_charg_con_sts가 True면 'slow'
    - 둘 다 False면 'unknown'
    """
    # True인 값의 개수 세기
    fast_count = df_segment['b_fast_charg_con_sts'].sum() if df_segment['b_fast_charg_con_sts'].dtype == bool else (df_segment['b_fast_charg_con_sts'] == True).sum()
    slow_count = df_segment['b_slow_charg_con_sts'].sum() if df_segment['b_slow_charg_con_sts'].dtype == bool else (df_segment['b_slow_charg_con_sts'] == True).sum()
    
    # 더 많이 나타나는 타입으로 결정
    if fast_count > slow_count:
        return 'fast'
    elif slow_count > fast_count:
        return 'slow'
    elif fast_count > 0:
        return 'fast'
    elif slow_count > 0:
        return 'slow'
    else:
        return 'unknown'


def extract_charging_segments(df: pd.DataFrame) -> List[pd.DataFrame]:
    """
    DataFrame에서 kind에 'charging'이 포함된 연속된 구간들을 추출
    
    Returns:
        list of DataFrames: 각 충전 구간별 DataFrame 리스트
    """
    # kind 컬럼에 'charging'이 포함된 행만 필터링
    charging_df = df[df['kind'].str.contains('charging', na=False)].copy()
    
    if charging_df.empty:
        return []
    
    # 시간 정렬
    charging_df = charging_df.sort_values('coll_dt')
    
    # 연속된 구간 찾기 (시간 차이가 일정 시간 이상이면 새로운 구간)
    charging_df['time_diff'] = charging_df['coll_dt'].diff()
    # 5분(300초) 이상 차이나면 새로운 구간으로 간주
    charging_df['new_segment'] = (charging_df['time_diff'] > pd.Timedelta(minutes=5)) | (charging_df['time_diff'].isna())
    charging_df['segment_id'] = charging_df['new_segment'].cumsum()
    
    # 각 구간별로 분리
    segments = []
    for seg_id in charging_df['segment_id'].unique():
        seg_df = charging_df[charging_df['segment_id'] == seg_id].copy()
        if len(seg_df) > 1:  # 최소 2개 행 이상인 구간만
            segments.append(seg_df)
    
    return segments


def process_one_csv(path: str) -> List[Dict]:
    """
    단일 CSV 파일을 읽어 충전 구간별로 통계를 생성.
    kind='charging'인 구간만 처리하고, 각 구간마다 하나의 통계 행 생성.
    
    Returns:
        List[Dict]: 각 충전 구간별 통계 딕셔너리 리스트
    """
    try:
        # 필요한 컬럼만 읽기
        df = pd.read_csv(path, low_memory=False, encoding="utf-8", usecols=REQUIRED_COLUMNS)
    except Exception as e:
        print(f"[WARN] CSV 읽기 실패: {path} ({e})", flush=True)
        return []

    # 필수 컬럼 체크
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        print(f"[WARN] 필요한 컬럼 없음: {path} (missing={missing})", flush=True)
        return []

    if df.empty:
        print(f"[WARN] 데이터 없음: {path}", flush=True)
        return []

    # 시간 정렬
    try:
        df["coll_dt"] = pd.to_datetime(df["coll_dt"])
    except Exception as e:
        print(f"[WARN] coll_dt 파싱 실패: {path} ({e})", flush=True)
        return []

    df = df.sort_values("coll_dt")

    # kind='charging'인 구간 추출
    segments = extract_charging_segments(df)
    
    if not segments:
        return []

    results = []
    
    # 각 충전 구간별로 통계 생성
    for seg_idx, seg_df in enumerate(segments):
        seg_df = seg_df.sort_values("coll_dt")
        
        first = seg_df.iloc[0]
        last = seg_df.iloc[-1]

        lines = len(seg_df)
        
        start_time = first["coll_dt"]
        end_time = last["coll_dt"]

        # duration (초/시간)
        duration_sec = (end_time - start_time).total_seconds()
        duration_hour = duration_sec / 3600.0 if pd.notna(duration_sec) else None

        # SOC
        start_soc = first["b_soc"]
        end_soc = last["b_soc"]
        soc_quan = end_soc - start_soc

        # 평균 값들
        b_modul_1_temp_avg = seg_df["b_modul_1_temp"].mean()
        b_modul_2_temp_avg = seg_df["b_modul_2_temp"].mean()
        b_modul_3_temp_avg = seg_df["b_modul_3_temp"].mean()
        b_modul_4_temp_avg = seg_df["b_modul_4_temp"].mean()
        b_pack_current_avg = seg_df["b_pack_current"].mean()
        b_pack_volt_avg = seg_df["b_pack_volt"].mean()

        # 충전 타입 판단
        charge_type = detect_charge_type_from_status(seg_df)

        result = {
            "car_id": first["dev_id"],
            "charge_type": charge_type,
            "start_soc": start_soc,
            "end_soc": end_soc,
            "soc_quan": soc_quan,
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration_sec,
            "duration_hour": duration_hour,
            "lines": lines,
            "b_modul_1_temp_avg": b_modul_1_temp_avg,
            "b_modul_2_temp_avg": b_modul_2_temp_avg,
            "b_modul_3_temp_avg": b_modul_3_temp_avg,
            "b_modul_4_temp_avg": b_modul_4_temp_avg,
            "b_pack_current_avg": b_pack_current_avg,
            "b_pack_volt_avg": b_pack_volt_avg,
            "source_path": f"{path}#segment_{seg_idx}",
            "car_type": "GV60",  # GV60 데이터이므로 고정
        }

        results.append(result)

    return results


def find_csv_files(root: str) -> List[str]:
    """
    root 이하의 모든 CSV 파일 경로 리스트 반환.
    임시 디렉토리(숨김 디렉토리 또는 _parts로 끝나는 디렉토리)와 
    이미 생성된 통계 CSV 파일은 제외.
    """
    csv_paths: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # 숨김 디렉토리나 _parts로 끝나는 디렉토리는 제외
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and not d.endswith('_parts')]
        
        for name in filenames:
            if name.lower().endswith(".csv"):
                # 이미 생성된 통계 CSV 파일은 제외
                if name.startswith("ev_statistics_"):
                    continue
                csv_paths.append(os.path.join(dirpath, name))
    csv_paths.sort()
    return csv_paths


def process_one_csv_to_file(path: str, idx: int, temp_dir: str) -> Optional[str]:
    """
    단일 CSV를 처리해 통계 CSV 파일을 작성하고, 그 경로를 반환.
    여러 구간이 있을 수 있으므로 여러 행이 저장될 수 있음.
    """
    rows = process_one_csv(path)
    if not rows:
        return None

    try:
        os.makedirs(temp_dir, exist_ok=True)
        part_path = os.path.join(temp_dir, f"part_{idx:07d}.csv")
        df_part = pd.DataFrame(rows)
        df_part.to_csv(part_path, index=False, encoding="utf-8-sig")
        return part_path
    except Exception as e:
        print(f"[ERROR] 부분 CSV 저장 실패: {path} -> {e}", flush=True)
        return None


def run_parallel(csv_paths: List[str], workers: int, temp_dir: str) -> TypedList[str]:
    """멀티프로세싱으로 CSV들을 처리해, 각 프로세스(작업)별 통계 CSV 경로 리스트를 생성."""
    part_paths: TypedList[str] = []

    with ProcessPoolExecutor(max_workers=workers) as executor:
        future_to_info = {
            executor.submit(process_one_csv_to_file, p, idx, temp_dir): (p, idx)
            for idx, p in enumerate(csv_paths)
        }

        for future in as_completed(future_to_info):
            path, idx = future_to_info[future]
            try:
                part_path = future.result()
            except Exception as e:
                print(f"[ERROR] 처리 중 예외 발생: {path} (idx={idx}, {e})", flush=True)
                part_path = None

            if part_path is not None:
                part_paths.append(part_path)
                # 처리된 구간 수 출력
                try:
                    df_part = pd.read_csv(part_path)
                    print(f"[INFO] 처리 완료: {os.path.basename(path)} -> {len(df_part)}개 구간", flush=True)
                except:
                    pass

    return part_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="GV60 데이터 통계 집계 스크립트")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="./GV60",
        help="입력 CSV들이 있는 루트 디렉터리 (기본: ./GV60)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="GV60/ev_statistics_fast_slow_stats.csv",
        help="결과 통계 CSV 파일 경로 (기본: GV60/ev_statistics_fast_slow_stats.csv)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=os.cpu_count() or 4,
        help="멀티프로세싱 프로세스 개수 (기본: CPU 코어 수)",
    )

    args = parser.parse_args()

    data_dir = args.data_dir
    output_path = args.output
    workers = max(1, args.workers)

    if not os.path.isdir(data_dir):
        print(f"[ERROR] 데이터 디렉터리가 존재하지 않습니다: {data_dir}")
        return

    csv_paths = find_csv_files(data_dir)
    if not csv_paths:
        print(f"[ERROR] CSV 파일을 찾지 못했습니다: {data_dir}")
        return

    print(f"[INFO] 총 {len(csv_paths)}개 CSV 파일 발견. workers={workers}")

    # 부분 통계 CSV를 저장할 임시 디렉터리
    base_output_dir = os.path.dirname(os.path.abspath(output_path)) or "."
    temp_dir_name = f".{os.path.basename(output_path)}_parts"
    temp_dir = os.path.join(base_output_dir, temp_dir_name)

    print(f"[INFO] 부분 통계 CSV 디렉터리: {temp_dir}")

    part_paths = run_parallel(csv_paths, workers, temp_dir)

    if not part_paths:
        print("[ERROR] 유효한 결과가 없습니다. (모든 파일에서 오류 발생)")
        return

    # 메인 프로세스에서 부분 CSV들을 읽어 하나의 통계 CSV로 합치기
    try:
        part_paths_sorted = sorted(part_paths)
        df_list = [pd.read_csv(p) for p in part_paths_sorted]
        df_result = pd.concat(df_list, ignore_index=True)
        df_result.to_csv(output_path, index=False, encoding="utf-8-sig")
    except Exception as e:
        print(f"[ERROR] 결과 CSV 병합/저장 실패: {output_path} ({e})")
        return

    print(f"[INFO] 통계 CSV 저장 완료: {output_path} (rows={len(df_result)}, parts={len(part_paths)})")
    
    # Fast/Slow 개수 출력
    if 'charge_type' in df_result.columns:
        print(f"\n[INFO] 충전 타입별 개수:")
        print(df_result['charge_type'].value_counts())
        print(f"[INFO] 고유 차량 수: {df_result['car_id'].nunique()}개")


if __name__ == "__main__":
    main()


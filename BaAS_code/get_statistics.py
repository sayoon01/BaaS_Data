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
]


def detect_charge_type(path: str) -> str:
    """파일 경로에서 fast/slow 여부를 판단."""
    lower = path.lower()
    if "fast" in lower:
        return "fast"
    if "slow" in lower:
        return "slow"
    return "unknown"


def process_one_csv(path: str) -> Optional[Dict]:
    """단일 CSV 파일을 읽어 통계 1줄(dict) 생성.

    실패 시 None 반환.
    """
    try:
        df = pd.read_csv(path, low_memory=False, encoding="utf-8", usecols=REQUIRED_COLUMNS)
    except Exception as e:
        print(f"[WARN] CSV 읽기 실패: {path} ({e})", flush=True)
        return None

    # 필수 컬럼 체크
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        print(f"[WARN] 필요한 컬럼 없음: {path} (missing={missing})", flush=True)
        return None

    if df.empty:
        print(f"[WARN] 데이터 없음: {path}", flush=True)
        return None

    # 시간 정렬
    try:
        df["coll_dt"] = pd.to_datetime(df["coll_dt"])
    except Exception as e:
        print(f"[WARN] coll_dt 파싱 실패: {path} ({e})", flush=True)
        return None

    df = df.sort_values("coll_dt")

    first = df.iloc[0]
    last = df.iloc[-1]

    lines = len(df)
    
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
    b_modul_1_temp_avg = df["b_modul_1_temp"].mean()
    b_modul_2_temp_avg = df["b_modul_2_temp"].mean()
    b_modul_3_temp_avg = df["b_modul_3_temp"].mean()
    b_modul_4_temp_avg = df["b_modul_4_temp"].mean()
    b_pack_current_avg = df["b_pack_current"].mean()
    b_pack_volt_avg = df["b_pack_volt"].mean()


    result = {
        "car_id": first["dev_id"],
        "charge_type": detect_charge_type(path),
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
        # 디버깅 및 추적을 위해 원본 파일 경로도 남김(원하면 나중에 드롭 가능)
        "source_path": path,
    }

    return result


def find_csv_files(root: str) -> List[str]:
    """root 이하의 모든 CSV 파일 경로 리스트 반환."""
    csv_paths: List[str] = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.lower().endswith(".csv"):
                csv_paths.append(os.path.join(dirpath, name))
    csv_paths.sort()
    return csv_paths


def process_one_csv_to_file(path: str, idx: int, temp_dir: str) -> Optional[str]:
    """단일 CSV를 처리해 통계 1줄짜리 CSV 파일을 작성하고, 그 경로를 반환."""
    row = process_one_csv(path)
    if row is None:
        return None

    try:
        os.makedirs(temp_dir, exist_ok=True)
        part_path = os.path.join(temp_dir, f"part_{idx:07d}.csv")
        df_part = pd.DataFrame([row])
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
            except Exception as e:  # 예상치 못한 예외 방어
                print(f"[ERROR] 처리 중 예외 발생: {path} (idx={idx}, {e})", flush=True)
                part_path = None

            if part_path is not None:
                part_paths.append(part_path)

    return part_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="EV_data 통계 집계 스크립트")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="./EV_data",
        help="입력 CSV들이 있는 루트 디렉터리 (기본: ./EV_data)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="ev_statistics.csv",
        help="결과 통계 CSV 파일 경로 (기본: ev_statistics.csv)",
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

    # 부분 통계 CSV를 저장할 임시 디렉터리 (최종 output과 같은 위치에 생성)
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


if __name__ == "__main__":
    main()

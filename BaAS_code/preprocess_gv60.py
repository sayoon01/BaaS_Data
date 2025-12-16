"""
GV60 raw 데이터에서 kind='charging'인 구간만 추출하여 통계 데이터로 변환

사용법:
    python preprocess_gv60.py --data-dir GV60 --output GV60/ev_statistics_fast_slow_stats.csv
"""
import os
import argparse
import pandas as pd
import numpy as np
from pathlib import Path


def detect_charge_type_from_current(avg_current: float, threshold: float = 50.0) -> str:
    """
    평균 전류 값으로 fast/slow 충전 구분
    threshold 이상이면 'fast', 미만이면 'slow'
    (GV60의 경우 적절한 threshold 값으로 조정 필요)
    """
    if pd.isna(avg_current):
        return 'unknown'
    return 'fast' if avg_current >= threshold else 'slow'


def extract_charging_segments(df: pd.DataFrame) -> list:
    """
    DataFrame에서 kind에 'charging'이 포함된 연속된 구간들을 추출
    
    Returns:
        list of DataFrames: 각 충전 구간별 DataFrame 리스트
    """
    # kind 컬럼에 'charging'이 포함된 행만 필터링 (예: 'charging', 'charging;driving')
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


def process_charging_segment(seg_df: pd.DataFrame, source_path: str, segment_idx: int) -> dict:
    """
    하나의 충전 구간을 통계 데이터로 변환
    """
    seg_df = seg_df.sort_values('coll_dt')
    
    first = seg_df.iloc[0]
    last = seg_df.iloc[-1]
    
    start_time = first['coll_dt']
    end_time = last['coll_dt']
    
    # duration (초/시간)
    duration_sec = (end_time - start_time).total_seconds()
    duration_hour = duration_sec / 3600.0 if pd.notna(duration_sec) else None
    
    # SOC
    start_soc = first['b_soc']
    end_soc = last['b_soc']
    soc_quan = end_soc - start_soc
    
    # 평균 값들
    b_modul_1_temp_avg = seg_df['b_modul_1_temp'].mean()
    b_modul_2_temp_avg = seg_df['b_modul_2_temp'].mean()
    b_modul_3_temp_avg = seg_df['b_modul_3_temp'].mean()
    b_modul_4_temp_avg = seg_df['b_modul_4_temp'].mean()
    b_pack_current_avg = seg_df['b_pack_current'].mean()
    b_pack_volt_avg = seg_df['b_pack_volt'].mean()
    
    # charge_type 판단 (전류 기준)
    charge_type = detect_charge_type_from_current(b_pack_current_avg)
    
    result = {
        'car_id': first['dev_id'],
        'charge_type': charge_type,
        'start_soc': start_soc,
        'end_soc': end_soc,
        'soc_quan': soc_quan,
        'start_time': start_time,
        'end_time': end_time,
        'duration': duration_sec,
        'duration_hour': duration_hour,
        'lines': len(seg_df),
        'b_modul_1_temp_avg': b_modul_1_temp_avg,
        'b_modul_2_temp_avg': b_modul_2_temp_avg,
        'b_modul_3_temp_avg': b_modul_3_temp_avg,
        'b_modul_4_temp_avg': b_modul_4_temp_avg,
        'b_pack_current_avg': b_pack_current_avg,
        'b_pack_volt_avg': b_pack_volt_avg,
        'source_path': f"{source_path}#segment_{segment_idx}",
        'car_type': 'GV60'  # GV60 데이터이므로 고정
    }
    
    return result


def process_one_csv_file(csv_path: str) -> list:
    """
    하나의 CSV 파일을 처리하여 충전 구간 통계 리스트 반환
    """
    try:
        # 필요한 컬럼만 읽기 (메모리 절약)
        required_cols = [
            'dev_id', 'coll_dt', 'b_soc', 
            'b_modul_1_temp', 'b_modul_2_temp', 'b_modul_3_temp', 'b_modul_4_temp',
            'b_pack_current', 'b_pack_volt', 'kind'
        ]
        
        df = pd.read_csv(csv_path, low_memory=False, usecols=required_cols)
        
        # coll_dt를 datetime으로 변환
        df['coll_dt'] = pd.to_datetime(df['coll_dt'])
        
        # kind='charging'인 구간 추출
        segments = extract_charging_segments(df)
        
        # 각 구간을 통계 데이터로 변환
        results = []
        for idx, seg_df in enumerate(segments):
            result = process_charging_segment(seg_df, csv_path, idx)
            results.append(result)
        
        return results
        
    except Exception as e:
        print(f"[WARN] 파일 처리 실패: {csv_path} ({e})", flush=True)
        return []


def main():
    parser = argparse.ArgumentParser(description="GV60 raw 데이터를 통계 데이터로 변환")
    parser.add_argument(
        '--data-dir',
        type=str,
        default='GV60',
        help='GV60 CSV 파일들이 있는 디렉토리'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='GV60/ev_statistics_fast_slow_stats.csv',
        help='출력 통계 CSV 파일 경로'
    )
    parser.add_argument(
        '--current-threshold',
        type=float,
        default=50.0,
        help='Fast/Slow 충전 구분 기준 전류값 (기본: 50.0A)'
    )
    
    args = parser.parse_args()
    
    data_dir = args.data_dir
    output_path = args.output
    threshold = args.current_threshold
    
    if not os.path.isdir(data_dir):
        print(f"[ERROR] 데이터 디렉토리가 존재하지 않습니다: {data_dir}")
        return
    
    # CSV 파일 찾기
    csv_files = sorted([f for f in os.listdir(data_dir) if f.endswith('.csv')])
    
    if not csv_files:
        print(f"[ERROR] CSV 파일을 찾지 못했습니다: {data_dir}")
        return
    
    print(f"[INFO] 총 {len(csv_files)}개 CSV 파일 발견")
    print(f"[INFO] Fast/Slow 구분 기준 전류: {threshold}A")
    
    # 모든 파일 처리
    all_results = []
    for csv_file in csv_files:
        csv_path = os.path.join(data_dir, csv_file)
        print(f"[INFO] 처리 중: {csv_file}")
        results = process_one_csv_file(csv_path)
        all_results.extend(results)
        print(f"  → {len(results)}개 충전 구간 추출")
    
    if not all_results:
        print("[ERROR] 유효한 충전 구간이 없습니다.")
        return
    
    # DataFrame으로 변환
    df_result = pd.DataFrame(all_results)
    
    # 결과 저장
    df_result.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    print(f"\n[INFO] 통계 CSV 저장 완료: {output_path}")
    print(f"[INFO] 총 {len(df_result)}개 충전 구간")
    print(f"[INFO] Fast 충전: {(df_result['charge_type'] == 'fast').sum()}개")
    print(f"[INFO] Slow 충전: {(df_result['charge_type'] == 'slow').sum()}개")
    print(f"[INFO] 고유 차량 수: {df_result['car_id'].nunique()}개")


if __name__ == '__main__':
    main()


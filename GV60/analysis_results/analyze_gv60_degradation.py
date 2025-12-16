"""
GV60 데이터 배터리 성능 분석 스크립트
- v5, v6 데이터 분석
- Fast/Slow 충전 비교
- 차량별 성능 분석
- 통계 요약 및 시각화
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import platform
import os

# 한글 폰트 설정
if platform.system() == 'Darwin':  # macOS
    matplotlib.rcParams['font.family'] = 'AppleGothic'
    matplotlib.rcParams['axes.unicode_minus'] = False
else:
    matplotlib.rcParams['font.family'] = 'DejaVu Sans'

# 출력 디렉토리
output_dir = 'GV60/analysis_results'
os.makedirs(output_dir, exist_ok=True)

print('='*70)
print('GV60 배터리 성능 분석')
print('='*70)

# 데이터 읽기
print('\n데이터 읽는 중...')
df_v5 = pd.read_csv('GV60/ev_statistics_fast_slow_stats_v5.csv')
df_v6 = pd.read_csv('GV60/ev_statistics_fast_slow_stats_v6.csv')

print(f'v5 (전체): {len(df_v5)}개 차량')
print(f'v6 (3개월 이상): {len(df_v6)}개 차량')

# ============================================================================
# 1. 기본 통계 요약
# ============================================================================
print('\n' + '='*70)
print('1. 기본 통계 요약')
print('='*70)

summary_data = []

indicators = [
    ('fast_degradation_rate_1_per_month', 'Fast Degradation Rate 1 (기본)'),
    ('fast_degradation_rate_2_per_month', 'Fast Degradation Rate 2 (전류 보정)'),
    ('fast_degradation_rate_3_per_month', 'Fast Degradation Rate 3 (전류+온도 보정)'),
    ('slow_degradation_rate_1_per_month', 'Slow Degradation Rate 1 (기본)'),
    ('slow_degradation_rate_2_per_month', 'Slow Degradation Rate 2 (전류 보정)'),
    ('slow_degradation_rate_3_per_month', 'Slow Degradation Rate 3 (전류+온도 보정)'),
]

for indicator, name in indicators:
    v5_data = df_v5[indicator].dropna()
    v6_data = df_v6[indicator].dropna()
    
    if len(v5_data) > 0:
        summary_data.append({
            '지표': name,
            'v5_평균': v5_data.mean(),
            'v5_표준편차': v5_data.std(),
            'v5_중앙값': v5_data.median(),
            'v5_n': len(v5_data),
            'v6_평균': v6_data.mean() if len(v6_data) > 0 else np.nan,
            'v6_표준편차': v6_data.std() if len(v6_data) > 0 else np.nan,
            'v6_중앙값': v6_data.median() if len(v6_data) > 0 else np.nan,
            'v6_n': len(v6_data),
        })

summary_df = pd.DataFrame(summary_data)
summary_df.to_csv(f'{output_dir}/statistics_summary.csv', index=False, encoding='utf-8-sig')
print(f'\n통계 요약 저장: {output_dir}/statistics_summary.csv')
print(summary_df.to_string(index=False))

# ============================================================================
# 2. 차량별 상세 분석
# ============================================================================
print('\n' + '='*70)
print('2. 차량별 상세 분석')
print('='*70)

# v5 데이터로 차량별 분석
vehicle_analysis = []

for _, row in df_v5.iterrows():
    car_id = row['car_id']
    car_type = row['car_type']
    
    # Fast 충전 정보
    fast_info = {}
    if pd.notna(row['first_fast_charging_date']):
        first_fast = pd.to_datetime(row['first_fast_charging_date'])
        last_fast = pd.to_datetime(row['last_fast_charging_date'])
        fast_months = (last_fast - first_fast).days / 30.0
        
        fast_info = {
            'fast_관측기간_개월': fast_months,
            'fast_degradation_rate_3': row['fast_degradation_rate_3'],
            'fast_degradation_rate_3_per_month': row['fast_degradation_rate_3_per_month'],
        }
    
    # Slow 충전 정보
    slow_info = {}
    if pd.notna(row['first_slow_charging_date']):
        first_slow = pd.to_datetime(row['first_slow_charging_date'])
        last_slow = pd.to_datetime(row['last_slow_charging_date'])
        slow_months = (last_slow - first_slow).days / 30.0
        
        slow_info = {
            'slow_관측기간_개월': slow_months,
            'slow_degradation_rate_3': row['slow_degradation_rate_3'],
            'slow_degradation_rate_3_per_month': row['slow_degradation_rate_3_per_month'],
        }
    
    vehicle_analysis.append({
        'car_id': car_id,
        'car_type': car_type,
        **fast_info,
        **slow_info,
    })

vehicle_df = pd.DataFrame(vehicle_analysis)
vehicle_df.to_csv(f'{output_dir}/vehicle_analysis.csv', index=False, encoding='utf-8-sig')
print(f'\n차량별 분석 저장: {output_dir}/vehicle_analysis.csv')
print(vehicle_df.to_string(index=False))

# ============================================================================
# 3. Fast vs Slow 충전 비교
# ============================================================================
print('\n' + '='*70)
print('3. Fast vs Slow 충전 비교')
print('='*70)

# v6 데이터 기준 (3개월 이상, 신뢰도 높은 데이터)
fast_v6 = df_v6['fast_degradation_rate_3_per_month'].dropna()
slow_v6 = df_v6['slow_degradation_rate_3_per_month'].dropna()

if len(fast_v6) > 0 and len(slow_v6) > 0:
    comparison = {
        '충전타입': ['Fast', 'Slow'],
        '평균_%/월': [fast_v6.mean(), slow_v6.mean()],
        '표준편차': [fast_v6.std(), slow_v6.std()],
        '중앙값': [fast_v6.median(), slow_v6.median()],
        '최소값': [fast_v6.min(), slow_v6.min()],
        '최대값': [fast_v6.max(), slow_v6.max()],
        '샘플수': [len(fast_v6), len(slow_v6)],
    }
    comparison_df = pd.DataFrame(comparison)
    comparison_df.to_csv(f'{output_dir}/fast_vs_slow_comparison.csv', index=False, encoding='utf-8-sig')
    print(f'\nFast vs Slow 비교 저장: {output_dir}/fast_vs_slow_comparison.csv')
    print(comparison_df.to_string(index=False))

# ============================================================================
# 4. 시각화: Fast vs Slow 비교
# ============================================================================
print('\n' + '='*70)
print('4. 시각화 생성 중...')
print('='*70)

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Fast vs Slow 박스플롯 (v6 데이터)
if len(fast_v6) > 0 and len(slow_v6) > 0:
    ax1 = axes[0]
    box_data = [fast_v6, slow_v6]
    bp = ax1.boxplot(box_data, labels=['Fast', 'Slow'], patch_artist=True, showmeans=True)
    
    colors = ['lightblue', 'lightcoral']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax1.set_title('Fast vs Slow Degradation Rate 비교 (v6, 3개월 이상)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Degradation Rate (%/month)')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='0% (성능 변화 없음)')
    ax1.legend()

# 차량별 degradation rate (v6)
ax2 = axes[1]
v6_with_both = df_v6[
    df_v6['fast_degradation_rate_3_per_month'].notna() & 
    df_v6['slow_degradation_rate_3_per_month'].notna()
]

if len(v6_with_both) > 0:
    x = range(len(v6_with_both))
    width = 0.35
    
    ax2.bar([i - width/2 for i in x], v6_with_both['fast_degradation_rate_3_per_month'], 
            width, label='Fast', color='lightblue', alpha=0.7)
    ax2.bar([i + width/2 for i in x], v6_with_both['slow_degradation_rate_3_per_month'], 
            width, label='Slow', color='lightcoral', alpha=0.7)
    
    ax2.set_xlabel('차량')
    ax2.set_ylabel('Degradation Rate (%/month)')
    ax2.set_title('차량별 Fast vs Slow Degradation Rate (v6)', fontsize=12, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels([car_id[:8] for car_id in v6_with_both['car_id']], rotation=45, ha='right')
    ax2.axhline(y=0, color='red', linestyle='--', alpha=0.5)
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(f'{output_dir}/fast_vs_slow_analysis.png', dpi=300, bbox_inches='tight')
print(f'Fast vs Slow 비교 그래프 저장: {output_dir}/fast_vs_slow_analysis.png')

# ============================================================================
# 5. 관측 기간별 분석
# ============================================================================
print('\n' + '='*70)
print('5. 관측 기간별 분석')
print('='*70)

period_analysis = []

for _, row in df_v5.iterrows():
    # Fast 관측 기간
    if pd.notna(row['first_fast_charging_date']):
        first = pd.to_datetime(row['first_fast_charging_date'])
        last = pd.to_datetime(row['last_fast_charging_date'])
        months = (last - first).days / 30.0
        
        period_analysis.append({
            'car_id': row['car_id'],
            '충전타입': 'Fast',
            '관측기간_개월': months,
            'degradation_rate_3_per_month': row['fast_degradation_rate_3_per_month'],
        })
    
    # Slow 관측 기간
    if pd.notna(row['first_slow_charging_date']):
        first = pd.to_datetime(row['first_slow_charging_date'])
        last = pd.to_datetime(row['last_slow_charging_date'])
        months = (last - first).days / 30.0
        
        period_analysis.append({
            'car_id': row['car_id'],
            '충전타입': 'Slow',
            '관측기간_개월': months,
            'degradation_rate_3_per_month': row['slow_degradation_rate_3_per_month'],
        })

period_df = pd.DataFrame(period_analysis)
period_df.to_csv(f'{output_dir}/observation_period_analysis.csv', index=False, encoding='utf-8-sig')
print(f'\n관측 기간별 분석 저장: {output_dir}/observation_period_analysis.csv')

# 관측 기간별 그룹화
if len(period_df) > 0:
    period_summary = period_df.groupby('충전타입').agg({
        '관측기간_개월': ['mean', 'min', 'max', 'std'],
        'degradation_rate_3_per_month': ['mean', 'std', 'count']
    }).round(2)
    print('\n관측 기간별 요약:')
    print(period_summary)

# ============================================================================
# 6. 종합 리포트 생성
# ============================================================================
print('\n' + '='*70)
print('6. 종합 리포트 생성')
print('='*70)

report = f"""
GV60 배터리 성능 분석 리포트
생성일: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

================================================================================
1. 데이터 개요
================================================================================
- 전체 차량 수 (v5): {len(df_v5)}개
- 3개월 이상 차량 수 (v6): {len(df_v6)}개
- Fast 충전 데이터 보유 차량: {df_v5['fast_degradation_rate_3_per_month'].notna().sum()}개 (v5), {df_v6['fast_degradation_rate_3_per_month'].notna().sum()}개 (v6)
- Slow 충전 데이터 보유 차량: {df_v5['slow_degradation_rate_3_per_month'].notna().sum()}개 (v5), {df_v6['slow_degradation_rate_3_per_month'].notna().sum()}개 (v6)

================================================================================
2. 주요 결과 (v6, 3개월 이상 데이터 기준)
================================================================================
"""

if len(fast_v6) > 0:
    report += f"""
Fast 충전 Degradation Rate (slope_3 기준):
- 평균: {fast_v6.mean():.4f} %/월
- 표준편차: {fast_v6.std():.4f} %/월
- 중앙값: {fast_v6.median():.4f} %/월
- 범위: {fast_v6.min():.4f} ~ {fast_v6.max():.4f} %/월
- 샘플 수: {len(fast_v6)}개
"""

if len(slow_v6) > 0:
    report += f"""
Slow 충전 Degradation Rate (slope_3 기준):
- 평균: {slow_v6.mean():.4f} %/월
- 표준편차: {slow_v6.std():.4f} %/월
- 중앙값: {slow_v6.median():.4f} %/월
- 범위: {slow_v6.min():.4f} ~ {slow_v6.max():.4f} %/월
- 샘플 수: {len(slow_v6)}개
"""

report += f"""
================================================================================
3. 해석
================================================================================
- Degradation Rate가 음수인 경우: 성능이 증가한 것으로 측정됨 (측정 오차 가능)
- Degradation Rate가 양수인 경우: 성능이 감소한 것으로 측정됨 (정상적인 노화)
- v6 (3개월 이상) 데이터가 더 신뢰도 높은 결과를 제공합니다.

================================================================================
4. 생성된 파일
================================================================================
- statistics_summary.csv: 통계 요약
- vehicle_analysis.csv: 차량별 상세 분석
- fast_vs_slow_comparison.csv: Fast vs Slow 비교
- observation_period_analysis.csv: 관측 기간별 분석
- fast_vs_slow_analysis.png: Fast vs Slow 비교 그래프
"""

with open(f'{output_dir}/analysis_report.txt', 'w', encoding='utf-8') as f:
    f.write(report)

print(report)
print(f'\n종합 리포트 저장: {output_dir}/analysis_report.txt')

print('\n' + '='*70)
print('분석 완료!')
print('='*70)
print(f'모든 결과는 {output_dir}/ 디렉토리에 저장되었습니다.')


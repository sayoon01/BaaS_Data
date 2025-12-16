import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import platform

# macOS에서 한글 폰트 설정
if platform.system() == 'Darwin':  # macOS
    # macOS에서 사용 가능한 한글 폰트
    matplotlib.rcParams['font.family'] = 'AppleGothic'
    matplotlib.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지
else:
    matplotlib.rcParams['font.family'] = 'DejaVu Sans'

# CSV 파일 읽기
print("CSV 파일 읽는 중...")
df_v5 = pd.read_csv('GV60/ev_statistics_fast_slow_stats_v5.csv')
df_v6 = pd.read_csv('GV60/ev_statistics_fast_slow_stats_v6.csv')

print(f"v5 파일 행 수: {len(df_v5)}")
print(f"v6 파일 행 수: {len(df_v6)}")

# 6개 지표 리스트
indicators = [
    'fast_degradation_rate_1_per_month',
    'fast_degradation_rate_2_per_month',
    'fast_degradation_rate_3_per_month',
    'slow_degradation_rate_1_per_month',
    'slow_degradation_rate_2_per_month',
    'slow_degradation_rate_3_per_month'
]

# 지표 이름 (그래프에 표시용)
indicator_names = [
    'Fast Degradation Rate 1 (per month)',
    'Fast Degradation Rate 2 (per month)',
    'Fast Degradation Rate 3 (per month)',
    'Slow Degradation Rate 1 (per month)',
    'Slow Degradation Rate 2 (per month)',
    'Slow Degradation Rate 3 (per month)'
]

# 각 지표별로 박스플롯 생성
fig, axes = plt.subplots(2, 3, figsize=(18, 12))
axes = axes.flatten()

for idx, (indicator, name) in enumerate(zip(indicators, indicator_names)):
    ax = axes[idx]
    
    # v5와 v6 데이터 추출 (NaN 제외)
    v5_data = df_v5[indicator].dropna()
    v6_data = df_v6[indicator].dropna()
    
    # 박스플롯 데이터 준비
    box_data = [v5_data, v6_data]
    labels = ['v5 (전체)', 'v6 (3개월 이상)']
    
    # 박스플롯 그리기
    bp = ax.boxplot(box_data, labels=labels, patch_artist=True, 
                    showmeans=True, meanline=True)
    
    # 박스 색상 설정
    colors = ['lightblue', 'lightcoral']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    # 통계 정보 계산
    v5_mean = v5_data.mean()
    v5_std = v5_data.std()
    v5_count = len(v5_data)
    
    v6_mean = v6_data.mean()
    v6_std = v6_data.std()
    v6_count = len(v6_data)
    
    # 제목 설정
    ax.set_title(f'{name}\n'
                 f'v5: 평균={v5_mean:.4f}, 표준편차={v5_std:.4f}, n={v5_count}\n'
                 f'v6: 평균={v6_mean:.4f}, 표준편차={v6_std:.4f}, n={v6_count}',
                 fontsize=10)
    ax.set_ylabel('Degradation Rate (%/month)')
    ax.grid(True, alpha=0.3)

plt.suptitle('Degradation Rate per Month 비교 (v5 vs v6)', fontsize=16, fontweight='bold')
plt.tight_layout()

# PNG 파일로 저장
output_file = 'GV60/degradation_rate_comparison.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"\n그래프 저장 완료: {output_file}")

# 통계 요약 출력
print("\n=== 통계 요약 ===")
print(f"{'지표':<40} {'v5 평균':>12} {'v5 표준편차':>15} {'v5 n':>8} {'v6 평균':>12} {'v6 표준편차':>15} {'v6 n':>8}")
print("-" * 110)

for indicator, name in zip(indicators, indicator_names):
    v5_data = df_v5[indicator].dropna()
    v6_data = df_v6[indicator].dropna()
    
    if len(v5_data) > 0:
        v5_mean = v5_data.mean()
        v5_std = v5_data.std()
    else:
        v5_mean = np.nan
        v5_std = np.nan
    
    if len(v6_data) > 0:
        v6_mean = v6_data.mean()
        v6_std = v6_data.std()
    else:
        v6_mean = np.nan
        v6_std = np.nan
    
    print(f"{name:<40} {v5_mean:>12.4f} {v5_std:>15.4f} {len(v5_data):>8} "
          f"{v6_mean:>12.4f} {v6_std:>15.4f} {len(v6_data):>8}")

print("\n완료!")

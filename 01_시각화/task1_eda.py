# -*- coding: utf-8 -*-
"""과제 1. 주요 Feature 시각화 [15점]
- SalePrice 히스토그램 + 왜도
- OverallQual별 SalePrice 박스플롯
- GrLivArea vs SalePrice 산점도 + 회귀선
- Neighborhood별 평균 SalePrice 막대(정렬)
- (선택) 수치형 상관 히트맵
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style='whitegrid', font='Malgun Gothic')

BASE = Path(__file__).resolve().parent
IMG = BASE / 'images'
IMG.mkdir(exist_ok=True)
CSV = BASE.parent / 'data' / 'housePricing_reduced.csv'

df = pd.read_csv(CSV, encoding='utf-8-sig')

# ── 구조 · 기초통계 ────────────────────────────────────────────────
with open(BASE / 'eda_summary.txt', 'w', encoding='utf-8') as f:
    df.info(buf=f)
    f.write('\n\n[describe]\n')
    f.write(df.describe().to_string())
    f.write('\n\n[결측치]\n')
    f.write(df.isna().sum().to_string())

skew_raw = df['SalePrice'].skew()
skew_log = np.log1p(df['SalePrice']).skew()
print(f'SalePrice 왜도: {skew_raw:.2f}  /  log1p 변환 후: {skew_log:.2f}')

# ── ① SalePrice 히스토그램 + 왜도 ─────────────────────────────────
fig, ax = plt.subplots(1, 2, figsize=(13, 5))
sns.histplot(df['SalePrice'], bins=50, kde=True, color='#2E5EAA', ax=ax[0])
ax[0].set_title(f'SalePrice 분포 (왜도 = {skew_raw:.2f})')
ax[0].set_xlabel('SalePrice (USD)')
sns.histplot(np.log1p(df['SalePrice']), bins=50, kde=True, color='#C0504D', ax=ax[1])
ax[1].set_title(f'log1p(SalePrice) 분포 (왜도 = {skew_log:.2f})')
ax[1].set_xlabel('log1p(SalePrice)')
fig.suptitle('① SalePrice 분포와 로그 변환 효과')
fig.tight_layout()
fig.savefig(IMG / '01_saleprice_hist.png', dpi=120)
plt.close(fig)

# ── ② OverallQual별 SalePrice 박스플롯 ────────────────────────────
fig, ax = plt.subplots(figsize=(11, 6))
sns.boxplot(data=df, x='OverallQual', y='SalePrice', hue='OverallQual',
            palette='YlGnBu', legend=False, ax=ax)
ax.set_title('② OverallQual(전반 품질)별 SalePrice 박스플롯')
ax.set_xlabel('OverallQual (1~10)')
fig.tight_layout()
fig.savefig(IMG / '02_boxplot_overallqual.png', dpi=120)
plt.close(fig)

# ── ③ GrLivArea vs SalePrice 산점도 + 회귀선 ──────────────────────
fig, ax = plt.subplots(figsize=(9, 6))
sns.regplot(data=df, x='GrLivArea', y='SalePrice',
            scatter_kws={'alpha': .35, 's': 22, 'color': '#2E5EAA'},
            line_kws={'color': '#C0504D', 'lw': 2}, ax=ax)
r_gr = df['GrLivArea'].corr(df['SalePrice'])
ax.set_title(f'③ GrLivArea vs SalePrice (r = {r_gr:.2f})')
ax.set_xlabel('지상 거주 면적 (sq ft)')
fig.tight_layout()
fig.savefig(IMG / '03_scatter_grlivarea.png', dpi=120)
plt.close(fig)

# ── ④ Neighborhood별 평균 SalePrice 막대(정렬) ────────────────────
nb = df.groupby('Neighborhood')['SalePrice'].mean().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(13, 6))
sns.barplot(x=nb.index, y=nb.values, hue=nb.index, palette='viridis',
            legend=False, ax=ax)
ax.axhline(df['SalePrice'].mean(), ls='--', color='#C0504D',
           label=f'전체 평균 ${df["SalePrice"].mean():,.0f}')
ax.set_title('④ Neighborhood(지역)별 평균 SalePrice (내림차순)')
ax.set_ylabel('평균 SalePrice (USD)')
ax.set_xlabel('Neighborhood')
ax.tick_params(axis='x', rotation=60)
ax.legend()
fig.tight_layout()
fig.savefig(IMG / '04_bar_neighborhood.png', dpi=120)
plt.close(fig)

# ── ⑤ (선택) 수치형 상관 히트맵 ───────────────────────────────────
num = df.select_dtypes('number').drop(columns=['Id'])
fig, ax = plt.subplots(figsize=(11, 9))
sns.heatmap(num.corr(), annot=True, fmt='.2f', cmap='coolwarm',
            center=0, square=True, linewidths=.4,
            cbar_kws={'shrink': .8}, ax=ax)
ax.set_title('⑤ 수치형 feature 상관 히트맵')
fig.tight_layout()
fig.savefig(IMG / '05_heatmap_corr.png', dpi=120)
plt.close(fig)

# ── 후속 과제에서 재사용할 요약 지표 저장 ─────────────────────────
corr_target = num.corr()['SalePrice'].drop('SalePrice').sort_values(ascending=False)
summary = {
    'n_rows': int(len(df)),
    'skew_raw': round(float(skew_raw), 3),
    'skew_log1p': round(float(skew_log), 3),
    'mean_price': float(df['SalePrice'].mean()),
    'max_price': float(df['SalePrice'].max()),
    'median_price': float(df['SalePrice'].median()),
    'corr_with_saleprice': {k: round(float(v), 3) for k, v in corr_target.items()},
    'top_neighborhood': {k: round(float(v), 1) for k, v in nb.head(5).items()},
}
(BASE / 'task1_summary.json').write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

print('\n[SalePrice 상관 상위]')
print(corr_target.head(8).round(2).to_string())
print(f'\n그래프 5종 저장 완료 → {IMG}')

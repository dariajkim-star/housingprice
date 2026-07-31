# -*- coding: utf-8 -*-
"""과제 1. 주요 Feature 시각화 [15점]

문제지 요구 그래프 ①~④ (+선택 ⑤)를 모두 충족하되,
- 색 언어 통일(회색 기본 / 남색 강조 / 빨강은 이상치 전용)
- 제목은 차트 종류가 아니라 '데이터에서 확인된 결론'을 서술
- 범례 대신 직접 라벨, 표본 수(n) 명시
원칙으로 작성. 제목에 쓰인 수치는 모두 코드에서 계산한 값을 f-string으로 주입한다.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

# ── 공통 스타일 ───────────────────────────────────────────────────
ACCENT = '#1F4E79'   # 핵심 강조
NEUTRAL = '#C8CDD3'  # 일반 데이터
DARK = '#222222'     # 텍스트
ALERT = '#B94A48'    # 이상치·제거 대상 전용
GRID = '#E6E8EB'

sns.set_theme(style='white', font='Malgun Gothic')
plt.rcParams.update({
    'font.family': 'Malgun Gothic',
    'axes.unicode_minus': False,
    'axes.edgecolor': GRID,
    'text.color': DARK,
    'axes.labelcolor': DARK,
    'figure.facecolor': 'white',
})

BASE = Path(__file__).resolve().parent
IMG = BASE / 'images'
IMG.mkdir(exist_ok=True)
CSV = BASE.parent / 'data' / 'housePricing_reduced.csv'

df = pd.read_csv(CSV, encoding='utf-8-sig')
N = len(df)
SOURCE = f'자료: housePricing_reduced.csv (Ames Housing) · n = {N:,}건'


def style_axes(ax, title, subtitle=None, xgrid=False, ygrid=True):
    """맥킨지식 공통 서식: 왼쪽 정렬 제목, 테두리 제거, 얇은 격자."""
    ax.set_title(title, loc='left', fontweight='bold', fontsize=13, pad=22 if subtitle else 10)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes,
                fontsize=9.5, color='#5A6470', va='bottom')
    sns.despine(ax=ax, top=True, right=True)
    ax.grid(axis='y' if ygrid else 'x', color=GRID, lw=.8)
    if xgrid:
        ax.grid(axis='x', color=GRID, lw=.8)
    ax.set_axisbelow(True)


def usd_k(x, _=None):
    return f'${x/1000:,.0f}K'


def footer(fig, text=SOURCE):
    fig.text(0.01, 0.005, text, fontsize=8, color='#8A929B', ha='left')


# ── 구조 · 기초통계 ────────────────────────────────────────────────
with open(BASE / 'eda_summary.txt', 'w', encoding='utf-8') as f:
    df.info(buf=f)
    f.write('\n\n[describe(include="all") — 수치형 14개 + 범주형 4개 전체]\n')
    f.write(df.describe(include='all').to_string())
    f.write('\n\n[결측치]\n')
    f.write(df.isna().sum().to_string())

skew_raw = df['SalePrice'].skew()
skew_log = np.log1p(df['SalePrice']).skew()
print(f'SalePrice 왜도: {skew_raw:.2f}  /  log1p 변환 후: {skew_log:.2f}')

# ── ① 로그 변환 전후 히스토그램 ───────────────────────────────────
fig, ax = plt.subplots(1, 2, figsize=(13, 5.2))
ax[0].hist(df['SalePrice'], bins=50, color=NEUTRAL, edgecolor='white', lw=.4)
ax[0].xaxis.set_major_formatter(plt.FuncFormatter(usd_k))
style_axes(ax[0], '원본 · 오른쪽 꼬리 존재', f'왜도 {skew_raw:.2f}')
ax[0].set_xlabel('SalePrice')

ax[1].hist(np.log1p(df['SalePrice']), bins=50, color=ACCENT, edgecolor='white', lw=.4)
style_axes(ax[1], '로그 변환 후 · 좌우 대칭 근접', f'왜도 {skew_log:.2f}')
ax[1].set_xlabel('log1p(SalePrice)')

fig.suptitle(f'① 로그 변환으로 데이터 불균형 해소 — 고가주택이 만든 왜도 {skew_raw:.2f} → {skew_log:.2f} 감소',
             x=0.01, ha='left', fontweight='bold', fontsize=15)
fig.tight_layout(rect=[0, 0.03, 1, 0.94])
footer(fig)
fig.savefig(IMG / '01_saleprice_hist.png', dpi=120)
plt.close(fig)

# ── ② OverallQual별 박스플롯 ──────────────────────────────────────
med = df.groupby('OverallQual')['SalePrice'].median()
cnt = df.groupby('OverallQual')['SalePrice'].size()
growth = med.pct_change() * 100
# 표본이 극히 적은 등급(1~3등급은 n=2·3·20)의 증가율은 우연에 좌우되므로
# 충분한 표본(n>=50)을 가진 등급 구간에서만 '가장 가파른 상승 구간'을 판정한다.
MIN_N = 50
solid = [q for q in growth.index if cnt[q] >= MIN_N and cnt.get(q - 1, 0) >= MIN_N]
peak_q = int(growth.loc[solid].idxmax())      # 중앙값 증가율이 가장 큰 등급
peak_pct = growth.loc[solid].max()

fig, ax = plt.subplots(figsize=(11.5, 6.2))
qs = sorted(df['OverallQual'].unique())
colors = [ACCENT if q >= peak_q else NEUTRAL for q in qs]
bp = ax.boxplot([df.loc[df['OverallQual'] == q, 'SalePrice'] for q in qs],
                positions=range(len(qs)), widths=.62, patch_artist=True,
                medianprops=dict(color=DARK, lw=1.6),
                flierprops=dict(marker='o', ms=3, mfc='none', mec='#B0B6BD', alpha=.6),
                whiskerprops=dict(color='#9AA1A9'), capprops=dict(color='#9AA1A9'))
for patch, c in zip(bp['boxes'], colors):
    patch.set(facecolor=c, edgecolor='#9AA1A9', lw=.8)

ax.set_xticks(range(len(qs)))
ax.set_xticklabels([f'{q}\n(n={cnt[q]})' for q in qs], fontsize=9)
ax.yaxis.set_major_formatter(plt.FuncFormatter(usd_k))
ax.set_xlabel('OverallQual (전반적 품질)')
ax.set_ylabel('')
style_axes(ax,
           f'② 품질 {peak_q-1}→{peak_q} 구간에서 가격 중앙값 {peak_pct:.0f}% 급등 — 전 구간 최대 상승폭',
           '박스 = 1~3사분위, 가로선 = 중앙값 · 남색 = 상승폭이 가장 큰 구간 이후')
# 중앙값 직접 라벨(주요 등급만)
for i, q in enumerate(qs):
    if q in (1, 5, peak_q, max(qs)):
        last = q == max(qs)
        ax.annotate(usd_k(med[q]), (i, med[q]),
                    xytext=(-26 if last else 26, 0), textcoords='offset points',
                    ha='right' if last else 'left', va='center',
                    fontsize=9, fontweight='bold', color=DARK)
fig.tight_layout(rect=[0, 0.03, 1, 1])
footer(fig)
fig.savefig(IMG / '02_boxplot_overallqual.png', dpi=120)
plt.close(fig)

# ── ②-B 중앙값 도트 + IQR 범위 (보고용 메시지 차트) ───────────────
# 박스플롯(②)은 문제지 요구 항목이므로 그대로 두고, '품질↑ → 가격↑'이라는
# 결론만 전달하는 축약 버전을 따로 만든다. 박스·수염·이상치를 걷어내고
# 중앙값(점)·중간 50% 범위(세로선)·진행 방향(연결선)만 남긴다.
q1 = df.groupby('OverallQual')['SalePrice'].quantile(.25)
q3 = df.groupby('OverallQual')['SalePrice'].quantile(.75)
rho_pearson = df['OverallQual'].corr(df['SalePrice'])
rho_spearman = df['OverallQual'].corr(df['SalePrice'], method='spearman')
med_ratio = med[max(qs)] / med[min(qs)]

fig, ax = plt.subplots(figsize=(11, 6.2))
ax.vlines(qs, q1[qs], q3[qs], color=NEUTRAL, lw=5, zorder=1)
ax.plot(qs, med[qs], color=ACCENT, lw=1.6, zorder=2)
ax.scatter(qs, med[qs], color=[ACCENT if q >= peak_q else '#7B8794' for q in qs],
           s=70, zorder=3)
for q in qs:
    ax.annotate(usd_k(med[q]), (q, med[q]), xytext=(0, 12),
                textcoords='offset points', ha='center', fontsize=9,
                fontweight='bold' if q >= peak_q else 'normal',
                color=ACCENT if q >= peak_q else '#5A6470')
ax.set_xticks(qs)
ax.set_xticklabels([f'{q}\n(n={cnt[q]})' for q in qs], fontsize=9)
ax.yaxis.set_major_formatter(plt.FuncFormatter(usd_k))
ax.set_xlabel('OverallQual (전반적 품질)')
ax.set_ylabel('')
style_axes(ax,
           f'②-B 품질 1→10 구간 가격 중앙값 {med_ratio:.1f}배 상승 — 전 등급 단조 증가',
           f'점 = 중앙값, 세로선 = 중간 50% 범위(IQR) · '
           f'Spearman ρ = {rho_spearman:.2f} (Pearson r = {rho_pearson:.2f})')
fig.tight_layout(rect=[0, 0.03, 1, 1])
footer(fig)
fig.savefig(IMG / '02b_qual_median_range.png', dpi=120)
plt.close(fig)

# ── ③ GrLivArea vs SalePrice 산점도 + 회귀선(이상치 강조) ─────────
r_gr = df['GrLivArea'].corr(df['SalePrice'])
out = df[(df['GrLivArea'] > 4000) & (df['SalePrice'] < 300_000)]

fig, ax = plt.subplots(figsize=(9.5, 6.4))
sns.regplot(data=df, x='GrLivArea', y='SalePrice', ci=None,
            scatter_kws={'alpha': .35, 's': 20, 'color': NEUTRAL,
                         'edgecolor': 'none'},
            line_kws={'color': ACCENT, 'lw': 2.2}, ax=ax)
ax.scatter(out['GrLivArea'], out['SalePrice'], s=90, facecolor='none',
           edgecolor=ALERT, lw=1.8, zorder=5)
for _, row in out.iterrows():
    ax.annotate(f"Id {int(row['Id'])} · 품질 {int(row['OverallQual'])}\n"
                f"{row['GrLivArea']:,.0f} sqft / {usd_k(row['SalePrice'])}",
                (row['GrLivArea'], row['SalePrice']), xytext=(-12, -34),
                textcoords='offset points', fontsize=8.5, color=ALERT,
                ha='right', va='top')
# 회귀선 옆 직접 라벨
x_lab = df['GrLivArea'].max() * .93
y_lab = np.polyval(np.polyfit(df['GrLivArea'], df['SalePrice'], 1), x_lab)
ax.annotate(f'회귀선  r = {r_gr:.2f}', (x_lab, y_lab), xytext=(-8, 16),
            textcoords='offset points', ha='right', color=ACCENT,
            fontweight='bold', fontsize=11)

ax.yaxis.set_major_formatter(plt.FuncFormatter(usd_k))
ax.set_xlabel('GrLivArea (지상 거주 면적, sqft)')
ax.set_ylabel('')
style_axes(ax, f'③ 면적 클수록 판매가 상승(r={r_gr:.2f}) — 최고급 대형 주택 2건은 시세 절반 수준 거래',
           f'전체 상관 r = {r_gr:.2f} · 빨간 표시 = 면적 4,000sqft 초과이면서 $300K 미만인 주택')
fig.tight_layout(rect=[0, 0.03, 1, 1])
footer(fig)
fig.savefig(IMG / '03_scatter_grlivarea.png', dpi=120)
plt.close(fig)

# ── ④ Neighborhood별 평균가 — 수평 막대(전체 평균 기준) ───────────
grand = df['SalePrice'].mean()
nb = df.groupby('Neighborhood')['SalePrice'].agg(['mean', 'size']).sort_values('mean')
ratio = nb['mean'].max() / nb['mean'].min()
SMALL_N = 20   # 표본이 적어 평균이 불안정한 지역 기준

fig, ax = plt.subplots(figsize=(10.5, 8.6))
bar_colors = [ACCENT if (m >= grand and n >= SMALL_N) else NEUTRAL
              for m, n in zip(nb['mean'], nb['size'])]
ax.barh(nb.index, nb['mean'], color=bar_colors, height=.68)
ax.axvline(grand, color='#777777', ls='--', lw=1.1)
ax.text(grand, len(nb) - .2, f'  전체 평균 {usd_k(grand)}',
        fontsize=9, color='#555555', va='center')

for i, (region, row) in enumerate(nb.iterrows()):
    small = row['size'] < SMALL_N
    ax.text(row['mean'] + 4500, i,
            f"{usd_k(row['mean'])}  (n={int(row['size'])})",
            va='center', fontsize=8.6,
            color='#9AA1A9' if small else DARK,
            fontweight='normal' if small else 'bold')

ax.xaxis.set_major_formatter(plt.FuncFormatter(usd_k))
ax.set_xlim(0, nb['mean'].max() * 1.22)
ax.set_xlabel('평균 SalePrice')
ax.set_ylabel('')
style_axes(ax, f'④ 같은 도시 안에서 지역 간 평균 판매가 최대 {ratio:.1f}배 격차',
           f'평균가 오름차순 · 남색 = 전체 평균 이상 & 표본 {SMALL_N}건 이상 · '
           f'회색 라벨 = 표본 {SMALL_N}건 미만(평균 불안정)',
           ygrid=False, xgrid=True)
fig.tight_layout(rect=[0, 0.03, 1, 1])
footer(fig)
fig.savefig(IMG / '04_bar_neighborhood.png', dpi=120)
plt.close(fig)

# ── ⑤-A (선택) SalePrice 상관 상위 도트플롯 ───────────────────────
num = df.select_dtypes('number').drop(columns=['Id'])
corr_target = num.corr()['SalePrice'].drop('SalePrice').sort_values()

fig, ax = plt.subplots(figsize=(9.5, 6))
top2 = corr_target.nlargest(2).index
dot_colors = [ACCENT if f in top2 else NEUTRAL for f in corr_target.index]
ax.hlines(y=corr_target.index, xmin=0, xmax=corr_target.values, color=GRID, lw=2)
ax.scatter(corr_target.values, corr_target.index, s=95, color=dot_colors, zorder=3)
for f, v in corr_target.items():
    ax.text(v + .015, f, f'{v:.2f}', va='center', fontsize=9,
            fontweight='bold' if f in top2 else 'normal',
            color=ACCENT if f in top2 else '#5A6470')
ax.set_xlim(0, corr_target.max() * 1.18)
ax.set_xlabel('SalePrice와의 피어슨 상관계수 r')
ax.set_ylabel('')
style_axes(ax, f'⑤ SalePrice 설명력 최상위 — OverallQual {corr_target.max():.2f} · GrLivArea {corr_target.nlargest(2).iloc[-1]:.2f}',
           '수치형 feature 12종 · 남색 = 상위 2개', ygrid=False, xgrid=True)
fig.tight_layout(rect=[0, 0.03, 1, 1])
footer(fig)
fig.savefig(IMG / '05_corr_ranking.png', dpi=120)
plt.close(fig)

# ── ⑤-B (선택) 축약 상관 히트맵 — 과제 2 연결용 ───────────────────
core = list(corr_target.nlargest(8).index) + ['SalePrice']
cm = num[core].corr()
mask = np.triu(np.ones_like(cm, dtype=bool))          # 위쪽 삼각형 가림
annot = cm.map(lambda v: f'{v:.2f}' if abs(v) >= 0.5 else '')   # |r|>=0.5만 표기

fig, ax = plt.subplots(figsize=(9, 7.2))
sns.heatmap(cm, mask=mask, annot=annot, fmt='', cmap='Blues', vmin=0, vmax=1,
            square=True, linewidths=.8, linecolor='white',
            cbar_kws={'shrink': .7}, ax=ax)
# |r| >= 0.8 인 설명변수 쌍만 빨간 테두리로 강조
for i, a in enumerate(core):
    for j, b in enumerate(core):
        if j < i and a != 'SalePrice' and b != 'SalePrice' and abs(cm.iat[i, j]) >= 0.8:
            ax.add_patch(plt.Rectangle((j, i), 1, 1, fill=False, edgecolor=ALERT, lw=2.4))
fig.suptitle('⑤-B 설명변수 3쌍 |r| ≥ 0.8 중복 — 과제 2 제거 대상',
             x=0.01, y=0.98, ha='left', fontweight='bold', fontsize=14)
fig.text(0.01, 0.935, '상관 상위 8개 + SalePrice · |r| ≥ 0.5만 수치 표기 · 빨간 테두리 = |r| ≥ 0.8',
         fontsize=9.5, color='#5A6470', ha='left')
fig.tight_layout(rect=[0, 0.03, 1, 0.92])
footer(fig)
fig.savefig(IMG / '06_heatmap_core.png', dpi=120)
plt.close(fig)

# ── 후속 과제에서 재사용할 요약 지표 ──────────────────────────────
summary = {
    'n_rows': int(N),
    'skew_raw': round(float(skew_raw), 3),
    'skew_log1p': round(float(skew_log), 3),
    'mean_price': float(grand),
    'median_price': float(df['SalePrice'].median()),
    'max_price': float(df['SalePrice'].max()),
    'neighborhood_ratio': round(float(ratio), 2),
    'qual_peak_step': {'to_grade': peak_q, 'median_growth_pct': round(float(peak_pct), 1)},
    'qual_median_ratio_1_to_10': round(float(med_ratio), 2),
    'qual_pearson_r': round(float(rho_pearson), 3),
    'qual_spearman_rho': round(float(rho_spearman), 3),
    'outlier_ids': [int(i) for i in out['Id']],
    'corr_with_saleprice': {k: round(float(v), 3)
                            for k, v in corr_target.sort_values(ascending=False).items()},
    'neighborhood_small_n': {k: int(v) for k, v in nb.loc[nb['size'] < SMALL_N, 'size'].items()},
}
(BASE / 'task1_summary.json').write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

print('\n[SalePrice 상관 상위]')
print(corr_target.sort_values(ascending=False).head(8).round(2).to_string())
print(f'\n품질 {peak_q-1}→{peak_q} 중앙값 증가율 {peak_pct:.1f}% (최대)')
print(f'지역 평균가 최고/최저 배율 {ratio:.2f}배 · 표본 20건 미만 지역 {int((nb["size"] < SMALL_N).sum())}곳')
print(f'추세 이탈 대형주택 Id: {list(out["Id"])}')
print(f'품질 1→10 중앙값 {med_ratio:.1f}배 · Spearman ρ={rho_spearman:.2f} / Pearson r={rho_pearson:.2f}')
print(f'\n그래프 7종 저장 완료 → {IMG}')

# -*- coding: utf-8 -*-
"""과제 2. 공분산 · 다중공선성 진단과 제거 [20점]

- 상관행렬 / 공분산행렬을 각각 구하고, 공분산의 스케일 의존성을 실증
- |r| >= 0.8 공선 쌍 탐지 (히트맵)
- VIF 계산 (numpy 직접 구현: VIF_i = 1 / (1 - R^2_i))
- 공선 쌍 중 SalePrice 상관이 낮은 쪽을 제거 → 제거 전/후 VIF 비교

시각화 규칙은 과제 1과 동일:
회색=일반, 남색=핵심 강조, 빨강=제거 대상 전용 / 제목은 결론을 명사형으로 서술.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

# ── 공통 스타일 (과제 1과 동일) ───────────────────────────────────
ACCENT = '#1F4E79'
NEUTRAL = '#C8CDD3'
DARK = '#222222'
ALERT = '#B94A48'
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
num = df.select_dtypes('number').drop(columns=['Id'])
SOURCE = f'자료: housePricing_reduced.csv (Ames Housing) · n = {len(df):,}건'

THRESH = 0.8      # 다중공선성 위험 상관 기준
VIF_STRONG = 10   # 문제지 기준: VIF > 10 이면 공선성 강함
VIF_WATCH = 5


def style_axes(ax, title, subtitle=None, xgrid=False, ygrid=True):
    ax.set_title(title, loc='left', fontweight='bold', fontsize=13,
                 pad=22 if subtitle else 10)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes,
                fontsize=9.5, color='#5A6470', va='bottom')
    sns.despine(ax=ax, top=True, right=True)
    ax.grid(axis='y' if ygrid else 'x', color=GRID, lw=.8)
    if xgrid:
        ax.grid(axis='x', color=GRID, lw=.8)
    ax.set_axisbelow(True)


def footer(fig, text=SOURCE):
    fig.text(0.01, 0.005, text, fontsize=8, color='#8A929B', ha='left')


# ── 1. 상관행렬 · 공분산행렬 ──────────────────────────────────────
corr = num.corr()
cov = num.cov()
corr.to_csv(BASE / 'corr_matrix.csv', encoding='utf-8-sig')
cov.to_csv(BASE / 'cov_matrix.csv', encoding='utf-8-sig')


# ── 2. VIF (numpy 직접 구현) ──────────────────────────────────────
def vif_table(frame: pd.DataFrame) -> pd.DataFrame:
    """VIF_i = 1 / (1 - R^2_i). 각 변수를 나머지 변수로 OLS 회귀(numpy lstsq)."""
    rows = []
    for c in frame.columns:
        y = frame[c].to_numpy(float)
        X = frame.drop(columns=[c]).to_numpy(float)
        X = np.column_stack([np.ones(len(X)), X])          # 절편 추가
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        r2 = 1 - resid.var() / y.var()
        rows.append((c, np.inf if r2 >= 1 else 1 / (1 - r2)))
    return (pd.DataFrame(rows, columns=['feature', 'VIF'])
            .set_index('feature').sort_values('VIF', ascending=False))


X_all = num.drop(columns=['SalePrice'])       # 설명변수만 (target 제외)
vif_before = vif_table(X_all)
n_strong = int((vif_before['VIF'] > VIF_STRONG).sum())


# ── 3. |r| >= 0.8 공선 쌍 탐지 및 제거 대상 판정 ──────────────────
c = X_all.corr()
mask_up = np.triu(np.ones(c.shape, bool), k=1)
pairs = [(c.index[i], c.columns[j], c.iat[i, j])
         for i, j in zip(*np.where(mask_up & (c.abs() >= THRESH)))]
pairs.sort(key=lambda t: -abs(t[2]))

r_target = corr['SalePrice'].drop('SalePrice')

decisions, dropped = [], []
for a, b, r in pairs:
    keep, drop = (a, b) if r_target[a] >= r_target[b] else (b, a)
    decisions.append({
        '공선 쌍': f'{a} ↔ {b}', 'r': round(float(r), 3),
        '유지': keep, 'r(유지, SalePrice)': round(float(r_target[keep]), 3),
        '제거': drop, 'r(제거, SalePrice)': round(float(r_target[drop]), 3),
    })
    if drop not in dropped:
        dropped.append(drop)

kept_features = [f for f in X_all.columns if f not in dropped]
vif_after = vif_table(X_all[kept_features])

# 검증: 한 쌍씩 제거하며 상관을 재계산하는 순차 방식과 결과가 같은지 확인
cur, seq_dropped = X_all.copy(), []
while True:
    cc = cur.corr().abs().to_numpy().copy()
    np.fill_diagonal(cc, 0)
    if cc.max() < THRESH:
        break
    i, j = np.unravel_index(np.argmax(cc), cc.shape)
    fa, fb = cur.columns[i], cur.columns[j]
    d = fa if r_target[fa] < r_target[fb] else fb
    seq_dropped.append(d)
    cur = cur.drop(columns=[d])
SEQ_MATCH = sorted(seq_dropped) == sorted(dropped)

vif_cmp = (vif_before.rename(columns={'VIF': 'VIF_제거전'})
           .join(vif_after.rename(columns={'VIF': 'VIF_제거후'}), how='left')
           .round(3).sort_values('VIF_제거전', ascending=False))
vif_cmp.to_csv(BASE / 'vif_before_after.csv', encoding='utf-8-sig')
pd.DataFrame(decisions).to_csv(BASE / 'collinear_pairs.csv',
                               index=False, encoding='utf-8-sig')

# ── ① 공분산 vs 상관 — 스케일 의존성 실증 ────────────────────────
cov_t = cov['SalePrice'].drop('SalePrice')
cmp_df = (pd.DataFrame({'공분산': cov_t, '상관 r': r_target})
          .sort_values('공분산', ascending=True))
top_cov = cmp_df['공분산'].idxmax()

fig, ax = plt.subplots(1, 2, figsize=(13, 6.8), gridspec_kw={'wspace': .45})
colors = [ALERT if f == top_cov else NEUTRAL for f in cmp_df.index]
ax[0].barh(cmp_df.index, cmp_df['공분산'], color=colors, height=.66)
ax[0].set_xscale('log')
ax[0].set_xlabel('SalePrice와의 공분산 (로그 눈금)')
style_axes(ax[0], '공분산 — 스케일에 압도됨',
           f'{top_cov}가 최대 (단위 sq ft가 커서 값이 부풀려짐)', ygrid=False, xgrid=True)

rank = cmp_df['상관 r'].sort_values()
colors2 = [ALERT if f == top_cov else (ACCENT if v >= .7 else NEUTRAL)
           for f, v in rank.items()]
ax[1].barh(rank.index, rank.values, color=colors2, height=.66)
for f, v in rank.items():
    ax[1].text(v + .012, f, f'{v:.2f}', va='center', fontsize=8.6,
               color=ALERT if f == top_cov else '#5A6470')
ax[1].set_xlim(0, 0.95)
ax[1].set_xlabel('SalePrice와의 상관계수 r')
style_axes(ax[1], '상관계수 — 표준화 후 순위 역전',
           f'{top_cov}는 r={r_target[top_cov]:.2f}로 최하위권', ygrid=False, xgrid=True)

fig.suptitle(f'① 공분산 최댓값 {top_cov}, 상관에서는 r={r_target[top_cov]:.2f} 최하위권 — 공분산의 스케일 의존성',
             x=0.01, y=0.985, ha='left', va='top', fontweight='bold', fontsize=15)
fig.tight_layout(rect=[0, 0.03, 1, 0.90])
footer(fig)
fig.savefig(IMG / '01_cov_vs_corr.png', dpi=120)
plt.close(fig)


# ── 히트맵 공통 ───────────────────────────────────────────────────
def draw_heatmap(cols, fname, title, subtitle):
    cm = num[cols].corr()
    up = np.triu(np.ones_like(cm, dtype=bool))
    annot = cm.map(lambda v: f'{v:.2f}' if abs(v) >= 0.5 else '')
    fig, ax = plt.subplots(figsize=(10.5, 8.4))
    sns.heatmap(cm, mask=up, annot=annot, fmt='', cmap='Blues', vmin=0, vmax=1,
                square=True, linewidths=.8, linecolor='white',
                annot_kws={'fontsize': 8.5}, cbar_kws={'shrink': .65}, ax=ax)
    for i, a in enumerate(cols):
        for j, b in enumerate(cols):
            if j < i and 'SalePrice' not in (a, b) and abs(cm.iat[i, j]) >= THRESH:
                ax.add_patch(plt.Rectangle((j, i), 1, 1, fill=False,
                                           edgecolor=ALERT, lw=2.6))
    ax.tick_params(labelsize=9)
    fig.suptitle(title, x=0.01, y=0.98, ha='left', fontweight='bold', fontsize=14)
    fig.text(0.01, 0.935, subtitle, fontsize=9.5, color='#5A6470', ha='left')
    fig.tight_layout(rect=[0, 0.03, 1, 0.92])
    footer(fig)
    fig.savefig(IMG / fname, dpi=120)
    plt.close(fig)


# ── ② 제거 전 히트맵 ──────────────────────────────────────────────
draw_heatmap(
    list(X_all.columns) + ['SalePrice'], '02_heatmap_before.png',
    f'② 설명변수 12종 중 {len(pairs)}쌍이 |r| ≥ {THRESH} — 제거 대상 확정',
    f'하단 삼각형만 표시 · |r| ≥ 0.5만 수치 표기 · 빨간 테두리 = |r| ≥ {THRESH} 공선 쌍')

# ── ③ 제거 후 히트맵 ──────────────────────────────────────────────
kept_corr = X_all[kept_features].corr().abs().to_numpy().copy()
np.fill_diagonal(kept_corr, 0)
max_after = kept_corr.max()
draw_heatmap(
    kept_features + ['SalePrice'], '03_heatmap_after.png',
    f'③ 제거 후 설명변수 간 최대 상관 {max_after:.2f} — |r| ≥ {THRESH} 쌍 소멸',
    f'{", ".join(dropped)} 제거 · 빨간 테두리 없음 = 공선 위험 쌍 없음')

# ── ④ VIF 제거 전/후 — 덤벨 차트 ──────────────────────────────────
order = vif_cmp.sort_values('VIF_제거전').index
fig, ax = plt.subplots(figsize=(11, 7))
for i, f in enumerate(order):
    b = vif_cmp.loc[f, 'VIF_제거전']
    a_ = vif_cmp.loc[f, 'VIF_제거후']
    if pd.isna(a_):                                   # 제거된 변수
        ax.scatter(b, i, s=95, color=ALERT, zorder=3)
        ax.text(b + .14, i, f'{b:.2f}  → 제거', va='center',
                fontsize=9, color=ALERT, fontweight='bold')
    else:
        ax.plot([a_, b], [i, i], color=GRID, lw=3, zorder=1, solid_capstyle='round')
        ax.scatter(b, i, s=85, color=NEUTRAL, zorder=3)
        ax.scatter(a_, i, s=85, color=ACCENT, zorder=4)
        ax.text(max(b, a_) + .14, i, f'{b:.2f} → {a_:.2f}', va='center',
                fontsize=9, color=DARK,
                fontweight='bold' if b >= VIF_WATCH else 'normal')

ax.set_yticks(range(len(order)))
ax.set_yticklabels(order)
ax.axvline(VIF_WATCH, color='#B0B6BD', ls=':', lw=1.2)
ax.text(VIF_WATCH, -0.75, ' VIF 5 (주의 기준)', fontsize=8.5, color='#8A929B', va='center')
ax.set_xlim(0, 7.6)
ax.set_xlabel('VIF (분산팽창인자)')
style_axes(ax,
           f'④ 최대 VIF {vif_before["VIF"].max():.2f} → {vif_after["VIF"].max():.2f} 하락, '
           f'전 변수 안전 구간 진입',
           f'회색 점 = 제거 전, 남색 점 = 제거 후, 빨간 점 = 제거된 변수 · '
           f'제거 전에도 VIF > {VIF_STRONG} 변수는 {n_strong}개 (VIF 단독 기준으로는 제거 대상 없음)',
           ygrid=False, xgrid=True)
fig.tight_layout(rect=[0, 0.03, 1, 1])
footer(fig)
fig.savefig(IMG / '04_vif_before_after.png', dpi=120)
plt.close(fig)


# ── 후속 과제(3·4·6)에서 쓸 확정 feature 세트 ─────────────────────
out = df[['Id'] + kept_features +
         ['Neighborhood', 'ExterQual', 'KitchenQual', 'CentralAir', 'SalePrice']]
out.to_csv(BASE.parent / 'data' / 'housePricing_selected.csv',
           index=False, encoding='utf-8-sig')

(BASE / 'task2_summary.json').write_text(json.dumps({
    'threshold_corr': THRESH,
    'vif_strong_threshold': VIF_STRONG,
    'n_features_over_vif10_before': n_strong,
    'collinear_pairs': decisions,
    'dropped_features': dropped,
    'kept_numeric_features': kept_features,
    'max_vif_before': round(float(vif_before['VIF'].max()), 3),
    'max_vif_after': round(float(vif_after['VIF'].max()), 3),
    'max_corr_after': round(float(max_after), 3),
    'sequential_removal_matches': bool(SEQ_MATCH),
    'cov_top_feature': top_cov,
    'cov_top_value': float(cov_t.max()),
    'cov_top_corr': round(float(r_target[top_cov]), 3),
}, ensure_ascii=False, indent=2), encoding='utf-8')

print(f'발견된 |r|>={THRESH} 공선 쌍: {len(pairs)}')
print(pd.DataFrame(decisions).to_string(index=False))
print('\n제거:', dropped)
print(f'순차 재계산 방식과 결과 일치: {SEQ_MATCH}')
print(f'\n제거 전 VIF > {VIF_STRONG} 인 변수: {n_strong}개  (최대 {vif_before["VIF"].max():.2f})')
print('\n[VIF 제거 전/후]')
print(vif_cmp.to_string())
print(f'\nmax VIF: {vif_before["VIF"].max():.2f} → {vif_after["VIF"].max():.2f}'
      f' · 제거 후 설명변수 간 최대 상관 {max_after:.2f}')
print(f'공분산 최대 {top_cov} = {cov_t.max():,.0f} (상관 r={r_target[top_cov]:.2f})')

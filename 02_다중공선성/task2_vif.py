# -*- coding: utf-8 -*-
"""과제 2. 공분산 · 다중공선성 진단과 제거 [20점]
- 상관행렬 / 공분산행렬
- |r| >= 0.8 공선 쌍 탐지
- VIF 계산 (numpy 직접 구현: VIF_i = 1 / (1 - R^2_i))
- 공선 쌍 중 SalePrice 상관이 낮은 쪽 제거 → 제거 전/후 VIF 비교
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

BASE = Path(__file__).resolve().parent
IMG = BASE / 'images'
IMG.mkdir(exist_ok=True)
CSV = BASE.parent / 'data' / 'housePricing_reduced.csv'

df = pd.read_csv(CSV, encoding='utf-8-sig')
num = df.select_dtypes('number').drop(columns=['Id'])

corr = num.corr()
cov = num.cov()
corr.to_csv(BASE / 'corr_matrix.csv', encoding='utf-8-sig')
cov.to_csv(BASE / 'cov_matrix.csv', encoding='utf-8-sig')


def vif_table(frame: pd.DataFrame) -> pd.DataFrame:
    """VIF_i = 1 / (1 - R^2_i). 각 변수를 나머지 변수로 OLS 회귀(numpy lstsq)."""
    cols = list(frame.columns)
    rows = []
    for c in cols:
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

# ── |r| >= 0.8 공선 쌍 탐지 ───────────────────────────────────────
THRESH = 0.8
c = X_all.corr()
mask = np.triu(np.ones(c.shape, bool), k=1)
pairs = [(c.index[i], c.columns[j], c.iat[i, j])
         for i, j in zip(*np.where(mask & (c.abs() >= THRESH)))]
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

vif_cmp = (vif_before.rename(columns={'VIF': 'VIF_제거전'})
           .join(vif_after.rename(columns={'VIF': 'VIF_제거후'}), how='left')
           .round(3).sort_values('VIF_제거전', ascending=False))
vif_cmp.to_csv(BASE / 'vif_before_after.csv', encoding='utf-8-sig')
pd.DataFrame(decisions).to_csv(BASE / 'collinear_pairs.csv',
                               index=False, encoding='utf-8-sig')

# ── 히트맵 (제거 전 / 제거 후) ────────────────────────────────────
for name, cols, title in [
    ('06_heatmap_before', list(X_all.columns) + ['SalePrice'], '제거 전'),
    ('07_heatmap_after', kept_features + ['SalePrice'], '제거 후'),
]:
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(num[cols].corr(), annot=True, fmt='.2f', cmap='coolwarm',
                center=0, square=True, linewidths=.4, ax=ax)
    ax.set_title(f'상관 히트맵 ({title}) — |r|≥0.8 쌍 점검')
    fig.tight_layout()
    fig.savefig(IMG / f'{name}.png', dpi=120)
    plt.close(fig)

# ── VIF 비교 막대 ─────────────────────────────────────────────────
plot_df = vif_cmp.reset_index().melt('feature', value_name='VIF', var_name='구분').dropna()
fig, ax = plt.subplots(figsize=(12, 6))
sns.barplot(data=plot_df, x='feature', y='VIF', hue='구분',
            palette=['#C0504D', '#2E5EAA'], ax=ax)
ax.axhline(10, ls='--', color='red', label='VIF = 10 (강한 공선성)')
ax.axhline(5, ls=':', color='orange', label='VIF = 5 (주의)')
ax.set_title('제거 전/후 VIF 비교')
ax.tick_params(axis='x', rotation=45)
ax.legend()
fig.tight_layout()
fig.savefig(IMG / '08_vif_before_after.png', dpi=120)
plt.close(fig)

# ── 후속 과제(3·4·6)에서 쓸 확정 feature 세트 저장 ────────────────
out = df[['Id'] + kept_features +
         ['Neighborhood', 'ExterQual', 'KitchenQual', 'CentralAir', 'SalePrice']]
out.to_csv(BASE.parent / 'data' / 'housePricing_selected.csv',
           index=False, encoding='utf-8-sig')

(BASE / 'task2_summary.json').write_text(json.dumps({
    'threshold': THRESH,
    'collinear_pairs': decisions,
    'dropped_features': dropped,
    'kept_numeric_features': kept_features,
    'max_vif_before': round(float(vif_before['VIF'].max()), 3),
    'max_vif_after': round(float(vif_after['VIF'].max()), 3),
}, ensure_ascii=False, indent=2), encoding='utf-8')

print('발견된 |r|>=0.8 공선 쌍:', len(pairs))
print(pd.DataFrame(decisions).to_string(index=False))
print('\n제거:', dropped)
print('\n[VIF 제거 전/후]')
print(vif_cmp.to_string())
print(f"\nmax VIF: {vif_before['VIF'].max():.2f} → {vif_after['VIF'].max():.2f}")

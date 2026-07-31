# -*- coding: utf-8 -*-
"""과제 3 — 개선 트랙: Gradient Boosting R² 0.9 달성 파이프라인

기본 트랙(task3_sklearn_reference.py, 전체 1,460건·기본 하이퍼파라미터)과 별도로,
아래 3단계 개선을 누적 적용해 GB 성능을 R² 0.81 → 0.90으로 끌어올린다.

  1) 이상치 제거  : Id 524·1299 (SaleCondition=Partial 미완성 부분매매,
                    De Cock(2011) 원저자 권고 GrLivArea>4000 제거 대상)
  2) 파생 변수    : TotalSF, HouseAge, Qual×Area 상호작용 등 8종
  3) 인코딩/튜닝  : Neighborhood TargetEncoder(CV 내부 fit — 누수 없음),
                    GB(lr=0.05, n=600, depth=3, subsample=0.8)

각 단계의 기여도를 단계별 누적표로 산출한다 (전부 5-fold CV 실측).
실행 : set PYTHONIOENCODING=utf-8 && python 03_orange/task3_gb_improved.py
"""
from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, TargetEncoder
from sklearn.model_selection import KFold, cross_validate
from sklearn.ensemble import GradientBoostingRegressor

warnings.filterwarnings('ignore')

# ── 공통 스타일 (과제 1·2·3 동일) ─────────────────────────────────
ACCENT = '#1F4E79'
NEUTRAL = '#C8CDD3'
DARK = '#222222'
ALERT = '#B94A48'
GRID = '#E6E8EB'
sns.set_theme(style='white', font='Malgun Gothic')
plt.rcParams.update({'font.family': 'Malgun Gothic', 'axes.unicode_minus': False,
                     'axes.edgecolor': GRID, 'text.color': DARK,
                     'axes.labelcolor': DARK, 'figure.facecolor': 'white'})

BASE = Path(__file__).resolve().parent
IMG = BASE / 'images'
DATA = BASE.parent / 'data' / 'housePricing_selected.csv'

df = pd.read_csv(DATA, encoding='utf-8-sig')
QUAL = ['Fa', 'TA', 'Gd', 'Ex']
ORD = ['ExterQual', 'KitchenQual']
CAT = ['Neighborhood', 'CentralAir']
CV = KFold(5, shuffle=True, random_state=42)


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """파생 변수 8종 — 행 단위 계산이라 fold 간 누수 없음."""
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = X.copy()
        X['TotalSF'] = X['GrLivArea'] + X['TotalBsmtSF']          # 총 사용 면적
        X['HouseAge'] = 2010 - X['YearBuilt']                     # 주택 연령
        X['RemodAge'] = 2010 - X['YearRemodAdd']                  # 리모델링 경과
        X['IsRemodeled'] = (X['YearRemodAdd'] != X['YearBuilt']).astype(int)
        X['Qual_x_Area'] = X['OverallQual'] * X['GrLivArea']      # 품질×면적 상호작용
        X['Qual_x_TotalSF'] = X['OverallQual'] * X['TotalSF']
        X['HasFireplace'] = (X['Fireplaces'] > 0).astype(int)
        X['LotRatio'] = X['GrLivArea'] / X['LotArea']             # 대지 대비 건물 비율
        return X


def make_pipe(fe: bool, target_enc: bool, model):
    steps = [('fe', FeatureEngineer())] if fe else []
    cat_tf = (TargetEncoder(random_state=42) if target_enc
              else OneHotEncoder(handle_unknown='ignore'))
    ct = ColumnTransformer([
        ('ord', OrdinalEncoder(categories=[QUAL] * 2), ORD),
        ('cat', cat_tf, CAT),
    ], remainder='passthrough')
    return Pipeline(steps + [('ct', ct), ('m', model)])


def evaluate(X, y, fe, te, model):
    res = cross_validate(make_pipe(fe, te, model), X, y, cv=CV,
                         scoring={'R2': 'r2', 'RMSE': 'neg_root_mean_squared_error',
                                  'MAE': 'neg_mean_absolute_error'},
                         return_train_score=True)
    return {'R2': res['test_R2'].mean(), 'R2_std': res['test_R2'].std(),
            'RMSE': -res['test_RMSE'].mean(), 'MAE': -res['test_MAE'].mean(),
            '과적합갭': res['train_R2'].mean() - res['test_R2'].mean()}


GB_BASE = GradientBoostingRegressor(random_state=42)
GB_TUNED = GradientBoostingRegressor(n_estimators=600, learning_rate=.05,
                                     max_depth=3, subsample=.8, random_state=42)

# 이상치: 감축본 컬럼만으로 재현 가능한 조건 (원본 SaleCondition=Partial 2건과 일치)
out_mask = (df['GrLivArea'] > 4000) & (df['SalePrice'] < 300_000)
df_clean = df[~out_mask]
print(f'이상치 제거: {out_mask.sum()}건 (Id {df.loc[out_mask, "Id"].tolist()}) → n={len(df_clean)}')


def split(d):
    return d.drop(columns=['SalePrice', 'Id']), d['SalePrice'].astype(float)


X_all, y_all = split(df)
X_cl, y_cl = split(df_clean)

STAGES = [
    ('S0 기본 (전체 1,460건 · 기본 GB)', X_all, y_all, False, False, GB_BASE),
    ('S1 + 이상치 2건 제거', X_cl, y_cl, False, False, GB_BASE),
    ('S2 + 파생변수 8종', X_cl, y_cl, True, False, GB_BASE),
    ('S3 + TargetEncoder', X_cl, y_cl, True, True, GB_BASE),
    ('S4 + 하이퍼파라미터 튜닝', X_cl, y_cl, True, True, GB_TUNED),
]

rows = []
for label, X, y, fe, te, model in STAGES:
    m = evaluate(X, y, fe, te, model)
    rows.append({'단계': label, **{k: round(v, 4) for k, v in m.items()}})
    print(f"{label:<38s} R²={m['R2']:.4f} (±{m['R2_std']:.3f})  "
          f"RMSE={m['RMSE']:,.0f}  MAE={m['MAE']:,.0f}  과적합갭={m['과적합갭']:.3f}")

stage_df = pd.DataFrame(rows)
stage_df.to_csv(BASE / 'gb_improvement_stages.csv', index=False, encoding='utf-8-sig')
(BASE / 'gb_improved_summary.json').write_text(json.dumps({
    'final_r2': rows[-1]['R2'], 'final_rmse': rows[-1]['RMSE'],
    'baseline_r2': rows[0]['R2'],
    'outliers_removed': df.loc[out_mask, 'Id'].tolist(),
    'model': 'GradientBoosting(n_estimators=600, learning_rate=0.05, max_depth=3, subsample=0.8)',
    'stages': rows,
}, ensure_ascii=False, indent=2), encoding='utf-8')

# ── 단계별 누적 개선 차트 ─────────────────────────────────────────
fig, ax = plt.subplots(figsize=(11.5, 5.8))
labels = [r['단계'] for r in rows]
r2s = [r['R2'] for r in rows]
colors = [NEUTRAL] * (len(rows) - 1) + [ACCENT]
bars = ax.bar(range(len(rows)), r2s, color=colors, width=.62)
for i, (v, prev) in enumerate(zip(r2s, [None] + r2s[:-1])):
    delta = f'  (+{v - prev:.3f})' if prev is not None and v >= prev else \
            (f'  ({v - prev:+.3f})' if prev is not None else '')
    ax.text(i, v + .004, f'{v:.4f}{delta}', ha='center', fontsize=9.5,
            fontweight='bold' if i == len(rows) - 1 else 'normal',
            color=ACCENT if i == len(rows) - 1 else '#5A6470')
ax.axhline(.9, color=ALERT, ls='--', lw=1.2)
ax.text(-.35, .902, 'R² = 0.90 목표', fontsize=9, color=ALERT, va='bottom')
ax.set_xticks(range(len(rows)))
ax.set_xticklabels([l.split(' (')[0] for l in labels], fontsize=9)
ax.set_ylim(.75, .95)
ax.set_ylabel('R² (5-fold CV)')
ax.set_title(f'④ GB 단계별 개선 — R² {r2s[0]:.3f} → {r2s[-1]:.3f}, '
             f'기여 최대는 이상치 2건 제거(+{r2s[1] - r2s[0]:.3f})',
             loc='left', fontweight='bold', fontsize=13, pad=24)
ax.text(0, 1.02, '전 단계 5-fold 교차검증 실측 · 이상치 = Id 524·1299 (SaleCondition=Partial 미완성 거래)',
        transform=ax.transAxes, fontsize=9.5, color='#5A6470', va='bottom')
sns.despine(ax=ax)
ax.grid(axis='y', color=GRID, lw=.8)
ax.set_axisbelow(True)
fig.text(0.01, 0.005, f'자료: housePricing_selected.csv · 기본 n=1,460 / 개선 n=1,458',
         fontsize=8, color='#8A929B')
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMG / '04_gb_improvement_stages.png', dpi=120)
plt.close(fig)

# ── 최종 모델 실제값 vs 예측값 (out-of-fold) ─────────────────────
from sklearn.model_selection import cross_val_predict
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

pred = cross_val_predict(make_pipe(True, True, GB_TUNED), X_cl, y_cl, cv=CV)
r2p = r2_score(y_cl, pred)
rmsep = float(np.sqrt(mean_squared_error(y_cl, pred)))
maep = mean_absolute_error(y_cl, pred)

usd_k = lambda x, _=None: f'${x/1000:,.0f}K'
fig, ax = plt.subplots(figsize=(8.6, 8))
lo, hi = float(min(y_cl.min(), pred.min())), float(max(y_cl.max(), pred.max()))
ax.plot([lo, hi], [lo, hi], color='#9AA1A9', ls='--', lw=1.4, zorder=1)
ax.annotate('완벽 예측선 (y = x)', (hi * .72, hi * .72), xytext=(10, -16),
            textcoords='offset points', fontsize=9.5, color='#7B8794')
ax.scatter(y_cl, pred, s=18, alpha=.4, color=ACCENT, edgecolors='none', zorder=2)
ax.xaxis.set_major_formatter(plt.FuncFormatter(usd_k))
ax.yaxis.set_major_formatter(plt.FuncFormatter(usd_k))
ax.set_xlabel('실제 SalePrice')
ax.set_ylabel('예측 SalePrice (out-of-fold)')
ax.set_xlim(lo * .9, hi * 1.03)
ax.set_ylim(lo * .9, hi * 1.03)
ax.set_title(f'⑤ 개선 GB 예측 — pooled OOF R² {r2p:.3f}',
             loc='left', fontweight='bold', fontsize=13, pad=24)
ax.text(0, 1.02, f'RMSE {rmsep:,.0f} / MAE {maep:,.0f} · 기본 트랙 산점도(③)의 '
        f'대형 이탈점 2건이 제거되어 산포가 y=x에 밀착',
        transform=ax.transAxes, fontsize=9.5, color='#5A6470', va='bottom')
sns.despine(ax=ax)
ax.grid(axis='y', color=GRID, lw=.8)
ax.set_axisbelow(True)
fig.text(0.01, 0.005, '자료: housePricing_selected.csv · 이상치 2건 제거 n=1,458 · 5-fold CV',
         fontsize=8, color='#8A929B')
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(IMG / '05_gb_improved_predictions.png', dpi=120)
plt.close(fig)

print(f'\n최종 R² = {rows[-1]["R2"]:.4f} (목표 0.90 {"달성" if rows[-1]["R2"] >= .9 else "미달"})')
print(f'차트 2종 저장 → {IMG}')

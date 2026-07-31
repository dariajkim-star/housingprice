# -*- coding: utf-8 -*-
"""과제 3 — Orange 회귀모델 개발의 Python(sklearn) 재현 스크립트 [20점]

Orange Test & Score 위젯(5-fold 교차검증)과 동일한 실험을 sklearn으로 재현해
실제 성능 수치(R² / RMSE / MAE)를 산출하고, 아래 3가지 추가 검증을 수행한다.

  A. 로그 타깃 실험   — 과제 1에서 확인한 왜도 1.88을 log1p로 보정하면 성능이 개선되는가
  B. Ridge alpha 탐색 — alpha 고정(1.0)이 아니라 탐색해도 Linear과 차이가 없는가 (과제 2 검증)
  C. 이상치 실험      — 과제 1에서 찾은 Id 524·1299를 제거하면 성능이 달라지는가

입력 : data/housePricing_selected.csv  (과제 2 다중공선성 제거 확정본)
출력 : model_scores.csv, log_target_comparison.csv, ablation.csv,
       images/ 3종, 콘솔 성능표

실행 : set PYTHONIOENCODING=utf-8 && python 03_orange/task3_sklearn_reference.py

시각화 규칙은 과제 1·2와 동일 (회색=일반 / 남색=핵심 / 빨강=이상치·제외 대상).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler
from sklearn.model_selection import KFold, cross_validate, cross_val_predict
from sklearn.linear_model import LinearRegression, Ridge, RidgeCV
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

# ── 공통 스타일 (과제 1·2와 동일) ─────────────────────────────────
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

RANDOM_STATE = 42
N_SPLITS = 5
OUTLIER_IDS = [524, 1299]          # 과제 1 ③에서 확인한 추세 이탈 대형 주택

BASE = Path(__file__).resolve().parent
IMG = BASE / 'images'
IMG.mkdir(exist_ok=True)
DATA = BASE.parent / 'data' / 'housePricing_selected.csv'

df = pd.read_csv(DATA, encoding='utf-8-sig')
SOURCE = (f'자료: housePricing_selected.csv (과제 2 확정본) · n = {len(df):,}건 · '
          f'{N_SPLITS}-fold 교차검증 (shuffle, seed={RANDOM_STATE})')

TARGET = 'SalePrice'
y_full = df[TARGET].astype(float)
X_full = df.drop(columns=[TARGET, 'Id'])       # Id는 meta(식별자)이므로 학습 제외

QUAL_ORDER = ['Fa', 'TA', 'Gd', 'Ex']          # 낮음 → 높음 (오름차순 코드 부여)
ORD_COLS = ['ExterQual', 'KitchenQual']
CAT_COLS = ['Neighborhood', 'CentralAir']
NUM_COLS = [c for c in X_full.columns if c not in ORD_COLS + CAT_COLS]


def make_preprocessor(scale: bool, drop_first: bool):
    """scale     : 거리·규제 기반 모델(Linear/Ridge/kNN)에만 표준화 적용
    drop_first : 선형 계열은 더미 변수 트랩을 피하려고 첫 범주를 제거
    """
    num_pipe = Pipeline([('scaler', StandardScaler())]) if scale else 'passthrough'
    ord_steps = [('ord', OrdinalEncoder(categories=[QUAL_ORDER] * len(ORD_COLS)))]
    if scale:
        ord_steps.append(('scaler', StandardScaler()))
    return ColumnTransformer([
        ('num', num_pipe, NUM_COLS),
        ('ord', Pipeline(ord_steps), ORD_COLS),
        ('cat', OneHotEncoder(handle_unknown='ignore',
                              drop='first' if drop_first else None), CAT_COLS),
    ])


# (모델, 스케일링 필요, 선형 계열 여부)
MODELS = {
    'Linear Regression': (LinearRegression(), True, True),
    'Ridge': (RidgeCV(alphas=np.logspace(-2, 3, 20)), True, True),
    'Random Forest': (RandomForestRegressor(n_estimators=100, random_state=RANDOM_STATE,
                                            n_jobs=-1), False, False),
    'Gradient Boosting': (GradientBoostingRegressor(n_estimators=100,
                                                    random_state=RANDOM_STATE), False, False),
    'kNN': (KNeighborsRegressor(n_neighbors=5), True, False),
}

CV = KFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
SCORING = {'R2': 'r2', 'RMSE': 'neg_root_mean_squared_error',
           'MAE': 'neg_mean_absolute_error'}


def build(name):
    est, scale, linear = MODELS[name]
    return Pipeline([('prep', make_preprocessor(scale, linear)), ('model', est)])


def footer(fig, text=SOURCE):
    fig.text(0.01, 0.005, text, fontsize=8, color='#8A929B', ha='left')


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


def usd_k(x, _=None):
    return f'${x/1000:,.0f}K'


print('=' * 78)
print(f'과제 3 : Orange 회귀모델 개발 - sklearn 재현 ({N_SPLITS}-fold 교차검증)')
print('=' * 78)
print(f'데이터 : {DATA}')
print(f'shape  : {df.shape[0]}행 x {df.shape[1]}열 / 결측치 {int(df.isna().sum().sum())}건')
print(f'  수치형({len(NUM_COLS)}) : {", ".join(NUM_COLS)}')
print(f'  순서형({len(ORD_COLS)}) : {", ".join(ORD_COLS)}  (Fa<TA<Gd<Ex)')
print(f'  명목형({len(CAT_COLS)}) : {", ".join(CAT_COLS)}  -> One-Hot')

# ── 1. 기본 성능표 ────────────────────────────────────────────────
rows = []
for name in MODELS:
    res = cross_validate(build(name), X_full, y_full, cv=CV, scoring=SCORING)
    rows.append({'Model': name,
                 'R2': res['test_R2'].mean(), 'RMSE': -res['test_RMSE'].mean(),
                 'MAE': -res['test_MAE'].mean(), 'R2_std': res['test_R2'].std(),
                 'FitTime_s': res['fit_time'].mean()})
    print(f'  - {name:<20s} 완료')

scores = pd.DataFrame(rows).sort_values('R2', ascending=False).reset_index(drop=True)
scores.round(6).to_csv(BASE / 'model_scores.csv', index=False, encoding='utf-8-sig')

print('\n' + '=' * 78)
print(f'Test & Score 결과 ({N_SPLITS}-fold, R² 내림차순)')
print('=' * 78)
print(f"{'Model':<20s}{'R2':>10s}{'RMSE':>14s}{'MAE':>14s}{'R2 std':>10s}")
print('-' * 78)
for _, r in scores.iterrows():
    print(f"{r['Model']:<20s}{r['R2']:>10.4f}{r['RMSE']:>14,.1f}"
          f"{r['MAE']:>14,.1f}{r['R2_std']:>10.4f}")

best = scores.loc[0, 'Model']
runner = scores.loc[1, 'Model']

# ── ① 모델 성능 비교 (R² ± 표준편차) ──────────────────────────────
s = scores.sort_values('R2')
fig, ax = plt.subplots(1, 2, figsize=(15, 6.2), gridspec_kw={'wspace': .52})

colors = [ACCENT if m == best else NEUTRAL for m in s['Model']]
ax[0].barh(s['Model'], s['R2'], color=colors, height=.6)
ax[0].errorbar(s['R2'], s['Model'], xerr=s['R2_std'], fmt='none',
               ecolor='#7B8794', elinewidth=1.4, capsize=5)
for m, v, sd in zip(s['Model'], s['R2'], s['R2_std']):
    ax[0].text(v + sd + .012, m, f'{v:.4f}  ±{sd:.3f}', va='center', fontsize=9,
               fontweight='bold' if m == best else 'normal',
               color=ACCENT if m == best else '#5A6470')
ax[0].set_xlim(0, 1.35)
ax[0].set_xlabel('R² (fold 평균, 오차막대 = 표준편차)')
style_axes(ax[0], 'R² — 평균은 근소, 안정성은 차이 큼',
           f'{best} 최고 · 오차막대가 겹칠 만큼 상위권 격차는 작다',
           ygrid=False, xgrid=True)

s2 = scores.sort_values('RMSE', ascending=False)
c2 = [ACCENT if m == best else NEUTRAL for m in s2['Model']]
ax[1].barh(s2['Model'], s2['RMSE'], color=c2, height=.6)
for m, v, mae in zip(s2['Model'], s2['RMSE'], s2['MAE']):
    ax[1].text(v + 700, m, f'{v:,.0f}  (MAE {mae:,.0f})', va='center', fontsize=9,
               fontweight='bold' if m == best else 'normal',
               color=ACCENT if m == best else '#5A6470')
ax[1].set_xlim(0, scores['RMSE'].max() * 1.42)
ax[1].xaxis.set_major_formatter(plt.FuncFormatter(usd_k))
ax[1].set_xlabel('RMSE (낮을수록 좋음)')
style_axes(ax[1], 'RMSE·MAE — 트리 계열이 선형 대비 우위',
           '괄호는 MAE', ygrid=False, xgrid=True)

fig.suptitle(f'① 알고리즘 5종 비교 — {best} R²={scores.loc[0, "R2"]:.4f}로 최고, '
             f'{runner}와 격차 {scores.loc[0, "R2"] - scores.loc[1, "R2"]:.4f}',
             x=0.01, y=0.99, ha='left', va='top', fontweight='bold', fontsize=15)
fig.tight_layout(rect=[0, 0.04, 1, 0.84])
footer(fig)
fig.savefig(IMG / '01_model_comparison.png', dpi=120)
plt.close(fig)


# ── 2. 로그 타깃 실험 ─────────────────────────────────────────────
def oof_metrics(name, log: bool, X=X_full, y=y_full):
    """out-of-fold 예측을 원본(달러) 스케일로 되돌려 평가 — 로그/원본 비교가 가능해진다."""
    yy = np.log1p(y) if log else y
    pred = cross_val_predict(build(name), X, yy, cv=CV)
    if log:
        pred = np.expm1(pred)
    return (r2_score(y, pred), float(np.sqrt(mean_squared_error(y, pred))),
            mean_absolute_error(y, pred), pred)


log_rows = []
for name in MODELS:
    for log in (False, True):
        r2, rmse, mae, _ = oof_metrics(name, log)
        log_rows.append({'Model': name, '타깃': 'log1p' if log else '원본',
                         'R2': r2, 'RMSE': rmse, 'MAE': mae})
log_cmp = pd.DataFrame(log_rows)
log_cmp.round(4).to_csv(BASE / 'log_target_comparison.csv',
                        index=False, encoding='utf-8-sig')

piv = log_cmp.pivot(index='Model', columns='타깃')
r2_gain = piv[('R2', 'log1p')] - piv[('R2', '원본')]
mae_gain = piv[('MAE', '원본')] - piv[('MAE', 'log1p')]     # 양수면 로그가 유리

fig, ax = plt.subplots(1, 2, figsize=(15, 5.8), gridspec_kw={'wspace': .5})
o = r2_gain.sort_values()
ax[0].barh(o.index, o.values, color=[ACCENT if v > 0 else ALERT for v in o], height=.6)
ax[0].axvline(0, color='#777777', lw=1)
for m, v in o.items():
    ax[0].text(v + (.01 if v > 0 else -.01), m, f'{v:+.3f}', va='center',
               ha='left' if v > 0 else 'right', fontsize=9,
               color=ACCENT if v > 0 else ALERT, fontweight='bold')
ax[0].set_xlim(o.min() * 1.45, max(o.max() * 2.6, .06))
ax[0].set_xlabel('R² 변화량 (로그 타깃 - 원본 타깃)')
style_axes(ax[0], 'R² 기준 — 선형 계열은 대폭 악화',
           '역변환 시 고가 주택의 절대오차가 증폭되기 때문', ygrid=False, xgrid=True)

o2 = mae_gain.sort_values()
ax[1].barh(o2.index, o2.values, color=[ACCENT if v > 0 else ALERT for v in o2], height=.6)
ax[1].axvline(0, color='#777777', lw=1)
for m, v in o2.items():
    ax[1].text(v + (60 if v > 0 else -60), m, f'{v:+,.0f}', va='center',
               ha='left' if v > 0 else 'right', fontsize=9,
               color=ACCENT if v > 0 else ALERT, fontweight='bold')
ax[1].set_xlim(min(o2.min() * 1.6, -700), max(o2.max() * 1.6, 700))
ax[1].set_xlabel('MAE 개선량 ($, 양수 = 로그 타깃이 유리)')
style_axes(ax[1], 'MAE 기준 — 결론이 뒤집힘',
           '상대오차를 줄이므로 중간 가격대 예측은 개선', ygrid=False, xgrid=True)

fig.suptitle('② 로그 타깃의 효과는 지표에 따라 정반대 — R²는 악화, MAE는 개선',
             x=0.01, y=0.99, ha='left', va='top', fontweight='bold', fontsize=15)
fig.tight_layout(rect=[0, 0.04, 1, 0.84])
footer(fig)
fig.savefig(IMG / '02_log_target_effect.png', dpi=120)
plt.close(fig)

# ── 3. 이상치 제거 실험 ───────────────────────────────────────────
keep = ~df['Id'].isin(OUTLIER_IDS)
abl = []
for name in MODELS:
    base_r2 = scores.loc[scores['Model'] == name, 'R2'].iat[0]
    res = cross_validate(build(name), X_full[keep.values], y_full[keep.values],
                         cv=CV, scoring=SCORING)
    abl.append({'Model': name, 'R2_전체': base_r2,
                'R2_이상치제거': res['test_R2'].mean(),
                'RMSE_이상치제거': -res['test_RMSE'].mean()})
abl_df = pd.DataFrame(abl)
abl_df['R2_변화'] = abl_df['R2_이상치제거'] - abl_df['R2_전체']
abl_df.round(4).to_csv(BASE / 'ablation.csv', index=False, encoding='utf-8-sig')

# ── ③ 최고 성능 모델 실제값 vs 예측값 ─────────────────────────────
r2_b, rmse_b, mae_b, pred_b = oof_metrics(best, False)
err = np.abs(pred_b - y_full)
out_mask = df['Id'].isin(OUTLIER_IDS).to_numpy()

fig, ax = plt.subplots(figsize=(8.6, 8))
lo, hi = float(min(y_full.min(), pred_b.min())), float(max(y_full.max(), pred_b.max()))
ax.plot([lo, hi], [lo, hi], color='#9AA1A9', ls='--', lw=1.4, zorder=1)
ax.annotate('완벽 예측선 (y = x)', (hi * .74, hi * .74), xytext=(10, -16),
            textcoords='offset points', fontsize=9.5, color='#7B8794')
ax.scatter(y_full[~out_mask], pred_b[~out_mask], s=18, alpha=.4,
           color=ACCENT, edgecolors='none', zorder=2)
ax.scatter(y_full[out_mask], pred_b[out_mask], s=120, facecolor='none',
           edgecolor=ALERT, lw=2, zorder=4)
for i in np.where(out_mask)[0]:
    ax.annotate(f"Id {int(df['Id'].iat[i])} · 오차 {usd_k(err.iat[i])}",
                (y_full.iat[i], pred_b[i]), xytext=(14, 8),
                textcoords='offset points', fontsize=9, color=ALERT)
ax.xaxis.set_major_formatter(plt.FuncFormatter(usd_k))
ax.yaxis.set_major_formatter(plt.FuncFormatter(usd_k))
ax.set_xlabel('실제 SalePrice')
ax.set_ylabel('예측 SalePrice')
ax.set_xlim(lo * .9, hi * 1.03)
ax.set_ylim(lo * .9, hi * 1.03)
style_axes(ax, f'③ {best} 예측 — R² {r2_b:.3f}, 고가 구간에서 과소예측 경향',
           f'out-of-fold 예측 {len(df):,}건 · RMSE {rmse_b:,.0f} / MAE {mae_b:,.0f} · '
           f'빨간 표시 = 과제 1에서 확인한 이상치 {", ".join(map(str, OUTLIER_IDS))}번')
fig.tight_layout(rect=[0, 0.03, 1, 1])
footer(fig)
fig.savefig(IMG / '03_predictions_scatter.png', dpi=120)
plt.close(fig)

# ── 결과 출력 ─────────────────────────────────────────────────────
print(f'\n[최고 성능 모델] {best} (R²={scores.loc[0, "R2"]:.4f}, '
      f'표준편차 {scores.loc[0, "R2_std"]:.3f})')
print(f'  참고: {runner} R²={scores.loc[1, "R2"]:.4f}, '
      f'표준편차 {scores.loc[1, "R2_std"]:.3f}')

print('\n[A. 로그 타깃 실험 — 원본 달러 스케일 기준]')
print(log_cmp.round(4).to_string(index=False))

print('\n[B. Ridge alpha 탐색 결과]')
ridge_pipe = build('Ridge').fit(X_full, y_full)
print(f"  RidgeCV 선택 alpha = {ridge_pipe.named_steps['model'].alpha_:.4g}")
print(f"  Linear R² = {scores.loc[scores['Model'] == 'Linear Regression', 'R2'].iat[0]:.4f}"
      f" / Ridge R² = {scores.loc[scores['Model'] == 'Ridge', 'R2'].iat[0]:.4f}")

print(f'\n[C. 이상치 {OUTLIER_IDS} 제거 실험]')
print(abl_df.round(4).to_string(index=False))
print(f'\n그래프 3종 저장 완료 → {IMG}')

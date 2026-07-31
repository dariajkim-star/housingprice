# -*- coding: utf-8 -*-
"""개선 트랙용 Orange CSV 생성 + Orange 실측 R² 사전 계산

- housePricing_orange_improved.csv : 이상치 2건 제거 + 파생변수 8종을 구운 3-row header CSV
  (TargetEncoder는 CSV에 박으면 fold 누수이므로 제외 — Orange는 자체 One-Hot 처리)
- 생성 후, 이 스크립트를 Orange 포터블 파이썬으로 실행하면 Orange의 CrossValidation으로
  튜닝 GB의 R²를 미리 계산한다 (GUI Test & Score와 동일 로직).

실행:
  일반 파이썬  : CSV 생성만
  Orange 파이썬: CSV 생성 + Orange CV 실측
    "C:\\Users\\user\\Downloads\\Orange3-3.40.0\\Orange\\python.exe" 03_orange/make_orange_improved.py
"""
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE.parent / 'data'
SRC = DATA_DIR / 'housePricing_selected.csv'
OUT = DATA_DIR / 'housePricing_orange_improved.csv'

df = pd.read_csv(SRC, encoding='utf-8-sig')

# 1) 이상치 제거 (SaleCondition=Partial 미완성 부분매매 · De Cock 권고)
mask = (df['GrLivArea'] > 4000) & (df['SalePrice'] < 300_000)
print(f'이상치 제거: Id {df.loc[mask, "Id"].tolist()} → n={int((~mask).sum())}')
df = df[~mask].reset_index(drop=True)

# 2) 파생변수 8종 (타깃 미사용)
df['TotalSF'] = df['GrLivArea'] + df['TotalBsmtSF']
df['HouseAge'] = 2010 - df['YearBuilt']
df['RemodAge'] = 2010 - df['YearRemodAdd']
df['IsRemodeled'] = (df['YearRemodAdd'] != df['YearBuilt']).astype(int)
df['Qual_x_Area'] = df['OverallQual'] * df['GrLivArea']
df['Qual_x_TotalSF'] = df['OverallQual'] * df['TotalSF']
df['HasFireplace'] = (df['Fireplaces'] > 0).astype(int)
df['LotRatio'] = (df['GrLivArea'] / df['LotArea']).round(6)

# 3) 3-row header (1행 이름 / 2행 타입 c·d / 3행 역할 class·meta)
cols = [c for c in df.columns if c not in ('Id', 'SalePrice')]
ordered = ['Id'] + cols + ['SalePrice']
df = df[ordered]
CATS = {'Neighborhood', 'ExterQual', 'KitchenQual', 'CentralAir'}
types = ['c'] + ['d' if c in CATS else 'c' for c in cols] + ['c']
roles = ['meta'] + [''] * len(cols) + ['class']

with open(OUT, 'w', encoding='utf-8', newline='') as f:
    f.write(','.join(ordered) + '\n')
    f.write(','.join(types) + '\n')
    f.write(','.join(roles) + '\n')
    df.to_csv(f, index=False, header=False)
print(f'저장: {OUT}  ({len(df)}행 × {len(ordered)}열, 파생변수 8종 포함)')

# 4) Orange가 있으면 GUI와 동일한 CV로 실측
try:
    import Orange
    from Orange.data import Table
    from Orange.evaluation import CrossValidation, R2, RMSE, MAE
    from Orange.modelling import GBLearner
except ImportError:
    print('\n(Orange 미탑재 파이썬 — CSV 생성만 완료. Orange python.exe로 재실행하면 실측 R²가 나온다)')
    raise SystemExit

data = Table(str(OUT))
print(f'\nOrange 로드: {len(data)}행, feature {len(data.domain.attributes)}개, '
      f'target={data.domain.class_var.name}')

gb = GBLearner(n_estimators=600, learning_rate=0.05, max_depth=3, subsample=0.8,
               random_state=42)
gb.name = 'Gradient Boosting (tuned)'
res = CrossValidation(k=5, random_state=42)(data, [gb])
print(f'\n[Orange CrossValidation 5-fold 실측 — GUI Test & Score와 동일 로직]')
print(f'  R²   = {R2(res)[0]:.4f}')
print(f'  RMSE = {RMSE(res)[0]:,.1f}')
print(f'  MAE  = {MAE(res)[0]:,.1f}')

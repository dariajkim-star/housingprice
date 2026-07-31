# -*- coding: utf-8 -*-
"""
과제 3 - Orange 회귀모델 개발의 Python(sklearn) 재현 스크립트

Orange의 Test & Score 위젯(5-fold 교차검증)과 동일한 실험을 sklearn으로 재현하여
실제 성능 수치(R2 / RMSE / MAE)를 산출한다.

입력 : data/housePricing_selected.csv  (과제 2 다중공선성 제거 확정본)
출력 : 03_orange/model_scores.csv
       03_orange/images/predictions_scatter.png
       콘솔 성능표

실행 : set PYTHONIOENCODING=utf-8 && python 03_orange/task3_sklearn_reference.py
"""

import os
import sys
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler
from sklearn.model_selection import KFold, cross_validate, cross_val_predict
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

# ---------------------------------------------------------------- 설정
RANDOM_STATE = 42
N_SPLITS = 5

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "03_orange")
IMG_DIR = os.path.join(OUT_DIR, "images")
DATA_PATH = os.path.join(BASE_DIR, "data", "housePricing_selected.csv")
os.makedirs(IMG_DIR, exist_ok=True)

# 한글 폰트 (윈도우)
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


def main():
    # ------------------------------------------------------------ 데이터 로드
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    print("=" * 78)
    print("과제 3 : Orange 회귀모델 개발 - sklearn 재현 (5-fold 교차검증)")
    print("=" * 78)
    print(f"데이터 : {DATA_PATH}")
    print(f"shape  : {df.shape[0]}행 x {df.shape[1]}열 / 결측치 {int(df.isna().sum().sum())}건")

    TARGET = "SalePrice"
    y = df[TARGET].astype(float)
    X = df.drop(columns=[TARGET, "Id"])  # Id는 meta(식별자)이므로 학습에서 제외

    # 순서형(품질 등급) : Ex > Gd > TA > Fa  (높을수록 좋음)
    QUAL_ORDER = ["Fa", "TA", "Gd", "Ex"]  # OrdinalEncoder는 오름차순 코드 부여
    ordinal_cols = ["ExterQual", "KitchenQual"]
    # 이진 범주 + 명목 범주 -> One-Hot
    onehot_cols = ["Neighborhood", "CentralAir"]
    numeric_cols = [c for c in X.columns if c not in ordinal_cols + onehot_cols]

    print(f"\n[특성 구성]")
    print(f"  수치형({len(numeric_cols)})   : {', '.join(numeric_cols)}")
    print(f"  순서형({len(ordinal_cols)})   : {', '.join(ordinal_cols)}  (Fa<TA<Gd<Ex)")
    print(f"  명목형({len(onehot_cols)})   : {', '.join(onehot_cols)}  -> One-Hot")

    def make_preprocessor(scale_numeric: bool):
        num_steps = [("scaler", StandardScaler())] if scale_numeric else []
        num_pipe = Pipeline(num_steps) if num_steps else "passthrough"
        ord_pipe = Pipeline(
            [("ord", OrdinalEncoder(categories=[QUAL_ORDER] * len(ordinal_cols)))]
            + ([("scaler", StandardScaler())] if scale_numeric else [])
        )
        return ColumnTransformer(
            [
                ("num", num_pipe, numeric_cols),
                ("ord", ord_pipe, ordinal_cols),
                ("cat", OneHotEncoder(handle_unknown="ignore", drop=None), onehot_cols),
            ]
        )

    # ------------------------------------------------------------ 모델 정의
    # 거리/규제 기반 모델(Linear, Ridge, kNN)은 스케일링 필요, 트리 기반은 불필요
    models = {
        "Linear Regression": (LinearRegression(), True),
        "Ridge": (Ridge(alpha=1.0, random_state=None), True),
        "Random Forest": (
            RandomForestRegressor(n_estimators=100, random_state=RANDOM_STATE, n_jobs=-1),
            False,
        ),
        "Gradient Boosting": (
            GradientBoostingRegressor(n_estimators=100, random_state=RANDOM_STATE),
            False,
        ),
        "kNN": (KNeighborsRegressor(n_neighbors=5), True),
    }

    cv = KFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    scoring = {
        "R2": "r2",
        "RMSE": "neg_root_mean_squared_error",
        "MAE": "neg_mean_absolute_error",
    }

    rows = []
    fitted_pipes = {}
    for name, (est, scale) in models.items():
        pipe = Pipeline([("prep", make_preprocessor(scale)), ("model", est)])
        fitted_pipes[name] = pipe
        res = cross_validate(pipe, X, y, cv=cv, scoring=scoring, n_jobs=None)
        rows.append(
            {
                "Model": name,
                "R2": res["test_R2"].mean(),
                "RMSE": -res["test_RMSE"].mean(),
                "MAE": -res["test_MAE"].mean(),
                "R2_std": res["test_R2"].std(),
                "FitTime_s": res["fit_time"].mean(),
            }
        )
        print(f"  - {name:<20s} 완료")

    scores = pd.DataFrame(rows).sort_values("R2", ascending=False).reset_index(drop=True)

    # ------------------------------------------------------------ 결과 출력
    print("\n" + "=" * 78)
    print(f"Test & Score 결과 ({N_SPLITS}-fold 교차검증, 정렬: R2 내림차순)")
    print("=" * 78)
    print(f"{'Model':<20s}{'R2':>10s}{'RMSE':>14s}{'MAE':>14s}{'R2 std':>10s}{'Fit(s)':>9s}")
    print("-" * 78)
    for _, r in scores.iterrows():
        print(
            f"{r['Model']:<20s}{r['R2']:>10.4f}{r['RMSE']:>14,.1f}"
            f"{r['MAE']:>14,.1f}{r['R2_std']:>10.4f}{r['FitTime_s']:>9.3f}"
        )
    print("-" * 78)

    out_csv = os.path.join(OUT_DIR, "model_scores.csv")
    scores.round(6).to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"\n[저장] 성능표 -> {out_csv}")

    # ------------------------------------------------------------ 최고 성능 모델 산점도
    best_name = scores.loc[0, "Model"]
    best_r2 = scores.loc[0, "R2"]
    print(f"[최고 성능 모델] {best_name}  (R2={best_r2:.4f})")

    y_pred = cross_val_predict(fitted_pipes[best_name], X, y, cv=cv)
    r2 = r2_score(y, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y, y_pred)))
    mae = mean_absolute_error(y, y_pred)

    fig, ax = plt.subplots(figsize=(8, 8), dpi=120)
    ax.scatter(y, y_pred, s=18, alpha=0.45, color="#1f77b4", edgecolors="none",
               label="예측 결과 (out-of-fold)")
    lo = float(min(y.min(), y_pred.min()))
    hi = float(max(y.max(), y_pred.max()))
    ax.plot([lo, hi], [lo, hi], "r--", lw=1.8, label="이상적 예측선 (y = x)")
    ax.set_xlabel("실제 SalePrice ($)", fontsize=12)
    ax.set_ylabel("예측 SalePrice ($)", fontsize=12)
    ax.set_title(
        f"실제값 vs 예측값 산점도 - {best_name}\n"
        f"5-fold CV : R² = {r2:.4f} / RMSE = {rmse:,.0f} / MAE = {mae:,.0f}",
        fontsize=13, pad=14,
    )
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(alpha=0.3, linestyle=":")
    ax.set_xlim(lo * 0.95, hi * 1.02)
    ax.set_ylim(lo * 0.95, hi * 1.02)
    fig.tight_layout()

    img_path = os.path.join(IMG_DIR, "predictions_scatter.png")
    fig.savefig(img_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[저장] 산점도   -> {img_path}")
    print("\n완료.")


if __name__ == "__main__":
    main()

# 과제 2. 공분산 · 다중공선성 진단과 제거 [20점]

## 무엇을
수치형 설명변수의 상관·공분산 행렬을 구하고, |r| ≥ 0.8 인 다중공선성 위험 쌍을 찾아 한쪽을 제거한 뒤 VIF 개선을 확인.

## 어떻게
- 실행: `python task2_vif.py`
- VIF는 statsmodels 없이 **numpy 직접 구현**: 각 변수를 나머지 설명변수로 OLS(`np.linalg.lstsq`) 회귀 → `VIF_i = 1 / (1 - R²_i)`
- 산출: `corr_matrix.csv`, `cov_matrix.csv`, `collinear_pairs.csv`, `vif_before_after.csv`, `task2_summary.json`, `images/` 4종
- 시각화 규칙은 과제 1과 동일 (회색=일반 / 남색=핵심 / 빨강=제거 대상, 제목은 결론을 명사형으로 서술)

---

## ① 공분산과 상관계수 — 왜 상관계수를 쓰는가
`images/01_cov_vs_corr.png`

문제지 요구대로 `df.cov()`와 `df.corr()`를 각각 구했다. 두 결과를 나란히 놓으면 **공분산을 그대로 쓰면 안 되는 이유**가 그대로 드러난다.

| feature | SalePrice와의 공분산 | SalePrice와의 상관 r | 상관 순위 |
|---|---:|---:|---:|
| **LotArea** | **209,211,070** (1위) | **0.26** | **12위 (최하위)** |
| GrLivArea | 29,581,867 | 0.71 | 2위 |
| TotalBsmtSF | 21,384,417 | 0.61 | 5위 |
| OverallQual | 약 8만 | 0.79 | 1위 |
| Fireplaces | 23,913 | 0.47 | 11위 |

LotArea(대지 면적)는 단위가 sq ft로 값 자체가 수천~수만 단위라 공분산이 압도적으로 크게 나온다.
하지만 표준화한 상관계수로 보면 **r = 0.26으로 최하위권**이다.
반대로 상관 1위인 OverallQual은 1~10 척도라 공분산으로는 하위권에 묻힌다.

> **공분산은 변수의 측정 단위에 의존하므로 변수 간 비교가 불가능하다.
> 따라서 다중공선성 진단은 표준화된 상관계수(그리고 VIF)로 수행한다.**

---

## ② 공선 쌍 탐지 — |r| ≥ 0.8, 3쌍
`images/02_heatmap_before.png` (하단 삼각형만 표시, |r|≥0.5만 수치 표기, 0.8 이상 셀만 빨간 테두리)

| 공선 쌍 | r | 유지 | r(유지, SalePrice) | 제거 | r(제거, SalePrice) |
|---|---|---|---|---|---|
| GarageCars ↔ GarageArea | 0.882 | **GarageCars** | 0.640 | GarageArea | 0.623 |
| GrLivArea ↔ TotRmsAbvGrd | 0.825 | **GrLivArea** | 0.709 | TotRmsAbvGrd | 0.534 |
| TotalBsmtSF ↔ 1stFlrSF | 0.820 | **TotalBsmtSF** | 0.614 | 1stFlrSF | 0.606 |

**제거 기준:** 각 쌍에서 SalePrice와의 상관이 더 **낮은** 쪽을 제거. 세 쌍 모두 의미상 중복(차고 규모 / 주택 규모 / 1층·지하 면적)이라 정보 손실이 사실상 없다.
- 차고: 대수(GarageCars)가 이산적이고 해석이 명확하며 상관도 높음 → 면적 제거
- 규모: 면적(GrLivArea)이 방 개수보다 SalePrice 설명력이 크게 앞섬(0.709 vs 0.534)
- 지하/1층: TotalBsmtSF가 지하 전체를 포괄해 정보량이 더 큼

**제거 목록:** `GarageArea`, `TotRmsAbvGrd`, `1stFlrSF`

### 제거 방식 검증
위 3쌍은 원본 상관행렬에서 **한 번에** 판정했다. 엄밀한 절차는 한 쌍을 제거할 때마다 상관을 재계산하고 다시 탐색하는 순차 방식이므로, 코드에서 두 방식을 모두 실행해 결과를 대조했다.

```
순차 재계산 방식과 결과 일치: True
```

두 방식 모두 `GarageArea → TotRmsAbvGrd → 1stFlrSF` 순으로 동일한 3개를 제거한다.

---

## ③ 제거 후 상관 구조
`images/03_heatmap_after.png`

제거 후 **설명변수 간 최대 상관은 0.63** (GrLivArea ↔ FullBath)으로, |r| ≥ 0.8 쌍이 완전히 사라졌다. 히트맵에 빨간 테두리가 하나도 남지 않는다.

---

## ④ VIF 제거 전 / 후
`images/04_vif_before_after.png` (덤벨 차트 — 회색 점 = 제거 전, 남색 점 = 제거 후, 빨간 점 = 제거된 변수)

| feature | VIF 제거 전 | VIF 제거 후 |
|---|---|---|
| GarageCars | 5.313 | **1.857** |
| GrLivArea | 5.306 | **2.692** |
| GarageArea | 4.995 | (제거) |
| 1stFlrSF | 3.778 | (제거) |
| TotalBsmtSF | 3.630 | **1.622** |
| TotRmsAbvGrd | 3.378 | (제거) |
| OverallQual | 2.864 | 2.813 |
| YearBuilt | 2.350 | 2.322 |
| FullBath | 2.238 | 2.167 |
| YearRemodAdd | 1.771 | 1.769 |
| Fireplaces | 1.448 | 1.400 |
| LotArea | 1.171 | 1.165 |

**최대 VIF 5.31 → 2.81.** 모든 변수가 VIF < 3 구간에 들어와 회귀계수 안정성이 확보됐다.
제거된 변수와 짝을 이루던 GarageCars(5.31→1.86)·GrLivArea(5.31→2.69)·TotalBsmtSF(3.63→1.62)에서 개선 폭이 가장 크고, 무관한 변수(LotArea 1.17→1.17)는 사실상 변화가 없다 — 제거가 의도한 지점에만 작용했다는 근거다.

### 판단 기준에 대한 중요한 단서
문제지는 "VIF > 10 이면 공선성 강함"을 기준으로 제시한다. 그러나 이 데이터에서는

```
제거 전 VIF > 10 인 변수: 0개  (최대 5.31)
```

즉 **VIF 단독 기준으로는 제거 대상이 하나도 없다.**
따라서 본 과제의 실제 제거 근거는 **|r| ≥ 0.8 상관 기준**이며, VIF는 제거의 근거가 아니라 **제거 효과를 사후 검증하는 지표**로 사용했다.
(부록 B의 "감축 전 최대 VIF ≈ 5.3"과 일치하는 결과다.)

YearBuilt ↔ YearRemodAdd 는 r = 0.59 로 임계값 0.8 미만이라 둘 다 유지했고, VIF도 2.3 수준으로 문제가 없다.

---

## 후속 과제로 넘기는 산출물
`../data/housePricing_selected.csv` — 제거 후 확정 feature 세트
- 수치형 9종: OverallQual, GrLivArea, GarageCars, TotalBsmtSF, FullBath, YearBuilt, YearRemodAdd, Fireplaces, LotArea
- 범주형 4종: Neighborhood, ExterQual, KitchenQual, CentralAir
- Target: SalePrice

→ **과제 3(Orange), 과제 4·5(Power BI), 과제 6(HTML)의 공통 입력**

### 과제 3에서 확인된 부수 효과
Orange/sklearn 5-fold 교차검증 결과 **Linear Regression R² 0.7881, Ridge R² 0.7883** 으로 차이가 0.0002에 불과했다.
Ridge는 다중공선성으로 인한 계수 불안정을 정규화로 억제하는 모델인데 개선 효과가 사실상 없다는 것은,
**이미 과제 2에서 공선성이 제거되어 정규화가 개입할 여지가 없었다**는 뜻이다. 제거 작업의 유효성을 뒷받침하는 간접 증거다.

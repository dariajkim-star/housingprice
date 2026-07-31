# 과제 2. 공분산 · 다중공선성 진단과 제거 [20점]

## 무엇을
수치형 설명변수의 상관·공분산 행렬을 구하고, |r| ≥ 0.8 인 다중공선성 위험 쌍을 찾아 한쪽을 제거한 뒤 VIF 개선을 확인.

## 어떻게
- 실행: `python task2_vif.py`
- VIF는 statsmodels 없이 **numpy 직접 구현**: 각 변수를 나머지 설명변수로 OLS(`np.linalg.lstsq`) 회귀 → `VIF_i = 1 / (1 - R²_i)`
- 산출: `corr_matrix.csv`, `cov_matrix.csv`, `collinear_pairs.csv`, `vif_before_after.csv`, `task2_summary.json`, `images/` 히트맵 2종 + VIF 비교 막대

## 발견된 공선 쌍 (|r| ≥ 0.8, 3쌍)

| 공선 쌍 | r | 유지 | r(유지, SalePrice) | 제거 | r(제거, SalePrice) |
|---|---|---|---|---|---|
| GarageCars ↔ GarageArea | 0.882 | **GarageCars** | 0.640 | GarageArea | 0.623 |
| GrLivArea ↔ TotRmsAbvGrd | 0.825 | **GrLivArea** | 0.709 | TotRmsAbvGrd | 0.534 |
| TotalBsmtSF ↔ 1stFlrSF | 0.820 | **TotalBsmtSF** | 0.614 | 1stFlrSF | 0.606 |

**제거 기준:** 각 쌍에서 SalePrice와의 상관이 더 **낮은** 쪽을 제거. 세 쌍 모두 의미상 중복(차고 규모 / 주택 규모 / 1층·지하 면적)이라 정보 손실이 사실상 없음.
- 차고: 대수(GarageCars)가 이산적이고 해석이 명확하며 상관도 높음 → 면적 제거
- 규모: 면적(GrLivArea)이 방 개수보다 SalePrice 설명력이 크게 앞섬(0.709 vs 0.534)
- 지하/1층: TotalBsmtSF가 지하 전체를 포괄해 정보량이 더 큼

**제거 목록:** `GarageArea`, `TotRmsAbvGrd`, `1stFlrSF`

## VIF 제거 전 / 후

| feature | VIF 제거 전 | VIF 제거 후 |
|---|---|---|
| GarageCars | 5.313 | 1.857 |
| GrLivArea | 5.306 | 2.692 |
| GarageArea | 4.995 | (제거) |
| 1stFlrSF | 3.778 | (제거) |
| TotalBsmtSF | 3.630 | 1.622 |
| TotRmsAbvGrd | 3.378 | (제거) |
| OverallQual | 2.864 | 2.813 |
| YearBuilt | 2.350 | 2.322 |
| FullBath | 2.238 | 2.167 |
| YearRemodAdd | 1.771 | 1.769 |
| Fireplaces | 1.448 | 1.400 |
| LotArea | 1.171 | 1.165 |

**최대 VIF 5.31 → 2.81** 로 하락. 모든 변수가 VIF < 3 구간에 들어와 회귀계수 안정성이 확보됨.
(YearBuilt ↔ YearRemodAdd 는 r=0.59 로 임계값 0.8 미만이라 둘 다 유지 — VIF도 2.3 수준으로 문제 없음)

## 후속 과제로 넘기는 산출물
`../data/housePricing_selected.csv` — 제거 후 확정 feature 세트
(수치형 9종: OverallQual, GrLivArea, GarageCars, TotalBsmtSF, FullBath, YearBuilt, YearRemodAdd, Fireplaces, LotArea
 + 범주형 4종: Neighborhood, ExterQual, KitchenQual, CentralAir + SalePrice)
→ **과제 3(Orange), 과제 4·5(Power BI), 과제 6(HTML)의 공통 입력**

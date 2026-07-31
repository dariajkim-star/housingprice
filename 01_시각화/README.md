# 과제 1. 주요 Feature 시각화 [15점]

## 무엇을
`housePricing_reduced.csv`(1,460행 × 18열, 결측 0)에서 SalePrice와 관련이 큰 feature의 분포·관계를 시각화.

## 어떻게
- 실행: `python task1_eda.py` (프로젝트 루트 기준 상대경로로 `../data/housePricing_reduced.csv` 로드, `encoding='utf-8-sig'`)
- 한글 폰트: Malgun Gothic, `axes.unicode_minus=False`
- 산출: `images/` 그래프 5종, `eda_summary.txt`(info·describe·결측), `task1_summary.json`(후속 과제 재사용용 요약 지표)

## 결과 요약 및 해석

| 그래프 | 파일 | 해석 |
|---|---|---|
| ① SalePrice 히스토그램 + 왜도 | `images/01_saleprice_hist.png` | 원자료 왜도 **1.88**로 오른쪽 꼬리가 김(고가 주택 소수). `log1p` 변환 시 왜도 **0.12**로 거의 정규에 근접 → 선형회귀 가정 충족에 유리. |
| ② OverallQual별 박스플롯 | `images/02_boxplot_overallqual.png` | 품질 등급이 오를수록 중앙값이 단조 증가하고 산포도 함께 커짐. 품질 8↑ 구간에서 가격 상승 폭이 가팔라짐. |
| ③ GrLivArea vs SalePrice + 회귀선 | `images/03_scatter_grlivarea.png` | r=0.71의 뚜렷한 양의 선형관계. 우하단에 면적은 크지만 가격이 낮은 이상치 2건(전형적인 Ames 이상치)이 보임. |
| ④ Neighborhood별 평균가 | `images/04_bar_neighborhood.png` | NoRidge·NridgHt·StoneBr가 상위, MeadowV·IDOTRR·BrDale이 하위. 지역 간 평균가 격차가 3배 이상 → 지역은 강한 설명 변수. |
| ⑤ (선택) 상관 히트맵 | `images/05_heatmap_corr.png` | OverallQual(0.79)·GrLivArea(0.71)가 최상위. 동시에 GarageCars↔GarageArea 등 설명변수끼리의 강상관도 관측 → 과제 2로 연결. |

## SalePrice 상관 상위
OverallQual 0.79 · GrLivArea 0.71 · GarageCars 0.64 · GarageArea 0.62 · TotalBsmtSF 0.61 · 1stFlrSF 0.61 · FullBath 0.56 · TotRmsAbvGrd 0.53

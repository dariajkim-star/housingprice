# 과제 5. 주요 영향 요인 — "SalePrice High"를 만드는 요인 [10점]

## 무엇을
Power BI **주요 영향 요인(Key Influencers)** 시각 개체로 고가 주택(High)을 만드는 핵심 요인을 정량적으로 도출.

## 어떻게 — 단계별
과제 4에서 만든 `housing.pbix` 를 그대로 이어서 사용한다 (같은 파일의 2페이지로 구성하면 제출이 간편).

### 1) 등급 계산 열 (과제 4에서 이미 생성했다면 건너뜀)
```dax
SalePrice_등급 =
IF ( 'data'[SalePrice] >= MEDIANX ( ALL ( 'data' ), 'data'[SalePrice] ), "High", "Low" )
```
- 중앙값 기준(약 $163,000)으로 High/Low가 대략 50:50으로 나뉜다.
- 상위 25% 기준으로 하고 싶으면 `MEDIANX` 대신 `PERCENTILEX.INC ( ALL('data'), 'data'[SalePrice], 0.75 )` 사용.

### 2) Key Influencers 시각 개체 설정
1. 시각화 창에서 **주요 영향 요인** 선택
2. **분석 대상(Analyze)** = `SalePrice_등급`
3. 우측 상단 드롭다운에서 **"High"** 선택 → "SalePrice_등급이 High가 될 가능성을 높이는 요인"
4. **설명 기준(Explain by)** 에 다음을 모두 추가:
   `OverallQual`, `GrLivArea`, `Neighborhood`, `ExterQual`, `KitchenQual`, `GarageCars`, `YearBuilt`, `TotalBsmtSF`, `CentralAir`
5. 하단 탭에서 **주요 영향 요인** / **주요 세그먼트** 두 뷰를 모두 캡처

> `GrLivArea`·`TotalBsmtSF`·`YearBuilt` 같은 연속형은 필드 우클릭 → **요약 안 함** 상태여야 영향 요인으로 올바르게 분석된다.

## 예상 상위 요인 (과제 1·2 결과와 대조용)
| 순위 | 요인 | 해석 방향 |
|---|---|---|
| 1 | **OverallQual** | 품질 등급이 1단계 오를 때 High가 될 확률이 수 배 상승. 과제 1의 r=0.79(최상위 상관)와 일치. |
| 2 | **GrLivArea** | 지상 면적이 넓을수록 High 확률 상승. 과제 1의 r=0.71, 산점도 기울기와 일치. |
| 3 | **Neighborhood** | NoRidge·NridgHt·StoneBr 등 상위 지역일 때 High 확률이 크게 증가. 과제 1 ④ 막대그래프의 상위 지역과 일치. |
| 4 | **ExterQual / KitchenQual = Ex 또는 Gd** | 외장·주방 품질이 Ex/Gd이면 High 확률 상승 (OverallQual과 같은 방향). |

**해석 시 주의:** 캡처에 표시되는 "n배" 수치는 실제 실행 결과 값을 그대로 적을 것. 위 표는 방향성 대조용이며, 실제 숫자는 화면에서 읽어 README에 반영한다.

## 제출물
- `images/key_influencers.png` — 주요 영향 요인 뷰 캡처
- `images/top_segments.png` — 주요 세그먼트 뷰 캡처
- 상위 요인 3가지 이상 + 영향 해석 (예: "OverallQual이 8 이상일 때 High일 확률이 n배")

## 과제 1·2와의 정합성
과제 1 상관 상위(OverallQual 0.79 > GrLivArea 0.71 > GarageCars 0.64)와 Key Influencers 순위가 대체로 일치하면, 서로 다른 방법론(피어슨 상관 vs 로지스틱 기반 영향도)이 같은 결론을 지지한다는 뜻이다. 불일치가 있다면 그 자체가 좋은 해석 포인트가 된다 (예: Neighborhood는 범주형이라 상관계수로는 잡히지 않지만 Key Influencers에서는 상위로 올라옴).

# 과제 4. Power BI 시각 개체 5종 [15점]

## 무엇을
Power BI Desktop으로 `data/housePricing_selected.csv`(과제 2 결과물)를 적재하고 서로 다른 시각 개체 5종으로 보고서 1페이지를 구성.

## 어떻게 — 단계별

### 1) 데이터 적재
1. Power BI Desktop 실행 → **데이터 가져오기 > 텍스트/CSV**
2. `C:\Users\user\Desktop\수업내용정리\260731\housingprice\data\housePricing_selected.csv` 선택
3. 파일 원본 = **65001: 유니코드(UTF-8)** 확인 (한글 깨짐 방지 — 공통 감점 항목)
4. **데이터 변환**에서 쿼리 이름을 `data` 로 변경 → **닫기 및 적용**
5. 데이터 형식 확인: SalePrice·GrLivArea·LotArea·TotalBsmtSF = 정수, OverallQual·GarageCars·FullBath·Fireplaces = 정수, YearBuilt·YearRemodAdd = 정수(날짜 아님), Neighborhood·ExterQual·KitchenQual·CentralAir = 텍스트

### 2) 계산 열 미리 생성 (과제 5로 바로 연결)
테이블 도구 > **새 열**:
```dax
SalePrice_등급 =
IF ( 'data'[SalePrice] >= MEDIANX ( ALL ( 'data' ), 'data'[SalePrice] ), "High", "Low" )
```
측정값(카드용):
```dax
평균 SalePrice = AVERAGE ( 'data'[SalePrice] )
주택 수 = COUNTROWS ( 'data' )
최고 SalePrice = MAX ( 'data'[SalePrice] )
```

### 3) 시각 개체 5종

| # | 시각 개체 | 필드 배치 | 용도 설명 |
|---|---|---|---|
| ① | **카드(Card)** ×3 | `평균 SalePrice` / `주택 수` / `최고 SalePrice` | 전체 시장 규모와 평균 가격 수준을 한눈에 보여주는 KPI. 슬라이서와 연동돼 필터 상황을 즉시 반영. |
| ② | **묶은 세로 막대형** | X축=`Neighborhood`, Y축=`평균 SalePrice`, 정렬=Y축 내림차순 | 지역별 가격 서열을 비교. NoRidge·NridgHt·StoneBr 상위 vs MeadowV·IDOTRR 하위로 3.4배 격차를 드러냄. |
| ③ | **분산형(산점도)** | X축=`GrLivArea`, Y축=`SalePrice`(요약 안 함), 범례=`OverallQual` | 면적-가격의 양의 선형관계(r=0.71)를 보여주고, 색(품질)으로 같은 면적에서도 품질이 가격을 끌어올림을 확인. |
| ④ | **꺾은선형** | X축=`YearBuilt`, Y축=`평균 SalePrice` | 건축연도별 평균가 추이. 최근 건축일수록 우상향하는 신축 프리미엄을 확인. |
| ⑤ | **슬라이서** | 필드=`Neighborhood` (드롭다운) + `OverallQual` (범위 슬라이더) | 지역·품질 조건을 바꿔가며 위 4개 시각 개체를 상호작용 필터링. |

> 산점도에서 `SalePrice` 필드를 끌어놓으면 기본이 **합계**이므로, 필드 우클릭 → **요약 안 함**으로 반드시 변경해야 1460개 점이 개별로 찍힌다.

## 제출물
- `housing.pbix` (이 폴더에 저장)
- `images/report_page.png` — 보고서 페이지 전체 캡처
- 위 표의 "용도 설명" 열이 각 시각 개체 1줄 설명에 해당

## 참고 — 예상 결과 대조
과제 1의 그래프(`01_시각화/images/`)와 같은 형태가 나와야 정상이다. 지역별 막대 순위와 산점도 기울기가 과제 1 결과와 일치하는지 대조하면 검산이 된다.

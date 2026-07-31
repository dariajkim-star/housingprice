# -*- coding: utf-8 -*-
"""
과제 3 보조 스크립트 : Orange용 자산 생성 + .ows 스키마 자체검증

1) data/housePricing_orange.csv 생성
   Orange 3-row header 형식
     1행 = 컬럼명
     2행 = 타입   (c=continuous, d=discrete, s=string)
     3행 = 역할   (class=목표변수, meta=메타, ignore=제외, 빈칸=feature)
   -> File 위젯이 이 파일을 읽으면 SalePrice가 자동으로 target(class)으로,
      Id가 자동으로 meta로 지정되므로 GUI에서 별도 설정이 필요 없다.

2) 03_orange/housing_regression.ows 생성 (Orange canvas XML 스키마 v2.0)

3) 생성된 .ows를 다시 파싱하여 구조 검증 (노드/링크/프로퍼티 역직렬화)

실행 : python 03_orange/make_orange_assets.py
"""

import base64
import io
import os
import pickle
import sys
import types
import xml.etree.ElementTree as ET
from xml.dom import minidom

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "03_orange")
DATA_DIR = os.path.join(BASE_DIR, "data")
SRC_CSV = os.path.join(DATA_DIR, "housePricing_selected.csv")
ORANGE_CSV = os.path.join(DATA_DIR, "housePricing_orange.csv")
OWS_PATH = os.path.join(OUT_DIR, "housing_regression.ows")


# =====================================================================
# 1) Orange 3-row header CSV
# =====================================================================
TYPES = {
    "Id": "c",
    "OverallQual": "c",
    "GrLivArea": "c",
    "GarageCars": "c",
    "TotalBsmtSF": "c",
    "FullBath": "c",
    "YearBuilt": "c",
    "YearRemodAdd": "c",
    "Fireplaces": "c",
    "LotArea": "c",
    "Neighborhood": "d",
    "ExterQual": "d",
    "KitchenQual": "d",
    "CentralAir": "d",
    "SalePrice": "c",
}
ROLES = {"Id": "meta", "SalePrice": "class"}  # 나머지는 빈칸 = feature


def build_orange_csv():
    df = pd.read_csv(SRC_CSV, encoding="utf-8-sig")
    cols = list(df.columns)
    buf = io.StringIO()
    buf.write(",".join(cols) + "\n")
    buf.write(",".join(TYPES[c] for c in cols) + "\n")
    buf.write(",".join(ROLES.get(c, "") for c in cols) + "\n")
    df.to_csv(buf, index=False, header=False, lineterminator="\n")
    with open(ORANGE_CSV, "w", encoding="utf-8", newline="") as f:
        f.write(buf.getvalue())
    print(f"[생성] Orange 3-row header CSV -> {ORANGE_CSV}")
    return cols


# =====================================================================
# 2) 위젯 settings 직렬화 헬퍼
# =====================================================================
# Orange의 RecentPath 클래스를 pickle 호환 스텁으로 재현한다.
# pickle은 클래스 본체가 아니라 (module, qualname) 참조만 저장하므로,
# Orange가 설치된 환경에서 로드하면 진짜 RecentPath로 복원된다.
_RECENTPATH_MODULE = "orangewidget.utils.filedialogs"


class RecentPath:
    """orangewidget.utils.filedialogs.RecentPath 와 동일한 상태를 갖는 스텁"""

    def __init__(self, abspath, prefix, relpath, title="", sheet="", file_format=None):
        self.abspath = abspath
        self.prefix = prefix
        self.relpath = relpath
        self.title = title
        self.sheet = sheet
        self.file_format = file_format

    def __repr__(self):
        return f"RecentPath({self.abspath!r})"


RecentPath.__module__ = _RECENTPATH_MODULE
# 자체검증(역직렬화) 시 위 모듈을 찾을 수 있도록 가짜 모듈을 등록
_stub_mod = types.ModuleType(_RECENTPATH_MODULE)
_stub_mod.RecentPath = RecentPath
sys.modules.setdefault(_RECENTPATH_MODULE, _stub_mod)
sys.modules.setdefault("orangewidget", types.ModuleType("orangewidget"))
sys.modules.setdefault("orangewidget.utils", types.ModuleType("orangewidget.utils"))


def pickle_props(obj) -> str:
    """Orange canvas가 쓰는 format='pickle' 표현 : base64(pickle)"""
    return base64.encodebytes(pickle.dumps(obj, protocol=4)).decode("ascii")


def literal_props(obj) -> str:
    """Orange canvas가 쓰는 format='literal' 표현 : repr() 문자열"""
    return repr(obj)


# =====================================================================
# 3) .ows 스키마 작성
# =====================================================================
# (id, 표시제목, qualified_name, (x, y))
NODES = [
    (0, "File",               "Orange.widgets.data.owfile.OWFile",                       (60,  260)),
    (1, "Select Columns",     "Orange.widgets.data.owselectcolumns.OWSelectAttributes",   (210, 260)),
    (2, "Linear Regression",  "Orange.widgets.model.owlinearregression.OWLinearRegression", (380,  40)),
    (3, "Ridge Regression",   "Orange.widgets.model.owlinearregression.OWLinearRegression", (380, 130)),
    (4, "Random Forest",      "Orange.widgets.model.owrandomforest.OWRandomForest",       (380, 220)),
    (5, "Gradient Boosting",  "Orange.widgets.model.owgradientboosting.OWGradientBoosting", (380, 310)),
    (6, "kNN",                "Orange.widgets.model.owknn.OWKNNLearner",                  (380, 400)),
    (7, "Test and Score",     "Orange.widgets.evaluate.owtestandscore.OWTestAndScore",    (600, 150)),
    (8, "Predictions",        "Orange.widgets.evaluate.owpredictions.OWPredictions",      (600, 360)),
    (9, "Scatter Plot",       "Orange.widgets.visualize.owscatterplot.OWScatterPlot",     (780, 360)),
    (10, "Data Table",        "Orange.widgets.data.owtable.OWTable",                  (210, 400)),
]

LEARNER_IDS = [2, 3, 4, 5, 6]

LINKS = []
_lid = 0


def add_link(src, snk, sch, kch):
    global _lid
    LINKS.append((_lid, src, snk, sch, kch))
    _lid += 1


add_link(0, 1, "Data", "Data")           # File -> Select Columns
add_link(1, 10, "Data", "Data")          # Select Columns -> Data Table (데이터 확인용)
add_link(1, 7, "Data", "Data")           # Select Columns -> Test and Score
for nid in LEARNER_IDS:
    add_link(nid, 7, "Learner", "Learner")   # 학습기 5개 -> Test and Score
    add_link(1, nid, "Data", "Data")         # 데이터 -> 학습기 (Model 출력 생성용)
    add_link(nid, 8, "Model", "Predictors")  # 학습된 모델 -> Predictions
add_link(1, 8, "Data", "Data")           # Select Columns -> Predictions
add_link(8, 9, "Predictions", "Data")    # Predictions -> Scatter Plot


def build_ows():
    scheme = ET.Element(
        "scheme",
        {
            "version": "2.0",
            "title": "House Price Regression (과제 3)",
            "description": (
                "Ames Housing 주택가격 회귀 분석 워크플로우.\n"
                "File -> Select Columns -> Test and Score(5-fold CV)에 "
                "Linear Regression / Ridge / Random Forest / Gradient Boosting / kNN "
                "5개 학습기를 연결하고, Predictions -> Scatter Plot 으로 "
                "실제값 대비 예측값을 확인한다."
            ),
        },
    )

    nodes_el = ET.SubElement(scheme, "nodes")
    for nid, title, qname, (x, y) in NODES:
        ET.SubElement(
            nodes_el,
            "node",
            {
                "id": str(nid),
                "name": title,
                "qualified_name": qname,
                "project_name": "Orange3",
                "version": "",
                "title": title,
                "position": f"({float(x)}, {float(y)})",
            },
        )

    links_el = ET.SubElement(scheme, "links")
    for lid, src, snk, sch, kch in LINKS:
        ET.SubElement(
            links_el,
            "link",
            {
                "id": str(lid),
                "source_node_id": str(src),
                "sink_node_id": str(snk),
                "source_channel": sch,
                "sink_channel": kch,
                "enabled": "true",
            },
        )

    ann_el = ET.SubElement(scheme, "annotations")
    ET.SubElement(
        ann_el,
        "text",
        {
            "id": "0",
            "type": "text/plain",
            "rect": "(40.0, 470.0, 700.0, 90.0)",
            "font-family": "Helvetica",
            "font-size": "12",
        },
    ).text = (
        "과제 3 : Orange 회귀모델 개발 (5개 알고리즘)\n"
        "File 위젯은 data/housePricing_orange.csv (Orange 3-row header)를 읽으며 "
        "SalePrice=target(class), Id=meta 가 자동 지정됩니다.\n"
        "Test and Score : Cross validation, Number of folds = 5 로 설정되어 있습니다."
    )

    ET.SubElement(scheme, "thumbnail")

    props_el = ET.SubElement(scheme, "node_properties")

    # --- File 위젯 : 읽을 CSV 경로 지정 --------------------------------
    rp = RecentPath(
        abspath=os.path.abspath(ORANGE_CSV),
        prefix="basedir",
        relpath=os.path.join("..", "data", "housePricing_orange.csv"),
        title="",
        sheet="",
        file_format=None,
    )
    file_settings = {
        "__version__": 3,
        "source": 0,          # LOCAL_FILE
        "recent_paths": [rp],
        "recent_urls": [],
        "sheet_names": {},
        "url": "",
        "controlAreaVisible": True,
        "savedWidgetGeometry": None,
    }
    ET.SubElement(
        props_el, "properties", {"node_id": "0", "format": "pickle"}
    ).text = pickle_props(file_settings)

    # --- Linear Regression (OLS, 규제 없음) ---------------------------
    ET.SubElement(
        props_el, "properties", {"node_id": "2", "format": "literal"}
    ).text = literal_props(
        {"learner_name": "Linear Regression", "reg_type": 0, "fit_intercept": True}
    )

    # --- Ridge Regression (동일 위젯, 규제 = Ridge) --------------------
    # Orange에는 독립된 Ridge 위젯이 없고, Linear Regression 위젯의
    # Regularization 옵션(0=None/OLS, 1=Ridge, 2=Lasso, 3=Elastic Net)으로 지정한다.
    ET.SubElement(
        props_el, "properties", {"node_id": "3", "format": "literal"}
    ).text = literal_props(
        {"learner_name": "Ridge", "reg_type": 1, "alpha_index": 6, "fit_intercept": True}
    )

    # --- Test and Score : 5-fold 교차검증 -----------------------------
    # resampling 0 = Cross validation, n_folds 는 [2,3,5,10,20] 인덱스 -> 2 == 5-fold
    ET.SubElement(
        props_el, "properties", {"node_id": "7", "format": "literal"}
    ).text = literal_props(
        {"resampling": 0, "n_folds": 2, "cv_stratified": False, "shuffle_stratified": True}
    )

    xml = ET.tostring(scheme, encoding="utf-8")
    pretty = minidom.parseString(xml).toprettyxml(indent="  ", encoding="utf-8")
    with open(OWS_PATH, "wb") as f:
        f.write(pretty)
    print(f"[생성] Orange 워크플로우      -> {OWS_PATH}")


# =====================================================================
# 4) 자체검증
# =====================================================================
def validate():
    tree = ET.parse(OWS_PATH)
    root = tree.getroot()
    assert root.tag == "scheme", "루트 엘리먼트가 scheme 이 아님"
    assert root.get("version") == "2.0"

    nodes = root.find("nodes").findall("node")
    ids = {int(n.get("id")) for n in nodes}
    for n in nodes:
        assert n.get("qualified_name") and "." in n.get("qualified_name")
        # position 은 "(x, y)" 튜플 리터럴이어야 함
        import ast
        pos = ast.literal_eval(n.get("position"))
        assert isinstance(pos, tuple) and len(pos) == 2

    links = root.find("links").findall("link")
    for l in links:
        assert int(l.get("source_node_id")) in ids
        assert int(l.get("sink_node_id")) in ids
        assert l.get("source_channel") and l.get("sink_channel")

    import ast
    for p in root.find("node_properties").findall("properties"):
        fmt = p.get("format")
        if fmt == "pickle":
            obj = pickle.loads(base64.decodebytes(p.text.encode("ascii")))
            assert isinstance(obj, dict)
            if "recent_paths" in obj:
                assert os.path.exists(obj["recent_paths"][0].abspath), "CSV 경로 없음"
        elif fmt == "literal":
            assert isinstance(ast.literal_eval(p.text), dict)
        else:
            raise AssertionError(f"알 수 없는 properties format: {fmt}")

    print(f"[검증] 노드 {len(nodes)}개 / 링크 {len(links)}개 / "
          f"properties {len(root.find('node_properties'))}개 - 구조 검증 통과")
    print("[주의] 이 검증은 XML 구조 + settings 역직렬화 검증이며, "
          "Orange3가 설치되어 있지 않아 실제 Orange 스키마 리더로는 검증하지 못했습니다.")


if __name__ == "__main__":
    build_orange_csv()
    build_ows()
    validate()

"""東北6県ドラッグストア調査 - 設定"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SHARED_DIR = ROOT_DIR / "shared"
PREFECTURES_DIR = ROOT_DIR / "prefectures"

PREFECTURES = {
    "01_青森県": {
        "code": "02",
        "name": "青森県",
        "short": "青森",
        "center": (40.8244, 140.7400),
        "zoom": 8,
    },
    "02_岩手県": {
        "code": "03",
        "name": "岩手県",
        "short": "岩手",
        "center": (39.7036, 141.1527),
        "zoom": 8,
    },
    "03_宮城県": {
        "code": "04",
        "name": "宮城県",
        "short": "宮城",
        "center": (38.2682, 140.8720),
        "zoom": 9,
    },
    "04_秋田県": {
        "code": "05",
        "name": "秋田県",
        "short": "秋田",
        "center": (39.7186, 140.1023),
        "zoom": 8,
    },
    "05_山形県": {
        "code": "06",
        "name": "山形県",
        "short": "山形",
        "center": (38.2404, 140.3633),
        "zoom": 8,
    },
    "06_福島県": {
        "code": "07",
        "name": "福島県",
        "short": "福島",
        "center": (37.7500, 140.4678),
        "zoom": 8,
    },
    "07_愛知県": {
        "code": "23",
        "name": "愛知県",
        "short": "愛知",
        "center": (35.1802, 136.9066),
        "zoom": 9,
    },
    "08_和歌山県": {
        "code": "30",
        "name": "和歌山県",
        "short": "和歌山",
        "center": (34.2260, 135.1675),
        "zoom": 9,
    },
}

# 東北で出店可能性のある主要チェーン（自動判定の第2段階）
KNOWN_CHAINS = [
    "スギ薬局",
    "スギドラッグ",
    "Vドラッグ",
    "GENKY",
    "ゲンキー",
    "ZIPドラッグ",
    "マツモトキヨシ",
    "マツキヨ",
    "ドラッグスギヤマ",
    "ツルハドラッグ",
    "ウエルシア",
    "サンドラック",
    "ココカラファイン",
    "ドラッグユタカ",
    "コスモス",
    "クスリのアオキ",
    "セキ薬品",
    "よどやドラッグ",
    "カワachi",
    "カワチ薬品",
    "トモズ",
    "ダイコクドラッグ",
    "キリン堂",
    "サツドラ",
    "コクミン",
    "なの花ドラッグ",
    "クリエイト",
    "セイムス",
    "ハックドラッグ",
    "杏林堂",
    "キョーリン",
]

# 店舗名→チェーン名の正規化
CHAIN_NORMALIZE = {
    "スギドラッグ": "スギ薬局",
    "ゲンキー": "GENKY",
    "マツキヨ": "マツモトキヨシ",
    "カワachi": "カワチ薬品",
    "カワチ薬品": "カワチ薬品",
}

EXCLUDE_NAME_KEYWORDS = ["薬局", "調剤", "処方箋", "Pharmacy"]

TOHOKU_SLUGS = [
    "01_青森県",
    "02_岩手県",
    "03_宮城県",
    "04_秋田県",
    "05_山形県",
    "06_福島県",
]

# 愛知県プロジェクトと統一したチェーン色
CHAIN_COLORS = {
    "スギ薬局": "#E74C3C",
    "Vドラッグ": "#2ECC71",
    "GENKY": "#3498DB",
    "ZIPドラッグ": "#F39C12",
    "マツモトキヨシ": "#9B59B6",
    "ドラッグスギヤマ": "#1ABC9C",
    "ツルハドラッグ": "#E67E22",
    "ウエルシア": "#8E44AD",
    "サンドラック": "#16A085",
    "ココカラファイン": "#EC7063",
    "ドラッグユタカ": "#A04000",
    "コスモス": "#5DADE2",
    "カワチ薬品": "#EF6C00",
    "サンドラッグ": "#00838F",
    "クスリのアオキ": "#F9A825",
    "トモズ": "#009688",
    "ダイコクドラッグ": "#4E342E",
    "コクミン": "#AD1457",
    "なの花ドラッグ": "#FF6F00",
    "クリエイト": "#546E7A",
    "セキ薬品": "#37474F",
    "よどやドラッグ": "#2E7D32",
    "キリン堂": "#7B1FA2",
    "サツドラ": "#00695C",
    "ハックドラッグ": "#00897B",
    # 東北・地域チェーン
    "薬王堂": "#1565C0",
    "ハッピードラッグ": "#C62828",
    "ドラッグヤマザワ": "#558B2F",
    "スーパードラッグアサヒ": "#4527A0",
    "セイムス": "#795548",
    "ドラッグストアモリ": "#5E35B1",
    "ハシドラッグ": "#303F9F",
    "イオンドラッグ": "#BF360C",
    "アークドラッグ": "#455A64",
    "杏林堂": "#673AB7",
    "キョーリン": "#FF9800",
    "その他": "#808080",
    "不明": "#B0BEC5",
}

# 凡例用カテゴリ（表示順）
CHAIN_CATEGORIES = {
    "全国チェーン": [
        "ツルハドラッグ", "ウエルシア", "マツモトキヨシ", "サンドラッグ",
        "クスリのアオキ", "カワチ薬品", "コスモス", "ココカラファイン",
        "スギ薬局", "Vドラッグ", "GENKY", "トモズ", "ダイコクドラッグ",
        "コクミン", "なの花ドラッグ",
    ],
    "東北・地域チェーン": [
        "薬王堂", "ハッピードラッグ", "ドラッグヤマザワ", "スーパードラッグアサヒ",
        "セイムス", "ドラッグストアモリ", "ハシドラッグ", "イオンドラッグ",
        "アークドラッグ", "サンドラック",
    ],
    "独立店・その他": ["その他", "不明"],
}

GSI_N03_BASE = "https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N03.html"

# 東北6県統合データ
TOHOKU = {
    "name": "東北地方",
    "center": (39.5, 140.8),
    "zoom": 6,
}
TOHOKU_DIR = ROOT_DIR / "tohoku"

# 愛知県プロジェクトと統一したコロプレス配色
DENSITY_CHOROPLETH_COLORS = [
    "#f7fbff", "#deebf7", "#c6dbef", "#9ecae1", "#6baed6",
    "#4292c6", "#2171b5", "#08519c", "#08306b",
]
# 密度コロプレス: 0〜50固定。25まで薄色域、25〜50で急峻に濃色化
DENSITY_CHOROPLETH_VMIN = 0
DENSITY_CHOROPLETH_VMAX = 50
DENSITY_CHOROPLETH_MID = 25
DENSITY_CHOROPLETH_MID_POS = 0.32
DENSITY_CHOROPLETH_UPPER_GAMMA = 0.85
DENSITY_CHOROPLETH_UPPER_BUMP = 0.09
AGING_CHOROPLETH_COLORS = ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]

# 地図の境界線スタイル（愛知県プロジェクト準拠）
MUNI_BORDER_COLOR = "#666666"
MUNI_BORDER_WEIGHT = 2
PREF_BOUNDARY_COLOR = "#d32f2f"
PREF_BOUNDARY_WEIGHT = MUNI_BORDER_WEIGHT
CHOROPLETH_BORDER_COLOR = "black"
CHOROPLETH_BORDER_WEIGHT = 0.5

# GeoJSON 軽量化（地図 HTML への埋め込みサイズ削減）
GEOJSON_SIMPLIFY_TOLERANCE = 0.002
GEOJSON_COORD_PRECISION = 4

# 国勢調査2020 市区町村別（e-Stat 統計表ID）
ESTAT_POPULATION_TABLE = "0003445078"
ESTAT_AGING_TABLE = "0003445078"

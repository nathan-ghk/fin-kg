import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import os
import re

load_dotenv()

# ===== 1. DB 연결 설정 =====
conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "5432"),
    dbname=os.getenv("DB_NAME", "fk"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD"),
)
cur = conn.cursor()

# ===== 2. 테이블 생성 DDL =====
CREATE_SQL = """
DROP TABLE IF EXISTS etf.etf_info;

CREATE TABLE etf.etf_info (
    symbol       VARCHAR(10)   PRIMARY KEY,                  -- 종목코드 (ID)
    bm_index     VARCHAR(100),                               -- 벤치마크 지수
    lst_date     DATE,                                       -- 상장일
    am_company   VARCHAR(100),                               -- 자산운용사
    mkt_capital  VARCHAR(50),                                -- 시가총액 (원문 유지)
    aum          VARCHAR(50),                                -- 순자산총액 (원문 유지)
    leverage     VARCHAR(10),                                -- 레버리지
    nav          NUMERIC(15, 2),                             -- 순자산가치
    dsc_rate     NUMERIC(7, 4),                              -- 괴리율(%)
    tot_expense  NUMERIC(7, 4),                              -- 총보수(%)
    trk_error    NUMERIC(7, 4),                              -- 추적오차(%)
    stt          VARCHAR(20),                                -- 증권거래세
    cgt          VARCHAR(100),                               -- 양도소득세
    dvt          VARCHAR(20),                                -- 배당소득세
    created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE  etf.etf_info             IS 'ETF 종목 기본 정보';
COMMENT ON COLUMN etf.etf_info.symbol      IS '종목코드';
COMMENT ON COLUMN etf.etf_info.bm_index    IS '벤치마크 지수';
COMMENT ON COLUMN etf.etf_info.lst_date    IS '상장일';
COMMENT ON COLUMN etf.etf_info.am_company  IS '자산운용사';
COMMENT ON COLUMN etf.etf_info.mkt_capital IS '시가총액';
COMMENT ON COLUMN etf.etf_info.aum         IS '순자산총액(AUM)';
COMMENT ON COLUMN etf.etf_info.leverage    IS '레버리지 배수';
COMMENT ON COLUMN etf.etf_info.nav         IS '순자산가치(NAV)';
COMMENT ON COLUMN etf.etf_info.dsc_rate    IS '괴리율(%)';
COMMENT ON COLUMN etf.etf_info.tot_expense IS '총보수율(%)';
COMMENT ON COLUMN etf.etf_info.trk_error   IS '추적오차(%)';
COMMENT ON COLUMN etf.etf_info.stt         IS '증권거래세';
COMMENT ON COLUMN etf.etf_info.cgt         IS '양도소득세';
COMMENT ON COLUMN etf.etf_info.dvt         IS '배당소득세';
"""

cur.execute(CREATE_SQL)
conn.commit()
print("✅ 테이블 생성 완료")

# ===== 3. 데이터 전처리 함수 =====
def parse_date(s):
    """'2002. 10. 14.' → '2002-10-14'"""
    if pd.isna(s) or s in ("-", ""):
        return None
    s = re.sub(r"[.\s]", "", str(s))   # 점/공백 제거 → '20021014'
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"

def parse_percent(s):
    """'-0.04%' → -0.04"""
    if pd.isna(s) or s in ("-", ""):
        return None
    return float(str(s).replace("%", "").replace(",", "").strip())

def parse_number(s):
    """'121,854' → 121854.0"""
    if pd.isna(s) or s in ("-", ""):
        return None
    return float(str(s).replace(",", "").strip())

def clean_str(s):
    if pd.isna(s):
        return None
    return str(s).strip()

# ===== 4. CSV 로드 & 변환 =====
df = pd.read_csv("./results_agg.csv",encoding = 'utf-8', dtype={"symbol": str})  # symbol 앞자리 0 보존

df["lst_date"]    = df["lst_date"].apply(parse_date)
df["nav"]         = df["nav"].apply(parse_number)
df["dsc_rate"]    = df["dsc_rate"].apply(parse_percent)
df["tot_expense"] = df["tot_expense"].apply(parse_percent)
df["trk_error"]   = df["trk_error"].apply(parse_percent)

for col in ["symbol", "bm_index", "am_company", "mkt_capital", "aum",
            "leverage", "stt", "cgt", "dvt"]:
    df[col] = df[col].apply(clean_str)

# ===== 5. 일괄 INSERT =====
records = df[[
    "symbol", "bm_index", "lst_date", "am_company", "mkt_capital", "aum",
    "leverage", "nav", "dsc_rate", "tot_expense", "trk_error",
    "stt", "cgt", "dvt"
]].values.tolist()

INSERT_SQL = """
INSERT INTO etf.etf_info (
    symbol, bm_index, lst_date, am_company, mkt_capital, aum,
    leverage, nav, dsc_rate, tot_expense, trk_error, stt, cgt, dvt
) VALUES %s
ON CONFLICT (symbol) DO UPDATE SET
    bm_index    = EXCLUDED.bm_index,
    lst_date    = EXCLUDED.lst_date,
    am_company  = EXCLUDED.am_company,
    mkt_capital = EXCLUDED.mkt_capital,
    aum         = EXCLUDED.aum,
    leverage    = EXCLUDED.leverage,
    nav         = EXCLUDED.nav,
    dsc_rate    = EXCLUDED.dsc_rate,
    tot_expense = EXCLUDED.tot_expense,
    trk_error   = EXCLUDED.trk_error,
    stt         = EXCLUDED.stt,
    cgt         = EXCLUDED.cgt,
    dvt         = EXCLUDED.dvt;
"""

execute_values(cur, INSERT_SQL, records)
conn.commit()
print(f"✅ {len(records)}건 적재 완료")

cur.close()
conn.close()

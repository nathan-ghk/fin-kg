import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import os
import re

load_dotenv()

# ===== 1. DB 연결 =====
conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "5432"),
    dbname=os.getenv("DB_NAME", "fk"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD"),
)
cur = conn.cursor()

# ===== 2. 테이블 생성 DDL =====
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS etf.etf_portfolio (
    id           SERIAL PRIMARY KEY,
    symbol       VARCHAR(10),                 -- ETF 종목코드 (FK 역할)
    stock_nm   VARCHAR(100),                -- 구성 종목명
    stock_qty     BIGINT,                      -- 주식수
    stock_weight       NUMERIC(7, 4),               -- 비중 (%)
    stock_price        BIGINT,                      -- 시세 (현재가)
    stock_change  VARCHAR(100),                -- 전일대비 (상승/하락 정보)
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성 (조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_portfolio_symbol ON etf.etf_portfolio(symbol);

COMMENT ON TABLE etf.etf_portfolio IS 'ETF 구성 종목 상세 내역 (PDF)';
"""

cur.execute(CREATE_TABLE_SQL)
conn.commit()

# ===== 3. 데이터 전처리 함수 =====
def clean_quantity(s):
    """ '7,022 주' -> 7022 """
    if pd.isna(s): return 0
    return int(re.sub(r"[^0-9]", "", str(s)))

def clean_weight(s):
    """ '32.90 %' -> 32.90 """
    if pd.isna(s): return 0.0
    return float(str(s).replace("%", "").replace(",", "").strip())

def clean_price(s):
    """ '287,250' -> 287250 """
    if pd.isna(s): return 0
    return int(re.sub(r"[^0-9]", "", str(s)))

# ===== 4. 샘플 데이터 생성 (User 제공 데이터 기반) =====
# 실제로는 pd.read_csv() 등으로 불러오시면 됩니다.
# data = [
#     ["삼성전자", "7,022 주", "32.90 %", "287,250", "상승 1,750 (+0.61%)", "069500"],
#     ["SK하이닉스", "834 주", "25.73 %", "1,945,000", "상승 65,000 (+3.46%)", "069500"],
#     ["SK스퀘어", "139 주", "2.70 %", "1,192,000", "상승 5,000 (+0.42%)", "069500"],
#     ["현대차", "205 주", "2.17 %", "686,500", "상승 40,500 (+6.27%)", "069500"],
#     ["두산에너빌리티", "653 주", "1.37 %", "131,500", "상승 3,500 (+2.73%)", "069500"]
# ]

data = pd.read_csv('table_results_agg.csv', encoding='utf-8')
df = pd.DataFrame(data, columns=["symbol","stock_nm","stock_qty","stock_weight","stock_price","stock_change"])

# 데이터 정제 적용
df["stock_qty"] = df["stock_qty"].apply(clean_quantity)
df["stock_weight"]   = df["stock_weight"].apply(clean_weight)
df["stock_price"]    = df["stock_price"].apply(clean_price)

# ===== 5. 데이터 적재 (INSERT) =====
# 튜플 리스트로 변환 (순서: symbol, stock_name, quantity, weight, price, change_info)
records = df[["symbol", "stock_nm", "stock_qty", "stock_weight", "stock_price", "stock_change"]].values.tolist()

INSERT_SQL = """
INSERT INTO etf.etf_portfolio (symbol, stock_nm, stock_qty, stock_weight, stock_price, stock_change)
VALUES %s
"""

execute_values(cur, INSERT_SQL, records)
conn.commit()

print(f"✅ etf.etf_portfolio에 {len(records)}건 적재 완료!")

cur.close()
conn.close()

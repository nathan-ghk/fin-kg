'''
Python script to insert ETF info data into the database

Usage:
    python update_infoData.py --create_table
        Create table in the database
    python update_infoData.py --insert_data
        Insert data into the database
    python update_infoData.py --close
        Close the database connection

Example:
    python update_infoData.py --create_table
    python update_infoData.py --insert_data
    python update_infoData.py --close

Created by: Gyuhee Kim
Date: 2026-05-14
Email: nathan.gyuhee.kim@gmail.com
GitHub: https://github.com/nathan-ghk

'''

from math import log
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import os
import re
import logging
import argparse
import numpy as np

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class update_info:
    def __init__(self):
        ''' DB 연결 '''
        load_dotenv()
        self.conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "fk"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
        )
        try: 
            self.cur = self.conn.cursor()
            print('DEBUG : DB 연결 성공')
            logger.info('DEBUG : DB 연결 성공')
        except Exception as e:
            print(f'DEBUG : {e}')
            logger.error(f'DEBUG : {e}')
            return None

    def create_table(self):
        ''' Create table in the database '''
        self.cur.execute("""
            DROP TABLE IF EXISTS etf.etf_info;

            CREATE TABLE etf.etf_info (
                symbol       VARCHAR(10)   PRIMARY KEY,                  -- 종목코드 (ID)
                bm_index     VARCHAR(100),                               -- 벤치마크 지수
                lst_date     DATE,                                       -- 상장일
                am_company   VARCHAR(100),                               -- 자산운용사
                mkt_capital  BIGINT,                                -- 시가총액 (원문 유지)
                aum          BIGINT,                                -- 순자산총액 (원문 유지)
                leverage     BIGINT,                                -- 레버리지
                nav          NUMERIC(15, 2),                             -- 순자산가치
                dsc_rate     NUMERIC(7, 4),                              -- 괴리율(%)
                tot_expense  NUMERIC(7, 4),                              -- 총보수(%)
                trk_error    NUMERIC(7, 4),                              -- 추적오차(%)
                stt          VARCHAR(20),                                -- 증권거래세
                cgt          VARCHAR(100),                               -- 양도소득세
                dvt          VARCHAR(20),                                -- 배당소득세
                created_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
            );
            COMMENT ON TABLE  etf.etf_info             IS 'ETF Basic Information';
            COMMENT ON COLUMN etf.etf_info.symbol      IS 'ETF Symbol(ID)';
            COMMENT ON COLUMN etf.etf_info.bm_index    IS 'Benchmark Index';
            COMMENT ON COLUMN etf.etf_info.lst_date    IS 'Listing Date';
            COMMENT ON COLUMN etf.etf_info.am_company  IS 'Asset Manager';
            COMMENT ON COLUMN etf.etf_info.mkt_capital IS 'Market Capitalization';
            COMMENT ON COLUMN etf.etf_info.aum         IS 'Total Assets Under Management';
            COMMENT ON COLUMN etf.etf_info.leverage    IS 'Leverage';
            COMMENT ON COLUMN etf.etf_info.nav         IS 'Net Asset Value';
            COMMENT ON COLUMN etf.etf_info.dsc_rate    IS 'Deviation Rate(%)';
            COMMENT ON COLUMN etf.etf_info.tot_expense IS 'Total Expense Ratio(%)';
            COMMENT ON COLUMN etf.etf_info.trk_error   IS 'Tracking Error(%)';
            COMMENT ON COLUMN etf.etf_info.stt         IS 'Securities Transaction Tax';
            COMMENT ON COLUMN etf.etf_info.cgt         IS 'Capital Gains Tax';
            COMMENT ON COLUMN etf.etf_info.dvt         IS 'Dividend Tax';
        """)
        try:
            self.conn.commit()
            print('DEBUG : Create table completed')
            logger.info('DEBUG : Create table completed')
        except Exception as e:
            print(f'DEBUG : {e}')
            logger.error(f'DEBUG : {e}')
            return None

    def parse_date(self, s):
        """'2002. 10. 14.' → '2002-10-14'"""
        if pd.isna(s) or s in ("-", ""):
            return None
        s = re.sub(r"[.\s]", "", str(s))   # 점/공백 제거 → '20021014'
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"

    def parse_percent(self, s):
        """'-0.04%' → -0.04"""
        if pd.isna(s) or s in ("-", ""):
            return None
        return float(str(s).replace("%", "").replace(",", "").strip())

    def parse_number(self, s):
        """'121,854' → 121854.0"""
        if pd.isna(s) or s in ("-", ""):
            return None
        return float(str(s).replace(",", "").strip())

    def clean_numwithletter(self,s):
        """'25조 9,940억' → 25994000000000"""
        if pd.isna(s) or s in ("-", ""):
            return None
        return int(str(s).replace(",", "").replace("조", "").replace("억", "").replace(" ", "").replace("배","").strip())

    def clean_str(self, s):
        if pd.isna(s):
            return None
        return str(s).strip()

    def read_csv(self):
        ''' Read data from the csv file '''
        if os.path.exists('results_agg.csv'):
            df = pd.read_csv('results_agg.csv', encoding='utf-8')
            print(f'DEBUG : Data read completed : {df.shape[0]} rows')
            logger.info(f'DEBUG : Data read completed : {df.shape[0]} rows')
            return df
        else:
            print('DEBUG : results_agg.csv file does not exist')
            logger.error('DEBUG : results_agg.csv file does not exist')
            return None
    
    def process_df(self, df):
        ''' Process data '''
        try:
            df["lst_date"]    = df["lst_date"].apply(self.parse_date)
            df["nav"]         = df["nav"].apply(self.parse_number)
            df["dsc_rate"]    = df["dsc_rate"].apply(self.parse_percent)
            df["tot_expense"] = df["tot_expense"].apply(self.parse_percent)
            df["trk_error"]   = df["trk_error"].apply(self.parse_percent)
            df["mkt_capital"] = df["mkt_capital"].apply(self.clean_numwithletter)
            df["aum"]         = df["aum"].apply(self.clean_numwithletter)
            df["leverage"]    = df["leverage"].apply(self.clean_numwithletter)
            for col in ["symbol", "bm_index", "am_company", "mkt_capital", "aum",
                        "leverage", "stt", "cgt", "dvt"]:
                df[col] = df[col].apply(self.clean_str)
            print(f'DEBUG : Process data completed : {df.shape[0]} rows')
            logger.info(f'DEBUG : Process data completed : {df.shape[0]} rows')
            return df
        except Exception as e:
            print(f'DEBUG : Process data failed: {e}')
            logger.error(f'DEBUG : Process data failed: {e}')
            return None

    def insert_data(self, df):
        ''' Insert data into the database '''
        try:
            # data processing: convert symbol to 6 digits string (e.g., 69500 -> '069500')
            df['symbol'] = df['symbol'].astype(str).str.zfill(6)

            # define columns to insert
            columns = ["symbol", "bm_index", "lst_date", "am_company", "mkt_capital", "aum",
                        "leverage", "nav", "dsc_rate", "tot_expense", "trk_error",
                        "stt", "cgt", "dvt"]
            data_values = [tuple(x) for x in df[columns].to_numpy()]

            # execute_values for efficient Bulk Insert
            query = f"""
                INSERT INTO etf.etf_info ({", ".join(columns)}) VALUES %s
            """

            execute_values(self.cur, query, data_values)
            self.conn.commit()

            msg = f'Data insertion completed : {len(df)} rows'
            print(f'DEBUG : {msg}')
            logger.info(msg)
        except Exception as e:
            self.conn.rollback()
            error_msg = f'DEBUG : Data insertion failed: {e}'
            print(f'DEBUG : {error_msg}')
            logger.error(error_msg)
            return None

    def close(self):
        ''' Close the database connection '''
        try:
            self.cur.close()
            self.conn.close()
            print('DEBUG : Database connection closed')
            logger.info('DEBUG : Database connection closed')
        except Exception as e:
            print(f'DEBUG : {e}')
            logger.error(f'DEBUG : Database connection closed failed: {e}')
            return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--create_table', action='store_true', help='Create table in the database')
    parser.add_argument('--insert_data', action='store_true', help='Insert data into the database')
    parser.add_argument('--close', action='store_true', help='Close the database connection')
    args = parser.parse_args()

    update_info = update_info()
    if args.create_table:
        update_info.create_table()
    if args.insert_data:
        df = update_info.read_csv()
        if df is not None:
            df = update_info.process_df(df)
            update_info.insert_data(df)
    if args.close:
        update_info.close()
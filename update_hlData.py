'''
Python script to insert ETF portfolio data into the database

Usage:
    python update_data.py --create_table
        Create table in the database
    python update_data.py --insert_data
        Insert data into the database
    python update_data.py --close
        Close the database connection

Example:
    python update_data.py --create_table
    python update_data.py --insert_data
    python update_data.py --close

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

class update_holdings:
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
            CREATE TABLE IF NOT EXISTS etf.etf_holdings (
                id           SERIAL PRIMARY KEY,
                symbol       VARCHAR(10),                 -- ETF 종목코드 (FK 역할)
                stock_nm   VARCHAR(100),                -- 구성 종목명
                stock_qty     BIGINT,                      -- 주식수
                stock_weight       NUMERIC(7, 4),               -- 비중 (%)
                stock_price        BIGINT,                      -- 시세 (현재가)
                stock_change_amt   NUMERIC(10, 2),                -- 전일대비 (상승/하락 정보)
                stock_change_pct       NUMERIC(7, 4),               -- 전일대비 (%)
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_holdings_symbol ON etf.etf_holdings(symbol);
            COMMENT ON TABLE etf.etf_holdings IS 'ETF 보유 종목 상세 내역 (PDF)';
            COMMENT ON COLUMN etf.etf_holdings.symbol IS 'ETF Symbol(FK)';
            COMMENT ON COLUMN etf.etf_holdings.stock_nm IS 'Stock Name';
            COMMENT ON COLUMN etf.etf_holdings.stock_qty IS 'Stock Quantity';
            COMMENT ON COLUMN etf.etf_holdings.stock_weight IS 'Stock Weight(%)';
            COMMENT ON COLUMN etf.etf_holdings.stock_price IS 'Stock Price(KRW)';
            COMMENT ON COLUMN etf.etf_holdings.stock_change_amt IS 'Stock Change Amount(KRW)';
            COMMENT ON COLUMN etf.etf_holdings.stock_change_pct IS 'Stock Change Percentage(%)';
            COMMENT ON COLUMN etf.etf_holdings.created_at IS 'Created At';
        """)
        try:
            self.conn.commit()
            print('DEBUG : Create table completed')
            logger.info('DEBUG : Create table completed')
        except Exception as e:
            print(f'DEBUG : {e}')
            logger.error(f'DEBUG : {e}')
            return None

    def read_csv(self):
        ''' Read data from the csv file '''
        if os.path.exists('table_results_agg.csv'):
            df = pd.read_csv('table_results_agg.csv', encoding='utf-8')
            print(f'DEBUG : Data read completed : {df.shape[0]} rows')
            logger.info(f'DEBUG : Data read completed : {df.shape[0]} rows')
            return df
        else:
            print('DEBUG : table_results_agg.csv file does not exist')
            logger.error('DEBUG : table_results_agg.csv file does not exist')
            return None

    def clean_quantity(self, s):
        """ '7,022 주' -> 7022 """
        if pd.isna(s): return 0
        return int(re.sub(r"[^0-9]", "", str(s)))

    def clean_weight(self, s):
        """ '32.90 %' -> 32.90 """
        if pd.isna(s): return 0.0
        return float(str(s).replace("%", "").replace(",", "").strip())

    def clean_price(self, s):
        """ '287,250' -> 287250 """
        if pd.isna(s): return 0
        return int(re.sub(r"[^0-9]", "", str(s)))

    def convert_value(self, text, type="amt"):
        """Convert text to number"""
        # 1. Handle NaN or Non-string values safely
        if pd.isna(text) or not isinstance(text, str):
            return np.nan

        # 2. Check if the direction means negative
        is_down = "하락" in text

        # 3. Clean string by removing commas for easier number parsing
        clean_text = text.replace(",", "")

        if type == "amt":
            # Extract the first numerical value (e.g., '36000' or '3.69' or '0')
            match = re.search(r"\d+(?:\.\d+)?", clean_text)
            if not match:
                return 0.0

            number = float(match.group())
            return -number if is_down else number

        elif type == "pct":
            # Extract the numerical value inside the parentheses (e.g., '-2.74' or '0.00')
            # Looks for any digits/decimals preceded by '(' or '+' or '-' inside brackets
            match = re.search(r"\(([-+]?\d+(?:\.\d+)?)\s*%\)", clean_text)

            # Fallback regex if parentheses lack spaces or formatting varies (e.g., '0(0.00%)')
            if not match:
                match = re.search(r"([-+]?\d+(?:\.\d+)?)\s*%\)?", clean_text)

            if not match:
                return 0.0

            number = float(match.groups()[0])

            # Apply negative logic if text says '하락' but the inner percentage lacks a '-' sign
            if is_down and number > 0:
                return -number
            return number

        return np.nan

    def clean_change_amt(self, s):
        """ '상승 1,750' -> 1750 """
        if pd.isna(s): return None
        return self.convert_value(s, type="amt")

    def clean_change_pct(self, s):
        """ '상승 0.61%' -> 0.61 """
        if pd.isna(s): return None
        return self.convert_value(s, type="pct")

    def process_df(self, df):
        ''' Clean data '''
        try:
            df["stock_qty"]        = df["stock_qty"].apply(self.clean_quantity)
            df["stock_weight"]     = df["stock_weight"].apply(self.clean_weight)
            df["stock_price"]      = df["stock_price"].apply(self.clean_price)
            df["stock_change_amt"] = df["stock_change"].apply(self.clean_change_amt)
            df["stock_change_pct"] = df["stock_change"].apply(self.clean_change_pct)
            return df
        except Exception as e:
            print(f'DEBUG : {e}')
            logger.error(f'DEBUG : {e}')
            return None


    def insert_data(self, df):
        ''' Insert data into the database '''
        try:
            # data processing: convert symbol to 6 digits string (e.g., 69500 -> '069500')
            # project requirement: '069500' format
            df['symbol'] = df['symbol'].astype(str).str.zfill(6)

            # define columns to insert
            columns = ["symbol", "stock_nm", "stock_qty", "stock_weight",
                    "stock_price", "stock_change_amt", "stock_change_pct"]
            data_values = [tuple(x) for x in df[columns].to_numpy()]

            # execute_values for efficient Bulk Insert
            query = f"""
                INSERT INTO etf.etf_holdings ({", ".join(columns)})
                VALUES %s
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
        try:
            self.cur.close()
            self.conn.close()          
            print('DEBUG : Database connection closed')
            logger.info('DEBUG : Database connection closed')
        except Exception as e:
            print(f'DEBUG : {e}')
            logger.error(f'DEBUG : {e}')
            return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--create_table', action='store_true', help='Create table in the database')
    parser.add_argument('--insert_data', action='store_true', help='Insert data into the database')
    parser.add_argument('--close', action='store_true', help='Close the database connection')
    args = parser.parse_args()

    update_holdings = update_holdings()
    if args.create_table:   
        update_holdings.create_table()
    if args.insert_data:
        df = update_holdings.read_csv()
        if df is not None:
            df = update_holdings.process_df(df)
            update_holdings.insert_data(df)
    if args.close:
        update_holdings.close()


'''
Python script to collect ETF data from FDR

Usage:
    python cellect_fdr.py --create_table
        Create table in the database
    python cellect_fdr.py --insert_data
        Insert data into the database
    python cellect_fdr.py --close
        Close the database connection

Example:
    python cellect_fdr.py --create_table
    python cellect_fdr.py --insert_data
    python cellect_fdr.py --close

Created by: Gyuhee Kim
Date: 2026-05-14
Email: nathan.gyuhee.kim@gmail.com
'''
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import os
import re
import logging
import argparse
import FinanceDataReader as fdr

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class collect_fdr:
    def __init__(self):
        ''' DB Connection '''
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
            print('DEBUG : DB Connection Success')
            logger.info('DEBUG : DB Connection Success')
        except Exception as e:
            print(f'DEBUG : DB Connection Failed: {e}')
            logger.error(f'DEBUG : DB Connection Failed: {e}')
            return None
        
    def create_table(self):
        ''' Create table in the database '''
        self.cur.execute("""
            DROP TABLE IF EXISTS etf.fdr;

            CREATE TABLE etf.fdr (
            symbol             VARCHAR(10) PRIMARY KEY,
            category         INT, -- 1: ETF, 2: Index, 3: Stock, 4: Bond, 5: Real Estate, 6: Commodity, 7: Currency, 8: Other
            name               VARCHAR(100),   -- ETF 이름
            price            BIGINT,              -- ETF 현재가
            risefall           VARCHAR(10),    -- ETF 전일대비
            change           BIGINT,              -- ETF 전일대비 금액
            changerate     FLOAT,              -- ETF 전일대비 등락률
            nav            FLOAT,              -- ETF 순자산가치
            earningrate    FLOAT,              -- ETF 수익률
            volume           BIGINT,              -- ETF 거래량
            amount           BIGINT,              -- ETF 거래대금
            marcap           BIGINT               -- ETF 시가총액
            );
            COMMENT ON TABLE etf.fdr IS 'ETF Financial Data';
            COMMENT ON COLUMN etf.fdr.symbol IS 'ETF Symbol';
            COMMENT ON COLUMN etf.fdr.category IS 'ETF Category';
            COMMENT ON COLUMN etf.fdr.name IS 'ETF Name';
            COMMENT ON COLUMN etf.fdr.price IS 'ETF Price';
            COMMENT ON COLUMN etf.fdr.risefall IS 'ETF RiseFall';
            COMMENT ON COLUMN etf.fdr.change IS 'ETF Change';
            COMMENT ON COLUMN etf.fdr.changerate IS 'ETF ChangeRate';
            COMMENT ON COLUMN etf.fdr.nav IS 'ETF NAV';
            COMMENT ON COLUMN etf.fdr.earningrate IS 'ETF EarningRate';
            COMMENT ON COLUMN etf.fdr.volume IS 'ETF Volume';
            COMMENT ON COLUMN etf.fdr.amount IS 'ETF Amount';
            COMMENT ON COLUMN etf.fdr.marcap IS 'ETF MarCap';
        """)

        try:
            self.conn.commit()
            print('DEBUG : Table created successfully')
            logger.info('DEBUG : Table created successfully')
        except Exception as e:
            print(f'DEBUG : {e}')
            logger.error(f'DEBUG : {e}')
            return None


    def read_fdrData(self):
        ''' Read data from the database '''
        try:
            df = fdr.StockListing('ETF/KR')
            df.columns = df.columns.str.lower()

            print(f'DEBUG : Data read completed : {df.shape[0]} rows')
            logger.info(f'DEBUG : Data read completed : {df.shape[0]} rows')
            return df
        except Exception as e:
            print(f'DEBUG : Data read failed: {e}')
            logger.error(f'DEBUG : Data read failed: {e}')
            return None
    
    def insert_data(self, df):
        ''' Insert data into the database '''
        try:
            # data processing: convert symbol to 6 digits string (e.g., 69500 -> '069500')
            # df['symbol'] = df['symbol'].astype(str).str.zfill(6)
            # define columns to insert
            columns = ["symbol", "category", "name", "price", "risefall", "change", "changerate", "nav", "earningrate", "volume", "amount", "marcap"]
            data_values = [tuple(x) for x in df[columns].to_numpy()]
             # execute_values for efficient Bulk Insert
            query = f"""
                INSERT INTO etf.fdr ({", ".join(columns)}) VALUES %s
            """
            execute_values(self.cur, query, data_values)
            self.conn.commit()
            print(f'DEBUG : Data insertion completed : {len(df)} rows')
            logger.info(f'DEBUG : Data insertion completed : {len(df)} rows')
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

    collect_fdr = collect_fdr()
    if args.create_table:
        collect_fdr.create_table()
    if args.insert_data:
        df = collect_fdr.read_fdrData()
        if df is not None:
            collect_fdr.insert_data(df)
    if args.close:
        collect_fdr.close()
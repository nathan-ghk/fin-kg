import os
from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine
from dotenv import load_dotenv
load_dotenv(override=True, encoding='utf-8')

# DB 환경 설정 
# DB_USER = "ghk" #"user"
# DB_PASS = "ghk42" # "password"
# DB_HOST = "localhost" # "172.26.229.112" # "localhost"
# DB_PORT = "5432"
# DB_NAME = "ghk_poc_db" # "mydatabase"

# def get_db_connection():
#     pg_uri = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
#     engine = create_engine(pg_uri)
#     # LangChain이 이해할 수 있는 SQLDatabase 객체로 반환
#     return SQLDatabase(engine)

def get_db_connection():
    DB_USER = os.getenv('DB_USER') #"ghk" #"user"
    DB_PASS = os.getenv('DB_PASSWORD') # "ghk42" # "password"
    DB_HOST = "localhost" # "172.26.229.112" # "localhost"
    DB_PORT = os.getenv('DB_PORT') # "5432"
    DB_NAME = os.getenv('DB_NAME') # "ghk_poc_db" # "mydatabase"

    pg_uri = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(pg_uri)
    # LangChain이 이해할 수 있는 SQLDatabase 객체로 반환
    return SQLDatabase(engine, 
                        schema = "etf",
                        sample_rows_in_table_info = 3,
                        include_tables=["etf_info", "etf_holdings", "fdr"])
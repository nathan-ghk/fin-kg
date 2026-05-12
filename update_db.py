import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def upload_dataframe_to_postgres(df, table_name):
    """
    .env의 환경 변수를 사용하여 DataFrame을 PostgreSQL에 업로드합니다.
    """
    try:
        # 1. 환경 변수 읽기
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        db_host = os.getenv('DB_HOST')
        db_port = os.getenv('DB_PORT')
        db_name = os.getenv('DB_NAME')

        # 2. Connection String 생성
        connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        # 3. SQLAlchemy 엔진 생성
        engine = create_engine(connection_string)

        # 4. 데이터 업로드
        # index=False는 데이터프레임의 인덱스를 별도 컬럼으로 저장하지 않겠다는 의미입니다.
        df.to_sql(table_name, engine, if_exists='replace', index=False)

        print(f"✅ Successfully uploaded data to '{db_name}.public.{table_name}'")

    except Exception as e:
        print(f"❌ Error occurred: {e}")

if __name__ == "__main__":
    # 샘플 데이터 생성
    data = {
        'agent_id': ['CD_INS_01', 'CD_INS_02'],
        'status': ['active', 'idle'],
        'last_run': ['2026-05-12', '2026-05-11']
    }
    sample_df = pd.DataFrame(data)

    # 함수 실행 (테이블명 예시: tn_ito_agent_status)
    upload_dataframe_to_postgres(sample_df, 'tn_ito_agent_status')

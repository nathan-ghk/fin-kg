from dotenv import load_dotenv
import os
import requests
import pandas as pd
import time
import logging
from typing import List, Dict, Optional, overload

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


load_dotenv()
api_key = os.getenv("DATA_GO_KR_API_KEY_D")

if api_key:
    print(api_key[0:10])
else:
    print("API 키가 없습니다.")

class FundDataCollector:
    """
    공공데이터포털 API를 통해 국내 펀드 정보를 수집하는 클래스
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://apis.data.go.kr/1160100/service/GetFundProductInfoService"
        self.headers = {'Content-Type': 'application/json'}

    def fetch_fund_data(self, page_no: int = 1, num_of_rows: int = 100) -> Optional[List[Dict]]:
        """
        특정 페이지의 펀드 정보를 가져옵니다.
        """
        endpoint = f"{self.base_url}/getStandardCodeInfo"
        params = {
            'serviceKey': self.api_key,
            'resultType': 'json',
            'pageNo': page_no,
            'numOfRows': num_of_rows
        }

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()  # 200 OK가 아니면 예외 발생

            data = response.json()

            # API 응답 구조 확인 (공공데이터포털 표준에 따름)
            items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
            return items

        except requests.exceptions.RequestException as e:
            logging.error(f"API 호출 중 오류 발생 (Page {page_no}): {e}")
            return None
        except Exception as e:
            logging.error(f"데이터 파싱 중 오류 발생: {e}")
            return None

    def collect_all_funds(self, max_pages: int = 10, rows_per_page: int = 100) -> pd.DataFrame:
        """
        여러 페이지에 걸쳐 펀드 데이터를 수집하여 DataFrame으로 반환합니다.
        """
        all_funds = []

        for page in range(1, max_pages + 1):
            logging.info(f"데이터 수집 중... (페이지: {page}/{max_pages})")

            items = self.fetch_fund_data(page_no=page, num_of_rows=rows_per_page)

            if not items:
                logging.info("더 이상 가져올 데이터가 없거나 오류가 발생했습니다.")
                break

            all_funds.extend(items)

            # API 과부하 방지를 위한 Rate Limiting (0.5초 대기)
            time.sleep(0.5)

        # 수집된 데이터를 데이터프레임으로 변환
        df = pd.DataFrame(all_funds)

        # 컬럼명 매핑 (한글명/영문명 정리)
        # fndNm: 펀드명, fndStdCd: 표준코드, amcNm: 운용사, setAmt: 설정액 등
        logging.info(f"수집 완료: 총 {len(df)}건의 노드 데이터 확보")
        return df

# --- 실행부 ---
if __name__ == "__main__":
    # TODO: 발급받은 일반 인증서(Encoding/Decoding 중 하나)를 입력하세요.
    MY_API_KEY = api_key

    collector = FundDataCollector(api_key=MY_API_KEY)

    # 테스트를 위해 5페이지(약 500건)만 수집
    fund_df = collector.collect_all_funds(max_pages=5, rows_per_page=100)

    if not fund_df.empty:
        print(fund_df[['basDt','srtnCd', 'fndNm',  'ctg', 'setpDt', 'fndTp', 'prdClsfCd', 'asoStdCd']].head())
        # 임시 저장
        fund_df.to_csv("raw_fund_data.csv", index=False, encoding='utf-8-sig')
    else:
        print("수집된 데이터가 없습니다. API 키나 네트워크 상태를 확인하세요.")

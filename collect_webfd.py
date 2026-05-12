from re import S
import pandas as pd
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from subprocess import CREATE_NO_WINDOW
from webdriver_manager.core.os_manager import OperationSystemManager,ChromeType
from cellect_etf import masterETF

def scraper(base_url: str, symbol: str):
    br_ver = OperationSystemManager().get_browser_version_from_os(ChromeType.GOOGLE)
    version_main=int(br_ver.split('.')[0])
    'Dirver Setting'

    option = Options()
    option.add_argument('--disable-gpu')
    option.add_argument('--window-size=1920x1080')
    option.add_argument('--start-maximized')
    option.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36')
    service = Service()
    service.creation_flags = CREATE_NO_WINDOW

    # driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver = uc.Chrome(service=service, options=option, version_main=version_main)
    driver.implicitly_wait(3) # 화명 렌더링을 3초간 기다림
    url = base_url + symbol + '/info/summary' # 'https://stock.naver.com/domestic/stock/069500/info/summary'
    driver.get(url)

    try:

        'Scrapping'
        results = []
        li_elements = driver.find_elements(By.XPATH, '//ul[@class="StockInfo_listing-info__qzcRk"]/li')

        for li in li_elements:
            # print(li)
            spans = li.find_elements(By.TAG_NAME, "span")
            data = [span.text for span in spans if span.text.strip() != ""]
            if data:
                item = {
                    "지표": data[0],
                    "값": data[1] if len(data) > 1 else 'N/A'
                }
                results.append(item) # 리스트에 추가    

        
        table_results = []
        all_tables = driver.find_elements(By.CSS_SELECTOR, "table.InnerTable_table___xmXR")
        seen_names = set()  
        if len(all_tables) >= 2:
            target_table = all_tables[0] 
            rows = target_table.find_elements(By.CSS_SELECTOR, "tbody.InnerTable_tbody__zuUyv tr")
            
            row_num = 0
            for row in rows:
                if row_num <= 10:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    print([cell.text for cell in cells])
                    # raw_data = [cell.text for cell in cells]
                    row_data = [cell.text.replace('\n', ' ').strip() for cell in cells]
                    stock_name = row_data[0]
                    if stock_name not in seen_names:

                        item = {
                            "종목명": row_data[0],
                            "주식수": row_data[1],
                            "비중중": row_data[2],
                            "시세": row_data[3] if len(row_data) > 3 else 'N/A',
                            "전일대비": row_data[4] if len(row_data) > 4 else 'N/A'
                        }
                        table_results.append(item)
                        seen_names.add(stock_name)

                    row_num += 1

        driver.quit()
        return results, table_results
    except Exception as e:
        print(e)
        return None, None
    finally:
        driver.quit()

def dict_to_df(results_agg: dict):
    # 1. set up a list to store data in a dictionary of {indicator: value}
    all_rows = []
    for code, data_list in results_agg.items():
        # convert to a dictionary of {indicator: value}
        row_dict = {item['지표']: item['값'] for item in data_list}
        row_dict['symbol'] = code
        all_rows.append(row_dict)

    # 2. convert to a dataframe
    df = pd.DataFrame(all_rows)

    # 3. move symbol column to the first column
    if 'symbol' in df.columns:
        cols = ['symbol'] + [c for c in df.columns if c != 'symbol']
        df = df[cols]

    # 4. redefine columns
    df.columns = ['symbol'
                ,'bm_index' # benchmark index   
                ,'lst_date' # listing date
                ,'am_company'  # asset management company
                ,'mkt_capital' # market capitalization
                ,'aum'  # Leveraged Assets Under Management 
                ,'leverage' # leverage
                ,'nav' # Net Asset Value
                ,'dsc_rate' # Discrepancy Rate
                ,'tot_expense' # Total Expense Ratio
                ,'trk_error' # Tracking Error
                ,'stt' # Securities Transaction Tax (STT)
                ,'cgt' # Capital gains tax
                ,'dvt' # Dividend Tax
                ]

    return df

def dictli_to_df(table_results_agg: dict):
    # 1. set up a dict to store data in a data frame
    df = pd.DataFrame()
    # 2. convert to a dataframe
    for code, data_list in table_results_agg.items():
        _df = pd.DataFrame(data_list)
        _df['symbol'] = code
        df = pd.concat([df, _df])
    # 3. redefine columns
    df.columns = ['stock_nm', 'stock_qty', 'stock_weight', 'stock_price', 'stock_change', 'symbol']
    # 4. move symbol column to the first column
    if 'symbol' in df.columns:
        cols = ['symbol'] + [c for c in df.columns if c != 'symbol']
        df = df[cols]    
    return df


if __name__ == "__main__":
    base_url = 'https://stock.naver.com/domestic/stock/'
    etf_master = masterETF()
    symbols = etf_master.df_etf.Symbol.tolist()[:10]
    print(symbols)

    results_agg = dict()
    table_results_agg = dict()

    try: 
        for symbol in symbols:
            print(symbol)
            results, table_results = scraper(base_url, symbol)
            results_agg[symbol] = results
            table_results_agg[symbol] = table_results
    except:
        pass

    print('DEBUG : Complteted to collect data')

    df = dict_to_df(results_agg)
    df.to_csv('results_agg.csv', encoding='utf-8', index=False)
    print(f'DEBUG : {len(df)} rows in results_agg.csv')
    tbl = dictli_to_df(table_results_agg)
    print(f'DEBUG : {len(tbl)} rows in table_results_agg.csv')
    tbl.to_csv('table_results_agg.csv', encoding='utf-8', index=False)
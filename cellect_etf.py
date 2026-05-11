import FinanceDataReader as fdr
# 한국거래소 상장 종목 전체 리스트 (ETF 포함)
# df_krx = fdr.StockListing('KRX')

class masterETF:
    def __init__(self):
        self.df_etf = fdr.StockListing('ETF/KR')

    def write_etf(self):
        self.df_etf.to_csv('etf.csv', index=False)
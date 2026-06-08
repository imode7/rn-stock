import FinanceDataReader as fdr

df = fdr.DataReader('005930', '2024-01-01')
print(df.tail())
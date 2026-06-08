import FinanceDataReader as fdr

def check_columns():
    # 1. 시세 데이터 컬럼 확인
    df_krx = fdr.StockListing('KRX')
    print("\n--- [KRX] 시세 데이터 컬럼 리스트 ---")
    print(df_krx.columns.tolist())
    print("상단 3개 데이터 예시:")
    print(df_krx.head(3))

    # 2. 상세 데이터 컬럼 확인
    # 여기서 우리가 원하는 '진짜 산업군'이 어디에 들어있는지 찾아야 합니다.
    df_desc = fdr.StockListing('KRX-DESC')
    print("\n--- [KRX-DESC] 상세 데이터 컬럼 리스트 ---")
    print(df_desc.columns.tolist())
    print("상단 3개 데이터 예시:")
    print(df_desc.head(3))

# 실행
check_columns()
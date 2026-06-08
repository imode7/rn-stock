import FinanceDataReader as fdr
import pandas as pd
import numpy as np


def get_rn_zone_proximity():
    # 1. 이전 단계에서 만든 3,000억 이상 종목 리스트 가져오기
    # (여기서는 함수 내에서 다시 호출하여 데이터를 생성합니다)
    df_base = fdr.StockListing('KRX')
    df_desc = fdr.StockListing('KRX-DESC')

    df_base['Code'] = df_base['Code'].astype(str).str.zfill(6)
    df_desc['Code'] = df_desc['Code'].astype(str).str.zfill(6)

    df_merged = pd.merge(df_base, df_desc[['Code', 'Sector', 'Industry']], on='Code', how='left')
    df_merged['Final_Sector'] = df_merged['Sector'].fillna(df_merged['Industry']).fillna('기타')

    # 필터링: 3,000억 이상 & 제외 키워드
    exclude_keywords = ['ETF', 'ETN', '스팩', '제', '펀드', '홀딩스']
    df_filtered = df_merged[(df_merged['Marcap'] >= 300_000_000_000) &
                            (~df_merged['Name'].str.contains('|'.join(exclude_keywords)))].copy()

    # 2. 라운드 피겨(RN) 계산 함수 정의
    def calculate_rn(price):
        # 주가 범위에 따른 라운드 피겨 단위 설정
        if price >= 100000:
            unit = 10000
        elif price >= 10000:
            unit = 1000
        elif price >= 1000:
            unit = 100
        else:
            unit = 10

        # 현재가보다 위/아래에 있는 가장 가까운 라운드 피겨 찾기
        lower_rn = (price // unit) * unit
        upper_rn = lower_rn + unit

        # 더 가까운 쪽 선택
        target_rn = upper_rn if (upper_rn - price) < (price - lower_rn) else lower_rn
        return target_rn

    # 3. 실시간 근접도 계산
    print("현재가 및 RN존 계산 중...")
    df_filtered['Close'] = pd.to_numeric(df_filtered['Close'], errors='coerce')
    df_filtered = df_filtered.dropna(subset=['Close'])

    df_filtered['Target_RN'] = df_filtered['Close'].apply(calculate_rn)
    # RN존까지의 거리(%) 계산
    df_filtered['Distance_pct'] = (
                (df_filtered['Target_RN'] - df_filtered['Close']) / df_filtered['Close'] * 100).round(2)

    # 4. 업종별 1위 종목만 추출 (1업종 1종목 원칙)
    df_top_by_sector = df_filtered.sort_values(by=['Final_Sector', 'Marcap'], ascending=[True, False]).groupby(
        'Final_Sector').head(1)

    # 5. RN존에 매우 근접한 종목 정렬
    # 절대값을 기준으로 정렬하기 위해 임시 컬럼('abs_dist')을 만든 뒤 정렬합니다.
    df_top_by_sector['abs_dist'] = df_top_by_sector['Distance_pct'].abs()

    # abs_dist(절대 거리)가 작은 순서대로 정렬 (즉, RN존에 가장 가까운 순서)
    df_result = df_top_by_sector.sort_values(by='abs_dist', ascending=True)

    # 6. 결과 정리 (임시 컬럼은 제외하고 추출)
    final_result = df_result[['Code', 'Name', 'Final_Sector', 'Close', 'Target_RN', 'Distance_pct']]

    print("\n--- [RN존 근접 업종 대장주 TOP 10] ---")
    print(final_result.head(10))

    final_result.to_excel("RN_Zone_Analysis.xlsx", index=False)
    return final_result


# 실행
get_rn_zone_proximity()
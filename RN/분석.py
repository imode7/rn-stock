import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta


def get_rn_expanded_targets():
    print("시장 전체 종목 분석 중... (시총 3,000억 이상 대상)")

    # 1. KRX 전체 종목 리스트 불러오기
    df_krx = fdr.StockListing('KRX')

    # [수정] 대소문자 구분 없이 시가총액 컬럼 매칭 (보내주신 목록의 'Marcap' 대응)
    mcap_col = None
    # 사용자가 보내준 인덱스 목록에 'Marcap'이 있으므로 이를 우선 확인
    for col in ['Marcap', 'MarCap', 'MarketCap', '시가총액']:
        if col in df_krx.columns:
            mcap_col = col
            break

    if not mcap_col:
        print("에러: 시가총액 컬럼을 찾을 수 없습니다. 현재 컬럼:", df_krx.columns)
        return pd.DataFrame()

    # 2. 데이터 정제
    df_krx[mcap_col] = pd.to_numeric(df_krx[mcap_col], errors='coerce')

    # 시가총액 3,000억 이상 필터링
    df_filtered = df_krx[df_krx[mcap_col] >= 300000000000].copy()

    # 분석 속도를 위해 시총 상위 400개만 정밀 분석
    df_filtered = df_filtered.sort_values(by=mcap_col, ascending=False).head(400)

    # RN 기준 가격 설정
    base_units = [1000, 1500, 2000, 3000, 5000, 7500]
    rn_levels = []
    for i in range(0, 7):  # 1,000원부터 1,000만원대까지 커버
        multiplier = 10 ** i
        rn_levels.extend([u * multiplier for u in base_units])
    rn_levels = sorted(list(set(rn_levels)))

    results = []
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d')

    for idx, row in df_filtered.iterrows():
        symbol = row['Code']
        name = row['Name']
        current_price = row['Close']
        m_cap = row[mcap_col]

        # RN존 설정 (상단선/매수선)
        upper_candidates = [level for level in rn_levels if level >= current_price]
        lower_candidates = [level for level in rn_levels if level < current_price]

        upper_rn = min(upper_candidates) if upper_candidates else None
        lower_rn = max(lower_candidates) if lower_candidates else None

        if upper_rn and lower_rn:
            distance_to_lower = (current_price - lower_rn) / lower_rn * 100

            # 매수선(RN존) 4% 이내 진입 여부
            if 0 <= distance_to_lower <= 4.0:
                try:
                    df_hist = fdr.DataReader(symbol, start_date, end_date)
                    if df_hist.empty: continue

                    highest_2m = df_hist['High'].max()

                    # [조건 1] 최근 2개월 내 상단선 터치 여부
                    is_upper_touched = highest_2m >= (upper_rn * 0.99)

                    # [조건 2] 시총 10조 미만은 최고 거래대금 1,500억 이상 기록 체크
                    # 10조 = 10,000,000,000,000
                    max_vol_val = (df_hist['Volume'] * df_hist['Close']).max()
                    is_heavy = True if m_cap >= 10e12 else (max_vol_val >= 150000000000)

                    if is_upper_touched and is_heavy:
                        results.append({
                            '종목명': name,
                            '시총(억)': int(m_cap / 100000000),
                            '현재가': f"{int(current_price):,}",
                            '상단선': f"{int(upper_rn):,}",
                            '매수선': f"{int(lower_rn):,}",
                            '거리': f"{distance_to_lower:.2f}%"
                        })
                except:
                    continue

    return pd.DataFrame(results)


if __name__ == "__main__":
    final_df = get_rn_expanded_targets()
    if not final_df.empty:
        print("\n" + "=" * 85)
        print("★ [RN존 최종 필터링] 상단 터치 완료 & 매수권 진입 종목 ★")
        print("=" * 85)
        print(final_df)
    else:
        print("\n[알림] 현재 기법 조건(상단 터치 + 매수선 4% 이내)에 맞는 종목이 없습니다.")
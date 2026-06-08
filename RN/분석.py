import json
import math
from datetime import datetime, timedelta
import pandas as pd
import requests
from bs4 import BeautifulSoup


def get_krx_market_top_400():
    """네이버 금융에서 시가총액 상위 400개 종목의 코드, 이름, 현재가, 시가총액을 크롤링합니다."""
    print("네이버 금융에서 시장 전체 종목 데이터 수집 중...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    stocks = []
    # 코스피(0), 코스닥(1)에서 상위 종목 수집 (각 4페이지씩 수집하여 충분한 풀 확보)
    for market_code in [0, 1]:
        for page in range(1, 5):
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={market_code}&page={page}"
            res = requests.get(url, headers=headers)
            soup = BeautifulSoup(res.text, 'html.parser')

            table = soup.find('table', {'class': 'type_2'})
            if not table:
                continue

            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 12:
                    continue

                # 종목명 및 코드 추출
                a_tag = cols[1].find('a')
                if not a_tag:
                    continue
                name = a_tag.text.strip()
                code = a_tag['href'].split('code=')[-1]

                # 현재가 및 시가총액 추출
                try:
                    current_price = int(cols[2].text.replace(',', '').strip())
                    # 네이버 시총은 '억' 단위이므로 원화로 환산
                    m_cap = int(cols[6].text.replace(',', '').strip()) * 100000000
                except ValueError:
                    continue

                stocks.append({
                    'Code': code,
                    'Name': name,
                    'Close': current_price,
                    'Marcap': m_cap
                })

    df = pd.DataFrame(stocks)
    if df.empty:
        return df

    # 중복 제거 및 시총 3,000억 이상 필터링 후 상위 400개 반환
    df = df.drop_duplicates(subset=['Code'])
    df = df[df['Marcap'] >= 300000000000]
    df = df.sort_values(by='Marcap', ascending=False).head(400)
    return df


def get_naver_historical_data(symbol, days=120):
    """네이버 일별시세 API(JSON식 차트 데이터)를 활용해 안정적으로 과거 시세를 가져옵니다."""
    url = f"https://fchart.stock.naver.com/sise.nhn?symbol={symbol}&timeframe=day&count={days}&requestType=0"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'xml')
    items = soup.find_all('item')

    hist_data = []
    for item in items:
        data_str = item.get('data')
        if not data_str:
            continue
        # 데이터 포맷: "날짜|시가|고가|저가|종가|거래량"
        tokens = data_str.split('|')
        if len(tokens) >= 6:
            hist_data.append({
                'Date': tokens[0],
                'High': int(tokens[2]),
                'Close': int(tokens[4]),
                'Volume': int(tokens[5])
            })

    return pd.DataFrame(hist_data)


def get_rn_expanded_targets():
    df_filtered = get_krx_market_top_400()
    if df_filtered.empty:
        print("에러: 시장 데이터를 수집하지 못했습니다.")
        return pd.DataFrame()

    print(f"시총 3,000억 이상 상위 {len(df_filtered)}개 종목 정밀 분석 시작...")

    # RN 기준 가격 설정
    base_units = [1000, 1500, 2000, 3000, 5000, 7500]
    rn_levels = []
    for i in range(0, 7):
        multiplier = 10 ** i
        rn_levels.extend([u * multiplier for u in base_units])
    rn_levels = sorted(list(set(rn_levels)))

    results = []

    for idx, row in df_filtered.iterrows():
        symbol = row['Code']
        name = row['Name']
        current_price = row['Close']
        m_cap = row['Marcap']

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
                    # 120일 치 일별 데이터 조회
                    df_hist = get_naver_historical_data(symbol, days=120)
                    if df_hist.empty:
                        continue

                    # 최근 2개월(대략 40영업일) 최고가 계산
                    df_2m = df_hist.tail(40)
                    highest_2m = df_2m['High'].max()

                    # [조건 1] 최근 2개월 내 상단선 터치 여부
                    is_upper_touched = highest_2m >= (upper_rn * 0.99)

                    # [조건 2] 시총 10조 미만은 최고 거래대금 1,500억 이상 체크
                    # 거래대금 = 거래량 * 종가
                    df_hist['VolVal'] = df_hist['Volume'] * df_hist['Close']
                    max_vol_val = df_hist['VolVal'].max()
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
                except Exception as e:
                    continue

    return pd.DataFrame(results)


if __name__ == "__main__":
    final_df = get_rn_expanded_targets()
    if not final_df.empty:
        print("\n" + "=" * 85)
        print("★ [RN존 최종 필터링] 상단 터치 완료 & 매수권 진입 종목 ★")
        print("=" * 85)
        print(final_df.to_string(index=False))
    else:
        print("\n[알림] 현재 기법 조건(상단 터치 + 매수선 4% 이내)에 맞는 종목이 없습니다.")
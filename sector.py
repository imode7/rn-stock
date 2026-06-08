import FinanceDataReader as fdr
import pandas as pd


def get_sector_stocks_above_300B():
    try:
        # 1. 시세 데이터 가져오기 (전체 시장)
        df_marcap = fdr.StockListing('KRX')

        # 2. 상세 데이터 가져오기 (산업 분류 Sector, Industry 정보 포함)
        df_desc = fdr.StockListing('KRX-DESC')

        # 3. 데이터 타입 및 컬럼명 통일 (종목코드 6자리 유지)
        df_marcap['Code'] = df_marcap['Code'].astype(str).str.zfill(6)
        df_desc['Code'] = df_desc['Code'].astype(str).str.zfill(6)

        # 4. 병합 (시세 데이터 기준, 업종 정보 추가)
        df_merged = pd.merge(df_marcap, df_desc[['Code', 'Sector', 'Industry']], on='Code', how='left')

        # 5. 제외 키워드 필터링 (ETF, ETN, 스팩 등 투자 부적합 종목 제거)
        exclude_keywords = ['ETF', 'ETN', '스팩', '제', '펀드', '홀딩스']
        df_filtered = df_merged[~df_merged['Name'].str.contains('|'.join(exclude_keywords))].copy()

        # 6. 시가총액 3,000억 원 이상 필터링
        # Marcap은 '원' 단위이므로 3,000억(300,000,000,000) 이상인 것만 추출
        df_filtered = df_filtered[df_filtered['Marcap'] >= 300_000_000_000]

        # 7. 섹터 명칭 정제
        # Sector가 비어있으면 Industry를 사용하고, 둘 다 없으면 '기타'로 표시
        df_filtered['Final_Sector'] = df_filtered['Sector'].fillna(df_filtered['Industry']).fillna('기타')

        # 8. 정렬 (섹터별 가나다순 -> 그 안에서 시가총액 높은 순)
        df_result = df_filtered.sort_values(by=['Final_Sector', 'Marcap'], ascending=[True, False])

        # 9. 단위 변환 (원 -> 억 원)
        df_result['Marcap(억)'] = (df_result['Marcap'] / 100_000_000).astype(int)

        # 10. 최종 결과 정리
        result = df_result[['Code', 'Name', 'Final_Sector', 'Marcap(억)']]

        # 11. 엑셀 저장
        file_name = "KOSPI_KOSDAQ_Above_300B.xlsx"
        result.to_excel(file_name, index=False)

        print(f"성공! '{file_name}' 파일이 생성되었습니다.")
        print(f"추출된 종목 수: {len(result)}개")
        print("\n--- [상위 5개 미리보기] ---")
        print(result.head(5))

        return result

    except Exception as e:
        print(f"오류 발생: {e}")
        return None


# 실행
get_sector_stocks_above_300B()
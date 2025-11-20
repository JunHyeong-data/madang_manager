import streamlit as st
import duckdb
import pandas as pd
import time

# 1. DB 연결
conn = duckdb.connect(database='madang.db', read_only=False)

st.title("마당 서점 관리 시스템 (DuckDB Ver.)")

# 2. 도서 목록 불러오기
try:
    books_df = conn.sql("SELECT bookid, bookname FROM Book").df()
    book_list = (books_df['bookid'].astype(str) + "," + books_df['bookname']).tolist()
    books = [None] + book_list
except Exception as e:
    books = [None]

tab1, tab2 = st.tabs(["고객조회", "거래 입력"])

# --- 탭 1: 고객 조회 및 로직 수정 ---
name = tab1.text_input("고객명")

if name:
    # [수정 1] 고객 존재 여부부터 먼저 확인 (주문 내역 없어도 됨)
    user_check_sql = f"SELECT * FROM Customer WHERE name = '{name}'"
    user_info = conn.sql(user_check_sql).df()

    if user_info.empty:
        tab1.warning("등록되지 않은 고객입니다.")
    else:
        # 고객 정보가 있으면 ID 확보
        custid = user_info.iloc[0]['custid']
        phone = user_info.iloc[0]['phone']

        # [수정 2] 주문 내역은 별도로 조회 (LEFT JOIN 효과)
        history_sql = f"""
            SELECT b.bookname, o.orderdate, o.saleprice 
            FROM Orders o
            JOIN Book b ON o.bookid = b.bookid
            WHERE o.custid = {custid}
            ORDER BY o.orderdate DESC
        """
        history_df = conn.sql(history_sql).df()
        
        if history_df.empty:
            tab1.info("구매 내역이 없는 신규 고객입니다.")
        else:
            tab1.write("구매 내역:")
            tab1.dataframe(history_df)

        # --- 탭 2: 거래 입력 (이제 신규 고객도 입력 가능) ---
        tab2.write(f"고객번호: {custid}")
        tab2.write(f"고객명: {name}")
        
        select_book = tab2.selectbox("구매 서적:", books)

        if select_book is not None:
            bookid = select_book.split(",")[0]
            dt = time.strftime('%Y-%m-%d', time.localtime())
            price = tab2.text_input("금액")

            if tab2.button('거래 입력'):
                max_order_df = conn.sql("SELECT COALESCE(MAX(orderid), 0) FROM Orders").fetchone()
                orderid = max_order_df[0] + 1
                
                insert_sql = f"""
                    INSERT INTO Orders (orderid, custid, bookid, saleprice, orderdate) 
                    VALUES ({orderid}, {custid}, {bookid}, {price}, '{dt}')
                """
                conn.sql(insert_sql)
                tab2.success(f'{name}님의 거래가 입력되었습니다!')
                
                # 입력 직후 내역 바로 갱신해서 보여주기
                st.rerun()
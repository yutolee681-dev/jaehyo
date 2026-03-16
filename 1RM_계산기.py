import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import time

st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="centered")

def get_ordinal(n):
    if 11 <= n % 100 <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

exercise_list = [
    "Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch",
    "Deadlift", "Back Squat", "Shoulder Press",
    "Thruster", "Bench Press", "Jerk", "Overhead Squat"
]

rename_map = {
    "Power Clean": "P.Clean",
    "Squat Clean": "S.Clean",
    "Power Snatch": "P.Snatch",
    "Squat Snatch": "S.Snatch",
    "Deadlift": "Dead",
    "Back Squat": "B.Squat",
    "Shoulder Press": "S.Press",
    "Thruster": "Thrust",
    "Bench Press": "Bench",
    "Jerk": "Jerk",
    "Overhead Squat": "OHS"
}

conn = st.connection("gsheets", type=GSheetsConnection)

def get_full_data():
    try:
        raw_df = conn.read(worksheet="Sheet1", ttl=0)

        if raw_df is None or raw_df.empty:
            return pd.DataFrame(columns=['name','exercise','weight','date','password','gender','memo'])

        required_cols = {'password': '0000', 'gender': '남성', 'memo': ''}

        for col, default in required_cols.items():
            if col not in raw_df.columns:
                raw_df[col] = default

        return raw_df

    except Exception as e:
        st.error(f"GSheets read error: {e}")
        return pd.DataFrame(columns=['name','exercise','weight','date','password','gender','memo'])


def get_comments():
    try:
        c_df = conn.read(worksheet="comments", ttl=0)

        if c_df is None:
            return pd.DataFrame(columns=['name','comment','date'])

        return c_df

    except Exception as e:
        st.error(f"GSheets comment error: {e}")
        return pd.DataFrame(columns=['name','comment','date'])


df = get_full_data()
comments_df = get_comments()

if 'is_auth' not in st.session_state:
    st.session_state.is_auth = False
    st.session_state.user_name = ""
    st.session_state.user_gender = "남성"

st.title("🏋️ 1RM을 기억해")

st.subheader("🏆 박스 실시간 랭킹 (전체)")

selected_rank_exercise = st.selectbox("랭킹 종목 선택", exercise_list, index=0)

rank_df = df[df['exercise'] == selected_rank_exercise].copy()
rank_df['weight'] = pd.to_numeric(rank_df['weight'], errors='coerce')

best_rank_df = rank_df.sort_values('weight', ascending=False).drop_duplicates('name')

if not best_rank_df.empty:

    m_data = best_rank_df[best_rank_df['gender'] == "남성"].sort_values('weight', ascending=False)
    f_data = best_rank_df[best_rank_df['gender'] == "여성"].sort_values('weight', ascending=False)

    max_rows = max(len(m_data), len(f_data))

    for i in range(max_rows):

        col1, col2 = st.columns(2)

        with col1:
            if i < len(m_data):
                row = m_data.iloc[i]
                st.write(f"{get_ordinal(i+1)} {row['name']} {row['weight']}")

        with col2:
            if i < len(f_data):
                row = f_data.iloc[i]
                st.write(f"{get_ordinal(i+1)} {row['name']} {row['weight']}")

st.divider()

st.subheader("💬 실시간 응원 한마디")

if st.session_state.is_auth:

    with st.form("comment_form", clear_on_submit=True):

        new_comment = st.text_input("응원 메시지")

        submit = st.form_submit_button("등록")

        if submit and new_comment:

            now = datetime.now() + timedelta(hours=9)

            new_row = pd.DataFrame([{
                "name": st.session_state.user_name,
                "comment": new_comment,
                "date": now.strftime("%m/%d %H:%M")
            }])

            updated = pd.concat([comments_df, new_row], ignore_index=True)

            conn.update(
                worksheet="comments",
                data=updated
            )

            st.rerun()

if not comments_df.empty:

    show_comments = comments_df.sort_index(ascending=False).head(10)

    for idx, row in show_comments.iterrows():

        col1, col2 = st.columns([10,1])

        with col1:
            st.write(f"{row['name']} : {row['comment']}")

        with col2:
            if st.session_state.is_auth and st.session_state.user_name == row['name']:

                if st.button("x", key=f"del_c_{idx}"):

                    new_df = comments_df.drop(idx)

                    conn.update(
                        worksheet="comments",
                        data=new_df
                    )

                    st.rerun()

st.divider()

if st.session_state.is_auth:

    my_data = df[df['name'] == st.session_state.user_name].copy()

    my_data['weight'] = pd.to_numeric(my_data['weight'], errors='coerce')

    if not my_data.empty:

        st.subheader("📊 나의 퍼포먼스")

        chart_df = my_data.sort_values('weight', ascending=False).drop_duplicates('exercise')

        chart = alt.Chart(chart_df).mark_bar().encode(
            x='weight:Q',
            y='exercise:N'
        )

        st.altair_chart(chart, use_container_width=True)

st.divider()

st.subheader("💪 오늘의 기록 업데이트")

if st.session_state.is_auth:

    save_exercise = st.selectbox("종목", exercise_list)

    with st.form("record_form"):

        new_weight = st.number_input("중량")

        new_memo = st.text_input("메모")

        save = st.form_submit_button("저장")

        if save and new_weight > 0:

            now = datetime.now() + timedelta(hours=9)

            new_record = pd.DataFrame([{
                "name": st.session_state.user_name,
                "exercise": save_exercise,
                "weight": new_weight,
                "date": now.strftime("%Y-%m-%d"),
                "password": "0000",
                "gender": st.session_state.user_gender,
                "memo": new_memo
            }])

            updated_df = pd.concat([df, new_record], ignore_index=True)

            conn.update(
                worksheet="Sheet1",
                data=updated_df
            )

            st.success("기록 저장 완료!")

            st.rerun()

else:

    st.warning("로그인 후 이용 가능합니다.")

with st.expander("Admin"):

    admin_pw = st.text_input("Key", type="password")

    if admin_pw == "5207":

        st.dataframe(df)

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import time

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="wide")

# --- 커스텀 CSS (모바일 가로배치 + 텍스트 간격 최적화) ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #f8f9fa; }
    .ranking-container {
        display: flex;
        flex-direction: row;
        gap: 10px;
        margin-bottom: 20px;
    }
    .rank-card {
        flex: 1;
        background: white;
        padding: 12px 10px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #eee;
        min-width: 0;
    }
    .rank-header {
        text-align: center;
        font-weight: 800;
        font-size: 0.9rem;
        color: #555;
        border-bottom: 2px solid #f1f3f5;
        padding-bottom: 8px;
        margin-bottom: 12px;
    }
    .rank-entry {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 5px;
        border-bottom: 1px solid #fcfcfc;
    }
    .rank-name {
        font-size: 0.85rem;
        font-weight: 600;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .rank-weight {
        font-size: 0.85rem;
        font-weight: 700;
        color: #29b5e8;
        flex-shrink: 0;
    }
    .me-highlight { background-color: #e3f2fd; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def get_full_data():
    try:
        raw_df = conn.read(worksheet="sheet1", ttl=0)
        if raw_df is None or raw_df.empty:
            return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo'])
        if 'password' in raw_df.columns:
            raw_df['password'] = raw_df['password'].astype(str).str.replace(".0", "", regex=False)
        return raw_df
    except:
        return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo'])

def get_comments():
    try:
        c_df = conn.read(worksheet="comments", ttl=0)
        return c_df if c_df is not None else pd.DataFrame(columns=['name', 'comment', 'date'])
    except:
        return pd.DataFrame(columns=['name', 'comment', 'date'])

df = get_full_data()
comments_df = get_comments()

if 'is_auth' not in st.session_state:
    st.session_state.is_auth, st.session_state.user_name, st.session_state.user_gender = False, "", "남성"

st.title("🏋️ 1RM 보관함")

# --- 3. 랭킹 섹션 (남좌여우 가로 배치) ---
st.subheader("🏆 박스 실시간 랭킹")
exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press", "Thruster", "Bench Press", "Jerk", "Overhead Squat"]
sel_ex = st.selectbox("랭킹 종목 선택", exercise_list, index=0)

r_df = df[df['exercise'] == sel_ex].copy()
r_df['weight'] = pd.to_numeric(r_df['weight'], errors='coerce')
best_df = r_df.sort_values('weight', ascending=False).drop_duplicates('name')

m_ranks = best_df[best_df['gender'] == "남성"].sort_values('weight', ascending=False)
f_ranks = best_df[best_df['gender'] == "여성"].sort_values('weight', ascending=False)

def render_card(data, title, icon):
    html = f"<div class='rank-card'><div class='rank-header'>{icon} {title}</div>"
    if data.empty:
        html += "<div style='text-align:center;color:gray;font-size:0.8rem;'>기록 없음</div>"
    else:
        for i, row in enumerate(data.itertuples(), 1):
            medal = {1:"🥇", 2:"🥈", 3:"🥉"}.get(i, f"{i}.")
            is_me = "me-highlight" if st.session_state.user_name == row.name else ""
            html += f"""
            <div class='rank-entry {is_me}'>
                <span class='rank-name'>{medal} {row.name}</span>
                <span class='rank-weight'>{int(row.weight)} lb</span>
            </div>
            """
    html += "</div>"
    return html

# 남좌여우 가로 배치 출력
st.markdown(f"""
    <div class='ranking-container'>
        {render_card(m_ranks, "MALE", "♂️")}
        {render_card(f_ranks, "FEMALE", "♀️")}
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- 4. 실시간 응원 한마디 ---
st.subheader("💬 실시간 응원 한마디")
if st.session_state.is_auth:
    with st.form(key="comm_form", clear_on_submit=True):
        c1, c2 = st.columns([4, 1])
        new_c = c1.text_input(f"{st.session_state.user_name}님, 응원의 한마디!", placeholder="예: 재효님 클린 미쳤네요ㄷㄷ")
        if c2.form_submit_button("등록") and new_c:
            kst = (datetime.now() + timedelta(hours=9)).strftime("%m/%d %H:%M")
            new_row = pd.DataFrame([{"name": st.session_state.user_name, "comment": new_c, "date": kst}])
            conn.update(worksheet="comments", data=pd.concat([comments_df, new_row], ignore_index=True))
            st.success("🔥 등록 완료!"); time.sleep(0.5); st.rerun()

if not comments_df.empty:
    with st.expander("최근 댓글 보기", expanded=True):
        for idx, row in comments_df.sort_index(ascending=False).head(10).iterrows():
            st.markdown(f"**{row['name']}** <small style='color:gray;'>{row['date']}</small>", unsafe_allow_html=True)
            st.info(row['comment'])

st.divider()

# --- 5. 로그인 및 기록 저장 ---
if not st.session_state.is_auth:
    st.subheader("👤 입장하기")
    mode = st.radio("방식", ["로그인", "신규등록"], horizontal=True)
    if mode == "로그인":
        u_list = sorted(df['name'].unique().tolist()) if not df.empty else []
        sel_name = st.selectbox("이름", ["선택하세요"] + u_list)
        pw_in = st.text_input("비밀번호", type="password")
        if st.button("입장", use_container_width=True):
            user_data = df[df['name'] == sel_name]
            if not user_data.empty and pw_in == str(user_data.iloc[-1]['password']):
                st.session_state.is_auth, st.session_state.user_name = True, sel_name
                st.session_state.user_gender = user_data.iloc[-1]['gender']
                st.rerun()
            else: st.error("비번 틀림")
    else:
        c1, c2 = st.columns(2)
        n_n, n_p = c1.text_input("새 이름"), c2.text_input("비번", type="password")
        n_g = st.radio("성별", ["남성", "여성"], horizontal=True)
        if st.button("가입완료", use_container_width=True) and n_n and n_p:
            st.session_state.is_auth, st.session_state.user_name, st.session_state.user_gender = True, n_n, n_g
            st.session_state.temp_pw = str(n_p)
            st.rerun()
else:
    # 개인 기록 저장 섹션
    st.subheader("💪 기록 갱신")
    my_data = df[df['name'] == st.session_state.user_name].copy()
    with st.container(border=True):
        sc1, sc2 = st.columns(2)
        in_ex = sc1.selectbox("종목", exercise_list)
        in_wt = sc2.number_input("중량(lb)", step=5.0)
        in_mm = st.text_input("메모")
        if st.button("기록 저장하기", use_container_width=True) and in_wt > 0:
            pw = str(my_data['password'].iloc[0]) if not my_data.empty else st.session_state.get('temp_pw', '0000')
            new_r = pd.DataFrame([{"name": st.session_state.user_name, "exercise": in_ex, "weight": in_wt, "date": (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d"), "password": pw, "gender": st.session_state.user_gender, "memo": in_mm}])
            conn.update(worksheet="sheet1", data=pd.concat([df, new_r], ignore_index=True))
            st.balloons(); time.sleep(1); st.rerun()
    
    if st.button("로그아웃"):
        st.session_state.is_auth = False
        st.rerun()

with st.expander("🛠 Admin"):
    if st.text_input("Key", type="password") == "5207": st.dataframe(df)

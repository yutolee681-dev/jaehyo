import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import time

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="wide")

# --- 커스텀 CSS (UI 개선) ---
st.markdown("""
    <style>
    /* 전체 배경 및 폰트 설정 */
    [data-testid="stAppViewContainer"] { background-color: #f8f9fa; }
    .stMarkdown { font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif; }
    
    /* 랭킹 컨테이너 플렉스박스 */
    .ranking-wrapper {
        display: flex;
        gap: 10px;
        width: 100%;
        margin-bottom: 20px;
    }
    .rank-card {
        flex: 1;
        background: white;
        padding: 15px 10px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #eee;
        min-width: 0; /* 텍스트 넘침 방지 */
    }
    .rank-title {
        text-align: center;
        font-weight: 800;
        font-size: 1.1rem;
        margin-bottom: 15px;
        padding-bottom: 8px;
        border-bottom: 2px solid #f0f0f0;
    }
    .rank-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 5px;
        border-bottom: 1px solid #fafafa;
    }
    .rank-name {
        font-weight: 600;
        font-size: 0.9rem;
        color: #333;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        margin-right: 5px;
    }
    .rank-weight {
        font-family: 'Monaco', monospace;
        font-weight: 700;
        color: #29b5e8;
        font-size: 0.95rem;
        flex-shrink: 0;
    }
    .my-record { background-color: #e3f2fd; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 서수(Ordinal) 변환 함수 ---
def get_ordinal(n):
    if 11 <= n % 100 <= 13: suffix = 'th'
    else: suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press", "Thruster", "Bench Press", "Jerk", "Overhead Squat"]
rename_map = {"Power Clean": "P.Clean", "Squat Clean": "S.Clean", "Power Snatch": "P.Snatch", "Squat Snatch": "S.Snatch", "Deadlift": "Dead", "Back Squat": "B.Squat", "Shoulder Press": "S.Press", "Thruster": "Thrust", "Bench Press": "Bench", "Jerk": "Jerk", "Overhead Squat": "OHS"}

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def get_full_data():
    try:
        raw_df = conn.read(worksheet="sheet1", ttl=0)
        if raw_df is None or raw_df.empty: return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo'])
        if 'password' in raw_df.columns: raw_df['password'] = raw_df['password'].astype(str).str.replace(".0", "", regex=False)
        for col, default in {'password': '0000', 'gender': '남성', 'memo': ''}.items():
            if col not in raw_df.columns: raw_df[col] = default
        return raw_df
    except: return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo'])

df = get_full_data()

if 'is_auth' not in st.session_state: st.session_state.is_auth, st.session_state.user_name, st.session_state.user_gender = False, "", "남성"

st.title("🏋️ 1RM을 기억해")

if st.session_state.is_auth:
    col_w, col_l = st.columns([5, 1])
    col_w.write(f"**{st.session_state.user_name}**님 득근하세요! 💪")
    if col_l.button("로그아웃"):
        st.session_state.is_auth = False
        st.rerun()

# --- 4. 랭킹 섹션 (남좌여우 가로 배치) ---
st.subheader("🏆 박스 실시간 랭킹")
selected_rank_exercise = st.selectbox("종목 선택", exercise_list, index=0)

rank_df = df[df['exercise'] == selected_rank_exercise].copy()
rank_df['weight'] = pd.to_numeric(rank_df['weight'], errors='coerce')
best_rank_df = rank_df.sort_values('weight', ascending=False).drop_duplicates('name')

m_ranks = best_rank_df[best_rank_df['gender'] == "남성"].sort_values(by='weight', ascending=False)
f_ranks = best_rank_df[best_rank_df['gender'] == "여성"].sort_values(by='weight', ascending=False)

def make_rank_card_html(data, title, icon):
    html = f"<div class='rank-card'><div class='rank-title'>{icon} {title}</div>"
    if data.empty:
        html += "<p style='text-align:center; color:gray; font-size:0.8rem;'>기록 없음</p>"
    else:
        for i, row in enumerate(data.itertuples(), 1):
            medal = {1:"🥇", 2:"🥈", 3:"🥉"}.get(i, f"<small>{i}th</small>")
            is_me = "my-record" if st.session_state.user_name == row.name else ""
            html += f"""
            <div class='rank-item {is_me}'>
                <div class='rank-name'>{medal} {row.name}</div>
                <div class='rank-weight'>{int(row.weight)} lb</div>
            </div>
            """
    html += "</div>"
    return html

# ✅ 남자가 왼쪽(Male), 여자가 오른쪽(Female) 강제 배치
st.markdown(f"""
    <div class='ranking-wrapper'>
        {make_rank_card_html(m_ranks, "MALE", "♂️")}
        {make_rank_card_html(f_ranks, "FEMALE", "♀️")}
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- 6. 사용자 인증 ---
if not st.session_state.is_auth:
    st.subheader("👤 로그인 / 회원가입")
    mode = st.radio("방식", ["로그인", "신규등록"], horizontal=True)
    if mode == "로그인":
        u_list = sorted(df['name'].dropna().unique().tolist()) if not df.empty else []
        sel_name = st.selectbox("이름", ["선택"] + u_list)
        pw_in = st.text_input("비밀번호", type="password")
        if st.button("입장", use_container_width=True):
            stored_pw = str(df[df['name'] == sel_name].iloc[-1]['password']).strip()
            if pw_in.strip() == stored_pw:
                st.session_state.is_auth, st.session_state.user_name = True, sel_name
                st.session_state.user_gender = df[df['name'] == sel_name].iloc[-1]['gender']
                st.rerun()
            else: st.error("비번 틀림")
    else:
        c1, c2 = st.columns(2)
        n_name = c1.text_input("이름")
        n_pw = c2.text_input("비번", type="password")
        n_gender = st.radio("성별", ["남성", "여성"], horizontal=True)
        if st.button("가입 및 로그인", use_container_width=True):
            if n_name and n_pw:
                st.session_state.is_auth, st.session_state.user_name, st.session_state.user_gender = True, n_name, n_gender
                st.session_state.temp_pw = str(n_pw)
                st.rerun()

# --- 7. 개인 차트 및 상세 기록 ---
if st.session_state.is_auth:
    my_data = df[df['name'] == st.session_state.user_name].copy()
    my_data['weight'] = pd.to_numeric(my_data['weight'], errors='coerce')
    
    if not my_data.empty:
        st.write(f"📊 **{st.session_state.user_name}**님의 최고 기록")
        chart_df = my_data.sort_values('weight', ascending=False).drop_duplicates('exercise').copy()
        chart_df['exercise_short'] = chart_df['exercise'].map(rename_map).fillna(chart_df['exercise'])
        base = alt.Chart(chart_df).encode(y=alt.Y('exercise_short:N', sort='-x', title=None), x=alt.X('weight:Q', title="lbs"))
        st.altair_chart(base.mark_bar(color="#29b5e8", cornerRadiusEnd=5) + base.mark_text(align='right', dx=-5, color='white').encode(text='weight:Q'), use_container_width=True)
        
        with st.expander("📋 상세 기록 보기"):
            st.dataframe(my_data[['date', 'exercise', 'weight', 'memo']].sort_values('date', ascending=False), hide_index=True, use_container_width=True)

    st.divider()

    # --- 8. 기록 업데이트 ---
    st.subheader("💪 기록 갱신")
    save_ex = st.selectbox("종목", exercise_list)
    new_w = st.number_input("무게 (lb)", step=5.0)
    new_m = st.text_input("메모 (컨디션 등)")
    if st.button("저장하기", use_container_width=True) and new_w > 0:
        u_rows = df[df['name'] == st.session_state.user_name]
        existing_pw = str(u_rows['password'].iloc[0]) if not u_rows.empty else st.session_state.get('temp_pw', '0000')
        new_rec = pd.DataFrame([{"name": st.session_state.user_name, "exercise": save_ex, "weight": new_w, "date": (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d"), "password": existing_pw, "gender": st.session_state.user_gender, "memo": new_m}])
        conn.update(worksheet="sheet1", data=pd.concat([df, new_rec], ignore_index=True))
        st.success("기록 완료!"); time.sleep(1); st.rerun()

with st.expander("🛠 Admin"):
    if st.text_input("Key", type="password") == "5207": st.dataframe(df)

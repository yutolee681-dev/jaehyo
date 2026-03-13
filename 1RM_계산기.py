import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import time

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="wide")

# --- 커스텀 CSS (모바일 가로배치 고정 + UI 최적화) ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #f5f7f9; }
    
    /* 랭킹 전체 감싸는 박스 */
    .rank-wrapper {
        display: flex;
        flex-direction: row; /* 무조건 가로로 */
        gap: 10px;
        width: 100%;
        margin: 10px 0;
    }
    
    /* 개별 카드 스타일 */
    .rank-card {
        flex: 1;
        background: white;
        padding: 12px 8px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        border: 1px solid #e1e4e8;
        min-width: 0;
    }
    
    .rank-header {
        text-align: center;
        font-weight: 800;
        font-size: 0.95rem;
        padding-bottom: 8px;
        margin-bottom: 10px;
        border-bottom: 2px solid #f0f2f6;
    }
    
    /* 랭킹 한 줄(이름...무게) */
    .rank-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 4px;
        border-bottom: 1px solid #f8f9fa;
    }
    
    .rank-name {
        font-size: 0.8rem;
        font-weight: 600;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: #333;
    }
    
    .rank-weight {
        font-size: 0.85rem;
        font-weight: 800;
        color: #007bff;
        flex-shrink: 0;
        margin-left: 5px;
    }
    
    /* 내 기록 강조 */
    .is-me { background-color: #e7f3ff; border-radius: 6px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        raw = conn.read(worksheet="sheet1", ttl=0)
        if raw is None or raw.empty: return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo'])
        raw['password'] = raw['password'].astype(str).str.replace(".0", "", regex=False)
        return raw
    except: return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo'])

df = get_data()

if 'is_auth' not in st.session_state: 
    st.session_state.is_auth, st.session_state.user_name, st.session_state.user_gender = False, "", "남성"

st.title("🏋️ 1RM 보관함")

# --- 4. 랭킹 섹션 (남좌여우 가로 배치) ---
st.subheader("🏆 박스 실시간 랭킹")
exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press", "Thruster", "Bench Press", "Jerk", "Overhead Squat"]
sel_ex = st.selectbox("종목 선택", exercise_list)

r_df = df[df['exercise'] == sel_ex].copy()
r_df['weight'] = pd.to_numeric(r_df['weight'], errors='coerce')
best_df = r_df.sort_values('weight', ascending=False).drop_duplicates('name')

m_data = best_df[best_df['gender'] == "남성"]
f_data = best_df[best_df['gender'] == "여성"]

# ✅ HTML 태그 에러 방지를 위해 f-string 대신 조립 방식 사용
def render_rank_card(data, label, icon):
    rows_html = ""
    if data.empty:
        rows_html = "<div style='text-align:center;color:gray;font-size:0.8rem;'>기록 없음</div>"
    else:
        for i, row in enumerate(data.itertuples(), 1):
            medal = {1:"🥇", 2:"🥈", 3:"🥉"}.get(i, f"{i}.")
            me_class = "is-me" if st.session_state.user_name == row.name else ""
            rows_html += f"""
            <div class='rank-row {me_class}'>
                <span class='rank-name'>{medal} {row.name}</span>
                <span class='rank-weight'>{int(row.weight)} lb</span>
            </div>
            """
    
    return f"""
    <div class='rank-card'>
        <div class='rank-header'>{icon} {label}</div>
        {rows_html}
    </div>
    """

# ✅ 남자가 왼쪽(Male), 여자가 오른쪽(Female) 고정 배치
st.markdown(f"""
    <div class='rank-wrapper'>
        {render_rank_card(m_data, "MALE", "♂️")}
        {render_rank_card(f_data, "FEMALE", "♀️")}
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- 6. 인증 및 로그인 ---
if not st.session_state.is_auth:
    st.subheader("👤 입장하기")
    m = st.radio("방식", ["로그인", "신규등록"], horizontal=True)
    if m == "로그인":
        u_list = sorted(df['name'].unique().tolist()) if not df.empty else []
        s_name = st.selectbox("이름", ["선택"] + u_list)
        pw_in = st.text_input("비밀번호", type="password")
        if st.button("들어가기", use_container_width=True):
            user_rows = df[df['name'] == s_name]
            if not user_rows.empty:
                stored = str(user_rows.iloc[-1]['password']).strip()
                if pw_in.strip() == stored:
                    st.session_state.is_auth, st.session_state.user_name = True, s_name
                    st.session_state.user_gender = user_rows.iloc[-1]['gender']
                    st.rerun()
                else: st.error("비밀번호가 틀렸습니다.")
    else:
        c1, c2 = st.columns(2)
        n_n, n_p = c1.text_input("새 이름"), c2.text_input("비번 설정", type="password")
        n_g = st.radio("성별", ["남성", "여성"], horizontal=True)
        if st.button("가입 후 입장", use_container_width=True) and n_n and n_p:
            st.session_state.is_auth, st.session_state.user_name, st.session_state.user_gender = True, n_n, n_g
            st.session_state.temp_pw = str(n_p)
            st.rerun()

# --- 7. 개인 데이터 및 저장 ---
if st.session_state.is_auth:
    my = df[df['name'] == st.session_state.user_name].copy()
    
    st.subheader(f"💪 {st.session_state.user_name}님의 기록")
    if not my.empty:
        with st.expander("📋 나의 전체 기록 보기"):
            st.dataframe(my[['date', 'exercise', 'weight', 'memo']].sort_values('date', ascending=False), hide_index=True, use_container_width=True)
    
    # 기록 저장
    with st.container(border=True):
        st.write("**오늘의 기록 저장**")
        sc1, sc2 = st.columns(2)
        save_ex = sc1.selectbox("종목", exercise_list, key="save_ex")
        new_w = sc2.number_input("무게(lb)", step=5.0)
        new_m = st.text_input("메모")
        if st.button("저장하기", use_container_width=True) and new_w > 0:
            rows = df[df['name'] == st.session_state.user_name]
            pw = str(rows['password'].iloc[0]) if not rows.empty else st.session_state.get('temp_pw', '0000')
            new_row = pd.DataFrame([{"name": st.session_state.user_name, "exercise": save_ex, "weight": new_w, "date": (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d"), "password": pw, "gender": st.session_state.user_gender, "memo": new_m}])
            conn.update(worksheet="sheet1", data=pd.concat([df, new_row], ignore_index=True))
            st.success("기록 완료!"); time.sleep(1); st.rerun()

# --- 8. Admin ---
with st.expander("🛠 Admin"):
    if st.text_input("Key", type="password") == "5207": st.dataframe(df)

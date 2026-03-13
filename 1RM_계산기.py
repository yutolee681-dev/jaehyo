import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import time

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="wide")

# --- 커스텀 CSS (UI 대공사: 폰에서도 무조건 남좌여우) ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #f1f3f5; }
    
    .ranking-container {
        display: flex;
        flex-direction: row; /* 가로 배치 강제 */
        gap: 8px;
        width: 100%;
        margin-top: 10px;
    }
    
    .rank-box {
        flex: 1;
        background: white;
        padding: 12px 8px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        min-width: 0; /* 좁은 화면 대응 */
    }
    
    .rank-header {
        text-align: center;
        font-weight: 800;
        font-size: 1rem;
        color: #333;
        border-bottom: 2px solid #eee;
        margin-bottom: 10px;
        padding-bottom: 5px;
    }
    
    .rank-entry {
        display: flex;
        justify-content: space-between; /* 이름 왼쪽, 무게 오른쪽 */
        align-items: center;
        padding: 6px 4px;
        border-bottom: 1px solid #f9f9f9;
    }
    
    .name-tag {
        font-size: 0.85rem;
        font-weight: 600;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-right: 4px;
    }
    
    .weight-tag {
        font-size: 0.9rem;
        font-weight: 700;
        color: #1a73e8;
        flex-shrink: 0;
    }
    
    .my-row { background-color: #e8f0fe; border-radius: 4px; }
    </style>
    """, unsafe_allow_html=True)

# --- 보조 함수 ---
def get_ordinal(n):
    if 11 <= n % 100 <= 13: return f"{n}th"
    return f"{n}" + {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')

exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press", "Thruster", "Bench Press", "Jerk", "Overhead Squat"]

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        raw = conn.read(worksheet="sheet1", ttl=0)
        if raw is None or raw.empty: return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo'])
        raw['password'] = raw['password'].astype(str).str.replace(".0", "", regex=False)
        return raw
    except: return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo'])

df = get_data()

if 'is_auth' not in st.session_state: st.session_state.is_auth, st.session_state.user_name, st.session_state.user_gender = False, "", "남성"

st.title("🏋️ 1RM 보관함")

# --- 4. 랭킹 섹션 (남좌여우 고정) ---
st.subheader("🏆 실시간 랭킹")
sel_ex = st.selectbox("종목 선택", exercise_list, index=0)

r_df = df[df['exercise'] == sel_ex].copy()
r_df['weight'] = pd.to_numeric(r_df['weight'], errors='coerce')
best_df = r_df.sort_values('weight', ascending=False).drop_duplicates('name')

m_list = best_df[best_df['gender'] == "남성"]
f_list = best_df[best_df['gender'] == "여성"]

def build_rank_card(data, label, icon):
    content = f"<div class='rank-box'><div class='rank-header'>{icon} {label}</div>"
    if data.empty:
        content += "<div style='text-align:center; font-size:0.8rem; color:gray;'>기록 없음</div>"
    else:
        for i, row in enumerate(data.itertuples(), 1):
            is_me = "my-row" if st.session_state.user_name == row.name else ""
            medal = {1:"🥇", 2:"🥈", 3:"🥉"}.get(i, f"{i}.")
            content += f"""
            <div class='rank-entry {is_me}'>
                <div class='name-tag'>{medal} {row.name}</div>
                <div class='weight-tag'>{int(row.weight)}lb</div>
            </div>
            """
    content += "</div>"
    return content

# ✅ 요청하신 대로 왼쪽 남자(MALE), 오른쪽 여자(FEMALE) 고정
st.markdown(f"""
    <div class='ranking-container'>
        {build_rank_card(m_list, "MALE", "♂️")}
        {build_rank_card(f_list, "FEMALE", "♀️")}
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- 6. 인증 ---
if not st.session_state.is_auth:
    st.subheader("👤 입장하기")
    m = st.radio("로그인 방식", ["기존", "신규"], horizontal=True)
    if m == "기존":
        u_list = sorted(df['name'].unique().tolist()) if not df.empty else []
        s_name = st.selectbox("이름", ["선택"] + u_list)
        pw_in = st.text_input("비번", type="password")
        if st.button("로그인", use_container_width=True):
            stored = str(df[df['name'] == s_name].iloc[-1]['password']).strip()
            if pw_in.strip() == stored:
                st.session_state.is_auth, st.session_state.user_name, st.session_state.user_gender = True, s_name, df[df['name'] == s_name].iloc[-1]['gender']
                st.rerun()
            else: st.error("비번 오류")
    else:
        c1, c2 = st.columns(2)
        n_n, n_p = c1.text_input("새이름"), c2.text_input("새비번", type="password")
        n_g = st.radio("성별", ["남성", "여성"], horizontal=True)
        if st.button("가입완료", use_container_width=True) and n_n and n_p:
            st.session_state.is_auth, st.session_state.user_name, st.session_state.user_gender = True, n_n, n_g
            st.session_state.temp_pw = str(n_p)
            st.rerun()

# --- 7. 개인 데이터 ---
if st.session_state.is_auth:
    my = df[df['name'] == st.session_state.user_name].copy()
    if not my.empty:
        st.write(f"📊 **{st.session_state.user_name}**님의 최고 기록")
        with st.expander("📋 상세 기록 (전체보기)"):
            st.dataframe(my[['date', 'exercise', 'weight', 'memo']].sort_values('date', ascending=False), hide_index=True, use_container_width=True)

    st.divider()

    # --- 8. 저장 ---
    st.subheader("💪 오늘 기록 저장")
    ex = st.selectbox("종목", exercise_list)
    wt = st.number_input("중량(lb)", step=5.0)
    mm = st.text_input("메모")
    if st.button("저장!", use_container_width=True) and wt > 0:
        rows = df[df['name'] == st.session_state.user_name]
        pw = str(rows['password'].iloc[0]) if not rows.empty else st.session_state.get('temp_pw', '0000')
        new = pd.DataFrame([{"name": st.session_state.user_name, "exercise": ex, "weight": wt, "date": (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d"), "password": pw, "gender": st.session_state.user_gender, "memo": mm}])
        conn.update(worksheet="sheet1", data=pd.concat([df, new], ignore_index=True))
        st.success("저장 완료!"); time.sleep(1); st.rerun()

with st.expander("🛠 Admin"):
    if st.text_input("Key", type="password") == "5207": st.dataframe(df)

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import time

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="centered")

# --- 서수(Ordinal) 변환 함수 ---
def get_ordinal(n):
    if 11 <= n % 100 <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

# --- 종목 및 단축어 설정 ---
exercise_list = [
    "Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", 
    "Deadlift", "Back Squat", "Shoulder Press", "Thruster", 
    "Bench Press", "Jerk", "Overhead Squat"
]
rename_map = {
    "Power Clean": "P.Clean", "Squat Clean": "S.Clean", "Power Snatch": "P.Snatch",
    "Squat Snatch": "S.Snatch", "Deadlift": "Dead", "Back Squat": "B.Squat",
    "Shoulder Press": "S.Press", "Thruster": "Thrust", "Bench Press": "Bench",
    "Jerk": "Jerk", "Overhead Squat": "OHS"
}

# --- 2. 구글 시트 연결 설정 (핵심 수정 부분) ---
# URL 끝에 /edit#gid=0 등을 지우고 ID까지만 입력하는 것이 가장 안전합니다.
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ekqS81gko96DVkrFsBkg2-bQiF3oAcHkXd02oHJQ1R4"

conn = st.connection("gsheets", type=GSheetsConnection)

def get_full_data():
    try:
        # spreadsheet=SHEET_URL 인자를 추가하여 404 에러 방지
        raw_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
        if raw_df is None or raw_df.empty:
            return pd.DataFrame(columns=['name','exercise','weight','date','password','gender','memo'])
        
        required_cols = {'password': '0000', 'gender': '남성', 'memo': ''}
        for col, default in required_cols.items():
            if col not in raw_df.columns:
                raw_df[col] = default
        return raw_df
    except Exception as e:
        st.error(f"Sheet1 읽기 에러: {e}")
        return pd.DataFrame(columns=['name','exercise','weight','date','password','gender','memo'])

def get_comments():
    try:
        # worksheet="comments" 이름 확인 완료
        c_df = conn.read(spreadsheet=SHEET_URL, worksheet="comments", ttl=0)
        if c_df is None:
            return pd.DataFrame(columns=['name','comment','date'])
        return c_df
    except Exception as e:
        st.error(f"comments 읽기 에러: {e}")
        return pd.DataFrame(columns=['name','comment','date'])

# 데이터 로드
df = get_full_data()
comments_df = get_comments()

# 세션 상태 초기화
if 'is_auth' not in st.session_state:
    st.session_state.is_auth = False
    st.session_state.user_name = ""
    st.session_state.user_gender = "남성"

st.markdown("<div id='link_to_top'></div>", unsafe_allow_html=True)
st.title("🏋️ 1RM을 기억해")

# --- 3. 최상단 환영 메시지 및 로그아웃 ---
if st.session_state.is_auth:
    col_welcome, col_refresh, col_logout = st.columns([2, 1, 1])
    with col_welcome:
        st.markdown(f"👋 **{st.session_state.user_name}**님")
    with col_refresh:
        if st.button("🔄 갱신", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col_logout:
        if st.button("로그아웃", use_container_width=True):
            st.session_state.is_auth = False
            st.session_state.user_name = ""
            st.rerun()
    st.divider()

# --- 4. 실시간 전체 랭킹 ---
st.subheader("🏆 박스 실시간 랭킹 (전체)")
selected_rank_exercise = st.selectbox("랭킹 종목 선택", exercise_list, index=0)
rank_df = df[df['exercise'] == selected_rank_exercise].copy()
rank_df['weight'] = pd.to_numeric(rank_df['weight'], errors='coerce')
best_rank_df = rank_df.sort_values('weight', ascending=False).drop_duplicates('name')

with st.expander(f"🔥 {selected_rank_exercise} 전체 순위 보기", expanded=True):
    if not best_rank_df.empty:
        m_data = best_rank_df[best_rank_df['gender'] == "남성"].sort_values('weight', ascending=False)
        f_data = best_rank_df[best_rank_df['gender'] == "여성"].sort_values('weight', ascending=False)
        max_rows = max(len(m_data), len(f_data))

        html_code = """<table style="width:100%; border-collapse: collapse; font-size: 0.8rem; table-layout: fixed;">
        <thead><tr style="border-bottom: 1px solid #444;"><th style="padding: 5px;">♂️ Male</th><th style="padding: 5px;">♀️ Female</th></tr></thead><tbody>"""
        
        for i in range(max_rows):
            m_col = "<td>-</td>"
            if i < len(m_data):
                row_m = m_data.iloc[i]
                medal = "🥇" if i==0 else "🥈" if i==1 else "🥉" if i==2 else f"{get_ordinal(i+1)}"
                style = "color:#29b5e8; font-weight:bold;" if st.session_state.user_name == row_m['name'] else ""
                m_col = f"<td>{medal} <span style='{style}'>{row_m['name']}</span> <b>{row_m['weight']}</b></td>"
            
            f_col = "<td>-</td>"
            if i < len(f_data):
                row_f = f_data.iloc[i]
                medal = "🥇" if i==0 else "🥈" if i==1 else "🥉" if i==2 else f"{get_ordinal(i+1)}"
                style = "color:#29b5e8; font-weight:bold;" if st.session_state.user_name == row_f['name'] else ""
                f_col = f"<td>{medal} <span style='{style}'>{row_f['name']}</span> <b>{row_f['weight']}</b></td>"
            
            html_code += f"<tr>{m_col}{f_col}</tr>"
        html_code += "</tbody></table>"
        st.markdown(html_code, unsafe_allow_html=True)
    else:
        st.write("첫 주인공이 되어보세요!")
st.divider()

# --- 5. 실시간 응원 한마디 ---
st.subheader("💬 실시간 응원 한마디")
if st.session_state.is_auth:
    with st.form(key="comment_form", clear_on_submit=True):
        col_c1, col_c2 = st.columns([4, 1])
        with col_c1:
            new_comment = st.text_input(f"{st.session_state.user_name}님, 한마디!", placeholder="오늘 컨디션 최고! 🔥")
        with col_c2:
            if st.form_submit_button("등록") and new_comment:
                kst_now = datetime.now() + timedelta(hours=9)
                new_c_row = pd.DataFrame([{"name": st.session_state.user_name, "comment": new_comment, "date": kst_now.strftime("%m/%d %H:%M")}])
                all_comments = pd.concat([comments_df, new_c_row], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="comments", data=all_comments)
                st.rerun()
else:
    st.info("로그인하면 응원 댓글을 남길 수 있습니다.")

if not comments_df.empty:
    with st.expander("📂 최근 응원 메시지", expanded=True):
        display_comments = comments_df.sort_index(ascending=False).head(10)
        for idx, row in display_comments.iterrows():
            c_main, c_del = st.columns([10, 1])
            with c_main:
                st.markdown(f"""<div style="margin-bottom: 5px; padding: 8px; border-bottom: 1px solid rgba(128,128,128,0.2);">
                <span style="font-weight: bold; font-size: 0.85rem; color: #29b5e8;">{row['name']}</span> <span style="color: #888; font-size: 0.7rem;">{row['date']}</span><br>
                <div style="font-size: 0.9rem; margin-top: 3px;">{row['comment']}</div></div>""", unsafe_allow_html=True)
            with c_del:
                if st.session_state.is_auth and st.session_state.user_name == row['name']:
                    if st.button("x", key=f"del_c_{idx}"):
                        conn.update(spreadsheet=SHEET_URL, worksheet="comments", data=comments_df.drop(idx))
                        st.rerun()
st.divider()

# --- 6. 사용자 인증 ---
if not st.session_state.is_auth:
    st.subheader("👤 사용자 인증")
    mode = st.radio("로그인 방식", ["기존 사용자", "신규 등록"], horizontal=True)
    
    if mode == "기존 사용자":
        user_list = sorted(df['name'].dropna().unique().tolist()) if not df.empty else []
        selected_name = st.selectbox("이름 선택", options=user_list, index=None, placeholder="이름을 선택하세요")
        if selected_name:
            pw_input = st.text_input("비밀번호", type="password")
            if st.button("로그인", use_container_width=True):
                user_rows = df[df['name'] == selected_name]
                stored_pw = str(user_rows.iloc[-1]['password']).strip().replace("'", "")
                if pw_input.strip() == stored_pw:
                    st.session_state.is_auth = True
                    st.session_state.user_name = selected_name
                    st.session_state.user_gender = user_rows.iloc[-1]['gender']
                    st.success(f"어서오세요, {selected_name}님!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("비밀번호가 틀렸습니다.")
    else:
        c1, c2 = st.columns(2)
        new_name = c1.text_input("새 이름")
        new_gender = c2.radio("성별", ["남성", "여성"], horizontal=True)
        new_pw = st.text_input("비밀번호 설정", type="password")
        if st.button("등록 및 로그인", use_container_width=True):
            if new_name and new_pw:
                st.session_state.is_auth = True
                st.session_state.user_name = new_name
                st.session_state.user_gender = new_gender
                st.session_state.temp_pw = f"'{new_pw}"
                st.rerun()

# --- 7. 개인 데이터 분석 및 관리 ---
if st.session_state.is_auth:
    my_data = df[df['name'] == st.session_state.user_name].copy()
    my_data['weight'] = pd.to_numeric(my_data['weight'], errors='coerce')
    
    if not my_data.empty:
        st.subheader("📊 나의 퍼포먼스 리포트")
        tab1, tab2, tab3 = st.tabs(["🏆 최고 기록", "📈 성장률", "📋 히스토리"])
        
        with tab1:
            chart_df = my_data.sort_values('weight', ascending=False).drop_duplicates('exercise').copy()
            chart_df['exercise_short'] = chart_df['exercise'].map(rename_map).fillna(chart_df['exercise'])
            chart = alt.Chart(chart_df).encode(
                y=alt.Y('exercise_short:N', sort='-x', title=None),
                x=alt.X('weight:Q', title="lbs")
            ).mark_bar(color="#29b5e8", cornerRadiusEnd=5)
            st.altair_chart(chart, use_container_width=True)
            
        with tab2:
            unique_ex = sorted(my_data['exercise'].unique())
            cols = st.columns(2)
            for i, ex in enumerate(unique_ex):
                ex_d = my_data[my_data['exercise'] == ex].sort_values('date')
                diff = ex_d.iloc[-1]['weight'] - ex_d.iloc[0]['weight']
                cols[i % 2].metric(label=ex, value=f"{ex_d.iloc[-1]['weight']} lbs", delta=f"{diff} lbs")
                
        with tab3:
            all_my_ex = sorted(my_data['exercise'].unique().tolist())
            filter_ex = st.selectbox("종목 필터", ["전체 보기"] + all_my_ex)
            display_df = my_data.sort_values(by='date', ascending=False)
            if filter_ex != "전체 보기":
                display_df = display_df[display_df['exercise'] == filter_ex]
            
            for idx, row in display_df.iterrows():
                with st.expander(f"📅 {row['date']} | {row['exercise']} | {row['weight']} lbs"):
                    e_col1, e_col2 = st.columns(2)
                    new_w = e_col1.number_input("중량", value=float(row['weight']), key=f"edit_w_{idx}")
                    new_m = e_col2.text_input("메모", value=str(row['memo']), key=f"edit_m_{idx}")
                    if st.button("저장", key=f"btn_s_{idx}"):
                        df.at[idx, 'weight'], df.at[idx, 'memo'] = new_w, new_m
                        conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=df)
                        st.rerun()
                    if st.button("삭제", key=f"btn_d_{idx}"):
                        conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=df.drop(idx))
                        st.rerun()

    # --- 8. 오늘의 기록 업데이트 ---
    st.divider()
    st.subheader("💪 오늘의 기록 업데이트")
    save_exercise = st.selectbox("종목 선택", exercise_list, key="final_save_ex")
    ex_record = my_data[my_data['exercise'] == save_exercise]
    prev_max = float(ex_record['weight'].max()) if not ex_record.empty else 0.0

    if prev_max > 0:
        st.markdown(f"💡 기존 최고: **{prev_max} lbs**")
        with st.expander("📊 훈련 무게 계산기"):
            html_rows = "".join([f"<div style='display:flex;justify-content:space-between;padding:5px;border-bottom:1px solid #eee;'><b>{p}%</b><span style='color:#29b5e8;'>{round((prev_max*p/100)/2.5)*2.5} lbs</span></div>" for p in range(50, 101, 5)])
            st.markdown(f"<div style='background:#f9f9f9;padding:10px;border-radius:10px;'>{html_rows}</div>", unsafe_allow_html=True)

    with st.form("update_form"):
        new_weight = st.number_input("성공 중량 (lbs)", value=prev_max, step=5.0)
        new_memo = st.text_input("메모", placeholder="컨디션 등")
        if st.form_submit_button("🔥 기록 저장하기", use_container_width=True):
            if new_weight > 0:
                kst_now = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d")
                user_rows = df[df['name'] == st.session_state.user_name]
                final_pw = f"'{str(user_rows.iloc[-1]['password']).replace("'", "")}" if not user_rows.empty else st.session_state.get('temp_pw', "'0000")
                
                new_row = pd.DataFrame([{"name": st.session_state.user_name, "exercise": save_exercise, "weight": new_weight, "date": kst_now, "password": final_pw, "gender": st.session_state.user_gender, "memo": new_memo}])
                conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=pd.concat([df, new_row], ignore_index=True))
                st.balloons()
                st.rerun()

st.markdown("<br><a href='#link_to_top' style='text-decoration:none;'><button style='width:100%; border-radius:10px; border:1px solid #ddd; background-color:#f9f9f9; padding:10px;'>🔝 맨 위로 가기</button></a>", unsafe_allow_html=True)

# --- 9. 관리자 모드 ---
with st.expander("🛠️ Admin"):
    if st.text_input("Key", type="password") == "5207":
        st.dataframe(df)

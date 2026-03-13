import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import time

# 0. 구글 시트 URL 설정 (본인의 시트 URL로 반드시 교체!)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvXdBZjgmUUq1Mw1UE5LucjPp4K8/edit"

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="centered")

# --- 서수(Ordinal) 변환 함수 ---
def get_ordinal(n):
    if 11 <= n % 100 <= 13: suffix = 'th'
    else: suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

# --- 종목 및 단축어 설정 ---
exercise_list = [
    "Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", 
    "Deadlift", "Back Squat", "Shoulder Press",
    "Thruster", "Bench Press", "Jerk", "Overhead Squat"
]
rename_map = {
    "Power Clean": "P.Clean", "Squat Clean": "S.Clean",
    "Power Snatch": "P.Snatch", "Squat Snatch": "S.Snatch",
    "Deadlift": "Dead", "Back Squat": "B.Squat",
    "Shoulder Press": "S.Press", "Thruster": "Thrust",
    "Bench Press": "Bench", "Jerk": "Jerk",
    "Overhead Squat": "OHS"
}

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def get_full_data():
    try:
        raw_df = conn.read(spreadsheet=SHEET_URL, worksheet="sheet1", ttl=0)
        if raw_df is None or raw_df.empty:
            return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo'])
        raw_df = raw_df.fillna('')
        for col in ['name', 'exercise', 'gender']:
            if col in raw_df.columns: raw_df[col] = raw_df[col].astype(str).str.strip()
        if 'weight' in raw_df.columns:
            raw_df['weight'] = pd.to_numeric(raw_df['weight'], errors='coerce').fillna(0)
        return raw_df
    except Exception as e:
        st.error(f"기록 로드 실패: {e}")
        return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo'])

def get_comments():
    try:
        c_df = conn.read(spreadsheet=SHEET_URL, worksheet="comments", ttl=0)
        return c_df if c_df is not None else pd.DataFrame(columns=['name', 'comment', 'date'])
    except:
        return pd.DataFrame(columns=['name', 'comment', 'date'])

# 데이터 불러오기
df = get_full_data()
comments_df = get_comments()

# 세션 상태 초기화
if 'is_auth' not in st.session_state:
    st.session_state.update({'is_auth': False, 'user_name': "", 'user_gender': "남성"})

st.markdown("<div id='link_to_top'></div>", unsafe_allow_html=True)
st.title("🏋️ 1RM을 기억해")

# --- 3. 로그인 상태 레이아웃 ---
if st.session_state.is_auth:
    col_welcome, col_logout = st.columns([3, 1])
    col_welcome.subheader(f"👋 {st.session_state.user_name}님")
    if col_logout.button("로그아웃", use_container_width=True):
        st.session_state.is_auth = False
        st.rerun()
    st.divider()

# --- 4. 실시간 전체 랭킹 ---
st.subheader("🏆 박스 실시간 랭킹 (전체)")
selected_rank_exercise = st.selectbox("랭킹 종목 선택", exercise_list, index=0)
rank_df = df[df['exercise'] == selected_rank_exercise].copy()

with st.expander(f"🔥 {selected_rank_exercise} 전체 순위 보기", expanded=True):
    if not rank_df.empty:
        best_rank_df = rank_df.sort_values('weight', ascending=False).drop_duplicates('name')
        m_data = best_rank_df[best_rank_df['gender'] == "남성"].sort_values('weight', ascending=False)
        f_data = best_rank_df[best_rank_df['gender'] == "여성"].sort_values('weight', ascending=False)
        
        max_rows = max(len(m_data), len(f_data))
        html_code = f"""
        <table style="width:100%; border-collapse: collapse; font-size: 0.8rem; table-layout: fixed;">
            <thead><tr style="border-bottom: 1px solid #444;"><th style="padding:5px;">♂️ Male</th><th style="padding:5px;">♀️ Female</th></tr></thead>
            <tbody>
        """
        for i in range(max_rows):
            m_col = f"<td>{get_ordinal(i+1)} {m_data.iloc[i]['name']} <b>{int(m_data.iloc[i]['weight'])}</b></td>" if i < len(m_data) else "<td>-</td>"
            f_col = f"<td>{get_ordinal(i+1)} {f_data.iloc[i]['name']} <b>{int(f_data.iloc[i]['weight'])}</b></td>" if i < len(f_data) else "<td>-</td>"
            html_code += f"<tr>{m_col}{f_col}</tr>"
        st.markdown(html_code + "</tbody></table>", unsafe_allow_html=True)
    else:
        st.write("첫 주인공이 되어보세요!")

st.divider()

# --- 5. 실시간 응원 댓글 ---
st.subheader("💬 응원 한마디")
if st.session_state.is_auth:
    with st.form(key="comment_form", clear_on_submit=True):
        col_c1, col_c2 = st.columns([4, 1])
        new_comment = col_c1.text_input(f"{st.session_state.user_name}님, 한마디!", placeholder="응원의 메시지")
        if col_c2.form_submit_button("등록") and new_comment:
            kst_now = (datetime.now() + timedelta(hours=9)).strftime("%m/%d %H:%M")
            new_c = pd.DataFrame([{"name": st.session_state.user_name, "comment": new_comment, "date": kst_now}])
            conn.update(spreadsheet=SHEET_URL, worksheet="comments", data=pd.concat([comments_df, new_c], ignore_index=True))
            st.rerun()

if not comments_df.empty:
    with st.expander("최근 댓글 보기", expanded=True):
        for idx, row in comments_df.sort_index(ascending=False).head(10).iterrows():
            c_c1, c_c2 = st.columns([5, 1])
            c_c1.markdown(f"**{row['name']}** <small style='color:gray;'>{row['date']}</small>", unsafe_allow_html=True)
            c_c1.info(row['comment'])
            if st.session_state.is_auth and st.session_state.user_name == row['name']:
                if c_c2.button("🗑️", key=f"del_{idx}"):
                    conn.update(spreadsheet=SHEET_URL, worksheet="comments", data=comments_df.drop(idx))
                    st.rerun()

st.divider()

# --- 6. 사용자 인증 (로그인/가입) ---
if not st.session_state.is_auth:
    st.subheader("👤 사용자 인증")
    mode = st.radio("로그인 방식", ["기존 사용자", "신규 등록"], horizontal=True)
    if mode == "기존 사용자":
        u_list = sorted(df['name'].unique().tolist()) if not df.empty else []
        sel_n = st.selectbox("이름 선택", ["선택하세요"] + u_list)
        pw_i = st.text_input("비밀번호", type="password")
        if st.button("로그인", use_container_width=True) and sel_n != "선택하세요":
            u_row = df[df['name'] == sel_n].iloc[-1]
            if pw_i.strip() == str(u_row['password']).replace("'", ""):
                st.session_state.update({'is_auth': True, 'user_name': sel_n, 'user_gender': u_row['gender']})
                st.rerun()
            else: st.error("비밀번호 불일치")
    else:
        n_col1, n_col2 = st.columns(2)
        n_n = n_col1.text_input("새 이름")
        n_g = n_col2.radio("성별", ["남성", "여성"], horizontal=True)
        n_p = st.text_input("비밀번호 설정", type="password")
        if st.button("등록 및 로그인", use_container_width=True) and n_n and n_p:
            new_u = pd.DataFrame([{"name": n_n, "exercise": "Back Squat", "weight": 0, "date": datetime.now().strftime("%Y-%m-%d"), "password": f"'{n_p}", "gender": n_g, "memo": "신규가입"}])
            conn.update(spreadsheet=SHEET_URL, worksheet="sheet1", data=pd.concat([df, new_u], ignore_index=True))
            st.session_state.update({'is_auth': True, 'user_name': n_n, 'user_gender': n_g})
            st.rerun()

# --- 7. 개인 차트 및 상세 기록 ---
if st.session_state.is_auth:
    my_data = df[df['name'] == st.session_state.user_name].copy()
    if not my_data.empty:
        st.subheader(f"📊 {st.session_state.user_name}님의 최고 기록")
        chart_df = my_data.sort_values('weight', ascending=False).drop_duplicates('exercise').copy()
        chart_df['exercise_short'] = chart_df['exercise'].map(rename_map).fillna(chart_df['exercise'])
        
        base = alt.Chart(chart_df).encode(y=alt.Y('exercise_short:N', sort='-x', title=None), x=alt.X('weight:Q', title="lbs"))
        st.altair_chart(base.mark_bar(color="#29b5e8") + base.mark_text(align='right', dx=-5, color='white').encode(text='weight:Q'), use_container_width=True)
        
        with st.expander("📋 상세 기록 조회"):
            sel_ex = st.selectbox("종목 필터", ["전체 보기"] + sorted(my_data['exercise'].unique().tolist()))
            disp = my_data if sel_ex == "전체 보기" else my_data[my_data['exercise'] == sel_ex]
            st.dataframe(disp[['date', 'exercise', 'weight', 'memo']].sort_values('date', ascending=False), hide_index=True, use_container_width=True)

    st.divider()

    # --- 8. 오늘 기록 저장 ---
    st.subheader("💪 오늘 기록 업데이트")
    save_ex = st.selectbox("종목 선택", exercise_list)
    p_max = float(my_data[my_data['exercise']==save_ex]['weight'].max()) if not my_data[my_data['exercise']==save_ex].empty else 0.0
    
    if p_max > 0:
        st.info(f"💡 기존 최고: {p_max} lbs")
        with st.expander("📊 퍼센트별 중량 확인"):
            p_cols = st.columns(3)
            for i, p in enumerate(range(50, 101, 5)):
                p_cols[i%3].metric(f"{p}%", f"{round((p_max*p/100)/2.5)*2.5} lb")

    n_w = st.number_input("오늘의 중량 (lbs)", value=p_max, step=5.0)
    n_m = st.text_input("메모 (오늘의 컨디션 등)")
    if st.button("🏋️ 새로운 기록 저장", use_container_width=True):
        u_data = df[df['name'] == st.session_state.user_name]
        f_pw = f"'{str(u_data.iloc[-1]['password']).replace("'", "")}" if not u_data.empty else "'0000"
        new_r = pd.DataFrame([{"name": st.session_state.user_name, "exercise": save_ex, "weight": n_w, "date": (datetime.now()+timedelta(hours=9)).strftime("%Y-%m-%d"), "password": f_pw, "gender": st.session_state.user_gender, "memo": n_m}])
        conn.update(spreadsheet=SHEET_URL, worksheet="sheet1", data=pd.concat([df, new_r], ignore_index=True))
        st.balloons(); time.sleep(1); st.rerun()

    st.markdown("<br><a href='#link_to_top' style='text-decoration:none;'><button style='width:100%; border-radius:10px; border:1px solid #ddd; background-color:#f9f9f9; padding:10px; cursor:pointer;'>🔝 맨 위로 가기</button></a>", unsafe_allow_html=True)

# --- 9. 관리자 모드 ---
with st.expander("🛠️ Admin"):
    if st.text_input("Key", type="password") == "5207": st.dataframe(df)

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import time

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="centered")

# --- 서수(Ordinal) 변환 함수 ---
def get_ordinal(n):
    if 11 <= n % 100 <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

# --- 종목 및 단축어 설정 ---
exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press", "Thruster", "Bench Press", "Jerk", "Overhead Squat"]
rename_map = {"Power Clean": "P.Clean", "Squat Clean": "S.Clean", "Power Snatch": "P.Snatch", "Squat Snatch": "S.Snatch", "Deadlift": "Dead", "Back Squat": "B.Squat", "Shoulder Press": "S.Press", "Thruster": "Thrust", "Bench Press": "Bench", "Jerk": "Jerk", "Overhead Squat": "OHS"}

# 2. 구글 시트 설정 (CSV 직접 호출 방식 적용)
SHEET_ID = "1ekqS81gko96DVkrFsBkg2-bQiF3oAcHkXd02oHJQ1R4"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
conn = st.connection("gsheets", type=GSheetsConnection)

def get_full_data():
    try:
        # [핵심 변경] CSV 직접 호출 방식으로 404 방지
        csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Sheet1"
        raw_df = pd.read_csv(csv_url)
        
        if raw_df is None or raw_df.empty:
            return pd.DataFrame(columns=['name','exercise','weight','date','password','gender','memo'])

        # 컬럼 보정 및 기본값 채우기
        required_cols = {'password': '0000', 'gender': '남성', 'memo': ''}
        for col, default in required_cols.items():
            if col not in raw_df.columns:
                raw_df[col] = default
        return raw_df
    except Exception as e:
        # 실패 시 라이브러리 방식 재시도
        try: return conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1", ttl=0)
        except: return pd.DataFrame(columns=['name','exercise','weight','date','password','gender','memo'])

def get_comments():
    try:
        # [핵심 변경] CSV 직접 호출 방식
        csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=comments"
        c_df = pd.read_csv(csv_url)
        return c_df if c_df is not None else pd.DataFrame(columns=['name','comment','date'])
    except:
        try: return conn.read(spreadsheet=SHEET_URL, worksheet="comments", ttl=0)
        except: return pd.DataFrame(columns=['name','comment','date'])

df = get_full_data()
comments_df = get_comments()

# --- 세션 상태 초기화 ---
if 'is_auth' not in st.session_state:
    st.session_state.update({'is_auth': False, 'user_name': "", 'user_gender': "남성"})

st.markdown("<div id='link_to_top'></div>", unsafe_allow_html=True)
st.title("🏋️ 1RM을 기억해")

# --- 3. 최상단 환영 메시지 및 로그아웃 ---
if st.session_state.is_auth:
    col_welcome, col_refresh, col_logout = st.columns([2, 1, 1])
    col_welcome.markdown(f"👋 **{st.session_state.user_name}**님")
    if col_refresh.button("🔄 갱신", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    if col_logout.button("로그아웃", use_container_width=True):
        st.session_state.is_auth = False
        st.rerun()
    st.divider()

# --- 4. 실시간 전체 랭킹 ---
st.subheader("🏆 박스 실시간 랭킹 (전체)")
selected_rank_exercise = st.selectbox("랭킹 종목 선택", exercise_list, index=0)

if not df.empty and 'weight' in df.columns:
    rank_df = df[df['exercise'] == selected_rank_exercise].copy()
    rank_df['weight'] = pd.to_numeric(rank_df['weight'], errors='coerce')
    best_rank_df = rank_df.sort_values('weight', ascending=False).drop_duplicates('name')

    with st.expander(f"🔥 {selected_rank_exercise} 전체 순위 보기", expanded=True):
        if not best_rank_df.empty:
            m_data = best_rank_df[best_rank_df['gender'] == "남성"].sort_values('weight', ascending=False)
            f_data = best_rank_df[best_rank_df['gender'] == "여성"].sort_values('weight', ascending=False)
            max_rows = max(len(m_data), len(f_data))
            
            html_code = '<table style="width:100%; border-collapse: collapse; font-size: 0.8rem; table-layout: fixed;"><thead><tr style="border-bottom: 1px solid #444;"><th style="text-align: left; padding: 5px;">♂️ Male</th><th style="text-align: left; padding: 5px;">♀️ Female</th></tr></thead><tbody>'
            for i in range(max_rows):
                m_col = f"<td>{get_ordinal(i+1)} {m_data.iloc[i]['name']} <b>{m_data.iloc[i]['weight']}</b></td>" if i < len(m_data) else "<td>-</td>"
                f_col = f"<td>{get_ordinal(i+1)} {f_data.iloc[i]['name']} <b>{f_data.iloc[i]['weight']}</b></td>" if i < len(f_data) else "<td>-</td>"
                html_code += f"<tr>{m_col}{f_col}</tr>"
            st.markdown(html_code + "</tbody></table>", unsafe_allow_html=True)
else:
    st.info("데이터를 불러오는 중이거나 기록이 없습니다.")

st.divider()

# --- 5. 실시간 응원 한마디 ---
st.subheader("💬 실시간 응원 한마디")
if st.session_state.is_auth:
    with st.form(key="comment_form_v5", clear_on_submit=True):
        col_c1, col_c2 = st.columns([4, 1])
        new_comment = col_c1.text_input(f"{st.session_state.user_name}님, 한마디!", placeholder="오늘 컨디션 최고! 🔥")
        if col_c2.form_submit_button("등록") and new_comment:
            kst_now = (datetime.now() + timedelta(hours=9)).strftime("%m/%d %H:%M")
            new_c_row = pd.DataFrame([{"name": st.session_state.user_name, "comment": new_comment, "date": kst_now}])
            conn.update(spreadsheet=SHEET_URL, worksheet="comments", data=pd.concat([comments_df, new_c_row], ignore_index=True))
            st.rerun()

if not comments_df.empty:
    with st.expander("📂 최근 응원 메시지", expanded=True):
        for idx, row in comments_df.sort_index(ascending=False).head(10).iterrows():
            st.markdown(f"<div style='margin-bottom: 5px; border-bottom: 1px solid rgba(128,128,128,0.2);'><span style='color: #29b5e8; font-weight:bold;'>{row['name']}</span> <small style='color:#888;'>{row['date']}</small><br>{row['comment']}</div>", unsafe_allow_html=True)

st.divider()

# --- 6. 사용자 인증 (비밀번호 강제 확인 모드) ---
if not st.session_state.is_auth:
    st.subheader("👤 사용자 인증")
    input_mode = st.radio("로그인 방식", ["기존 사용자", "신규 등록"], horizontal=True)
    
    if input_mode == "기존 사용자":
        if not df.empty and 'name' in df.columns:
            user_list = sorted(df['name'].dropna().astype(str).str.strip().unique().tolist())
        else:
            user_list = []
        
        selected_name = st.selectbox("이름 선택", options=user_list, index=None, placeholder="이름을 선택하세요")
        
        if selected_name:
            pw_input = st.text_input("비밀번호", type="password")
            if st.button("로그인", use_container_width=True):
                # 1. 이름으로 해당 사용자의 모든 행 찾기
                user_rows = df[df['name'].astype(str).str.strip() == selected_name]
                
                if not user_rows.empty:
                    # 2. 가장 마지막에 저장된 비밀번호 가져오기
                    raw_val = user_rows.iloc[-1]['password']
                    
                    # 3. 모든 변수 제거하고 순수 문자열 비교 (숫자든 문자든 상관없음)
                    # 5207.0 -> 5207 로 바꾸는 가장 강력한 방법
                    clean_sheet_pw = str(raw_val).replace("'", "").strip()
                    if clean_sheet_pw.endswith('.0'):
                        clean_sheet_pw = clean_sheet_pw[:-2]
                    
                    user_entered_pw = pw_input.strip()

                    # 4. 비교 및 결과 표시
                    if user_entered_pw == clean_sheet_pw:
                        st.session_state.update({
                            'is_auth': True, 
                            'user_name': selected_name, 
                            'user_gender': user_rows.iloc[-1]['gender']
                        })
                        st.success(f"로그인 성공! 환영합니다.")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        # 💥 틀렸을 때만 비밀번호 힌트를 빨간 박스로 보여줍니다.
                        st.error("비밀번호가 일치하지 않습니다!")
                        st.warning(f"시스템이 시트에서 찾은 [{selected_name}]님의 비밀번호는 **{clean_sheet_pw}** 입니다. 똑같이 입력해 보세요.")
                else:
                    st.error("사용자를 찾을 수 없습니다. (데이터 로딩 오류)")
    else:
        # 신규 등록
        reg_col1, reg_col2 = st.columns(2)
        new_name = reg_col1.text_input("새 이름")
        new_gender = reg_col2.radio("성별", ["남성", "여성"], horizontal=True)
        new_pw = st.text_input("비밀번호 설정", type="password")
        if st.button("등록 및 로그인", use_container_width=True) and new_name and new_pw:
            st.session_state.update({'is_auth': True, 'user_name': new_name.strip(), 'user_gender': new_gender, 'temp_pw': f"'{new_pw}"})
            st.rerun()


# --- 7 & 8. 개인 분석 및 데이터 입력 (로그인 후) ---
if st.session_state.is_auth:
    my_data = df[df['name'] == st.session_state.user_name].copy()
    my_data['weight'] = pd.to_numeric(my_data['weight'], errors='coerce')
    
    tab1, tab2, tab3 = st.tabs(["🏆 최고 기록", "📈 성장률", "📋 히스토리"])
    with tab1:
        if not my_data.empty:
            chart_df = my_data.sort_values('weight', ascending=False).drop_duplicates('exercise')
            chart_df['ex_short'] = chart_df['exercise'].map(rename_map).fillna(chart_df['exercise'])
            st.altair_chart(alt.Chart(chart_df).mark_bar(color="#29b5e8").encode(y=alt.Y('ex_short:N', sort='-x'), x='weight:Q'), use_container_width=True)
    with tab2:
        for ex in sorted(my_data['exercise'].unique()):
            ex_d = my_data[my_data['exercise']==ex].sort_values('date')
            st.metric(ex, f"{ex_d.iloc[-1]['weight']} lbs", f"{ex_d.iloc[-1]['weight'] - ex_d.iloc[0]['weight']} lbs")
    with tab3:
        for idx, row in my_data.sort_values('date', ascending=False).iterrows():
            with st.expander(f"📅 {row['date']} | {row['exercise']} | {row['weight']}lb"):
                if st.button("삭제", key=f"del_{idx}"):
                    conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=df.drop(idx))
                    st.rerun()

    st.divider()
    st.subheader("💪 오늘의 기록 업데이트")
    save_ex = st.selectbox("종목", exercise_list)
    p_max = float(my_data[my_data['exercise']==save_ex]['weight'].max()) if not my_data[my_data['exercise']==save_ex].empty else 0.0
    
    if p_max > 0:
        with st.expander("📊 훈련 무게 계산기"):
            calc_html = "".join([f"<div style='display:flex;justify-content:space-between;'><b>{p}%</b> <span>{round((p_max*p/100)/2.5)*2.5} lbs</span></div>" for p in range(50, 101, 5)])
            st.markdown(f"<div style='background:#f1f1f1;padding:10px;border-radius:5px;'>{calc_html}</div>", unsafe_allow_html=True)

    with st.form("record_form"):
        new_w = st.number_input("중량(lbs)", value=p_max)
        new_m = st.text_input("메모")
        if st.form_submit_button("🔥 저장"):
            kst = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d")
            u_rows = df[df['name'] == st.session_state.user_name]
            f_pw = f"'{str(u_rows.iloc[-1]['password']).replace('\'','')}" if not u_rows.empty else st.session_state.get('temp_pw', "'0000")
            new_r = pd.DataFrame([{"name": st.session_state.user_name, "exercise": save_ex, "weight": new_w, "date": kst, "password": f_pw, "gender": st.session_state.user_gender, "memo": new_m}])
            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=pd.concat([df, new_r], ignore_index=True))
            st.balloons(); st.rerun()

# --- 9. Admin ---
with st.expander("🛠️ Admin"):
    if st.text_input("Key", type="password") == "5207": st.dataframe(df)

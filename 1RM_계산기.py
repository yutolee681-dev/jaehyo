import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import altair as alt

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="centered")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def get_full_data():
    try:
        raw_df = conn.read(worksheet="sheet1", ttl=0)
        if raw_df is None or raw_df.empty:
            return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password'])
        if 'password' not in raw_df.columns:
            raw_df['password'] = "0000"
        return raw_df
    except Exception:
        return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password'])

df = get_full_data()

st.title("🏋️ 1RM을 기억해!!")

# --- [위치 조정] 3. 로그인 및 개인 기록 대시보드 (최상단) ---
st.subheader("👤 사용자 인증 및 기록 확인")
user_list = sorted(df['name'].dropna().unique().tolist()) if not df.empty else []

# 로그인 섹션
col1, col2 = st.columns([1, 1])
with col1:
    input_mode = st.radio("로그인 방식", ["기존 사용자", "신규 등록"], horizontal=True)
with col2:
    if input_mode == "기존 사용자":
        selected_name = st.selectbox("이름 선택", ["선택하세요"] + user_list)
        user_name = selected_name if selected_name != "선택하세요" else ""
    else:
        user_name = st.text_input("이름 입력", placeholder="예: 재효")

# 비밀번호 및 차트 노출
if user_name:
    pw_input = st.text_input("비밀번호", type="password", key="auth_main")
    
    user_rows = df[df['name'] == user_name]
    is_auth = False

    if not user_rows.empty:
        # 비밀번호 검증 로직 (숫자/문자 호환)
        try:
            raw_pw = user_rows.iloc[0]['password']
            stored_pw = str(int(float(raw_pw))).strip()
        except:
            stored_pw = str(user_rows.iloc[0]['password']).strip()
        
        if pw_input.strip() == stored_pw:
            is_auth = True
            st.success(f"🔓 {user_name}님 환영합니다!")
            
            # 개인 차트 바로 보여주기
            my_data = user_rows.copy()
            chart_df = my_data[['exercise', 'weight']].sort_values(by='weight', ascending=False)
            chart_df.columns = ['종목', '기록']
            
            personal_chart = alt.Chart(chart_df).mark_bar(color="#29b5e8").encode(
                x=alt.X('종목:N', sort='-y', axis=alt.Axis(labelAngle=0)),
                y=alt.Y('기록:Q', title="중량 (lbs)")
            ).properties(height=300)
            st.altair_chart(personal_chart, use_container_width=True)
        elif pw_input != "":
            st.error("비밀번호가 틀렸습니다.")

st.divider()

# --- 4. 강도별 가이드 및 기록 입력 (중단/하단) ---
if user_name and (input_mode == "신규 등록" or (input_mode == "기존 사용자" and is_auth)):
    st.subheader("💪 오늘의 운동 기록")
    
    exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
    exercise = st.selectbox("종목 선택", exercise_list)
    
    # 해당 종목 기존 기록 찾기
    ex_record = df[(df['name'] == user_name) & (df['exercise'] == exercise)]
    current_pr = float(pd.to_numeric(ex_record['weight'], errors='coerce').max()) if not ex_record.empty else 0.0
    
    if current_pr > 0:
        st.info(f"💡 현재 {exercise} PR: {current_pr} lbs")
        
        # 강도별 가이드 바로 보여주기
        st.write(f"📊 {exercise} 강도별 가이드")
        g_cols = st.columns(3)
        for i, p in enumerate([50, 70, 80, 85, 90, 100]):
            with g_cols[i % 3]:
                calc_w = round((current_pr * p / 100) / 2.5) * 2.5
                st.metric(f"{p}%", f"{calc_w} lbs")
    
    st.divider()
    
    # 신규 기록 입력
    new_weight = st.number_input("새로운 기록 입력 (lbs)", value=0.0, step=5.0)
    
    if input_mode == "신규 등록":
        new_user_pw = st.text_input("새 비번 설정", type="password")

    if st.button("🏋️ 기록 저장하기"):
        # 저장 로직 (이전과 동일)
        current_date = datetime.now().strftime("%Y-%m-%d")
        if input_mode == "신규 등록":
            final_pw = new_user_pw.strip()
        else:
            final_pw = stored_pw
            
        new_record = pd.DataFrame([{"name": user_name, "exercise": exercise, "weight": new_weight, "date": current_date, "password": final_pw}])
        updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
        
        conn.update(worksheet="sheet1", data=updated_df[['name', 'exercise', 'weight', 'date', 'password']])
        st.balloons()
        st.success("기록이 업데이트되었습니다!")
        st.rerun()

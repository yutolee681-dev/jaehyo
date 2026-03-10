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

# --- 3. 사용자 인증 및 개인 기록 대시보드 (최상단) ---
st.subheader("👤 사용자 인증 및 기록 확인")
user_list = sorted(df['name'].dropna().unique().tolist()) if not df.empty else []

col_login, col_pw = st.columns([1, 1])

with col_login:
    input_mode = st.radio("로그인 방식", ["기존 사용자", "신규 등록"], horizontal=True)
    if input_mode == "기존 사용자":
        selected_name = st.selectbox("이름 선택", ["선택하세요"] + user_list)
        user_name = selected_name if selected_name != "선택하세요" else ""
    else:
        user_name = st.text_input("이름 입력", placeholder="예: 재효")

is_auth = False
stored_pw = "0000"

with col_pw:
    if user_name:
        pw_input = st.text_input("비밀번호", type="password", key="auth_main")
        user_rows = df[df['name'] == user_name]
        
        if not user_rows.empty:
            try:
                raw_pw = user_rows.iloc[0]['password']
                stored_pw = str(int(float(raw_pw))).strip()
            except:
                stored_pw = str(user_rows.iloc[0]['password']).strip()
            
            if pw_input.strip() == stored_pw:
                is_auth = True
                st.success(f"🔓 {user_name}님 확인됨")
            elif pw_input != "":
                st.error("비밀번호 불일치")

# 인증 성공 시 차트 출력
if is_auth:
    my_data = df[df['name'] == user_name].copy()
    chart_df = my_data[['exercise', 'weight']].sort_values(by='weight', ascending=False)
    chart_df.columns = ['종목', '기록']
    
    personal_chart = alt.Chart(chart_df).mark_bar(color="#29b5e8").encode(
        x=alt.X('종목:N', sort='-y', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('기록:Q', title="중량 (lbs)")
    ).properties(height=250)
    st.altair_chart(personal_chart, use_container_width=True)

st.divider()

# --- 4. 강도별 가이드 및 기록 입력 (중단/하단) ---
if user_name and (input_mode == "신규 등록" or is_auth):
    st.subheader("💪 오늘의 운동 및 가이드")
    
    exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
    exercise = st.selectbox("종목 선택", exercise_list)
    
    # 해당 종목 기존 기록 확인
    ex_record = df[(df['name'] == user_name) & (df['exercise'] == exercise)]
    current_pr = float(pd.to_numeric(ex_record['weight'], errors='coerce').max()) if not ex_record.empty else 0.0
    
    # 📊 강도별 가이드 (3열 구성)
    if current_pr > 0:
        st.info(f"💡 현재 {exercise} PR: {current_pr} lbs")
        st.write(f"🔢 **{exercise}** 강도별 계산기")
        
        # 3열 배치를 위한 컬럼 생성
        percents = [50, 60, 70, 75, 80, 85, 90, 95, 100]
        g_cols = st.columns(3) # 3줄(3열)로 설정
        
        for i, p in enumerate(percents):
            with g_cols[i % 3]: # 인덱스를 3으로 나눈 나머지로 열 배치
                calc_w = round((current_pr * p / 100) / 2.5) * 2.5
                st.metric(label=f"{p}%", value=f"{calc_w} lbs")
    
    st.divider()
    
    # 🏋️ 새로운 기록 저장 섹션
    st.subheader("📝 새로운 기록 저장")
    new_weight = st.number_input("오늘 달성한 기록 (lbs)", value=0.0, step=5.0)
    
    if input_mode == "신규 등록":
        new_user_pw = st.text_input("새 비밀번호 설정 (숫자 4자리)", type="password")

    if st.button("🏋️ 기록 저장하기"):
        if new_weight <= 0:
            st.error("중량을 입력해주세요.")
        else:
            current_date = datetime.now().strftime("%Y-%m-%d")
            final_save_pw = new_user_pw.strip() if input_mode == "신규 등록" else stored_pw
            
            new_record = pd.DataFrame([{
                "name": user_name, 
                "exercise": exercise, 
                "weight": new_weight, 
                "date": current_date, 
                "password": final_save_pw
            }])
            
            # 기존 데이터 합치기 (동일 종목 업데이트)
            updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
            
            try:
                conn.update(worksheet="sheet1", data=updated_df[['name', 'exercise', 'weight', 'date', 'password']])
                st.balloons()
                st.success("성공적으로 저장되었습니다!")
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {e}")

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

# --- 3. 사용자 인증 섹션 (위아래 배치) ---
with st.container():
    st.subheader("👤 사용자 인증")
    
    # 1층: 로그인 방식 선택
    input_mode = st.radio("로그인 방식", ["기존 사용자", "신규 등록"], horizontal=True)
    
    # 2층: 이름 선택/입력
    if input_mode == "기존 사용자":
        user_list = sorted(df['name'].dropna().unique().tolist()) if not df.empty else []
        user_name = st.selectbox("등록된 이름을 선택하세요", ["선택하세요"] + user_list)
        if user_name == "선택하세요": user_name = ""
    else:
        user_name = st.text_input("이름을 입력하세요", placeholder="예: 재효")

    is_auth = False
    stored_pw = "0000"

    # 3층: 이름이 확인되면 바로 밑에 비밀번호 칸 노출
    if user_name:
        pw_input = st.text_input(
            "비밀번호를 입력하세요", 
            type="password", 
            key=f"pw_{user_name}", # 이름 변경 시 자동 초기화 핵심 로직
            placeholder="비밀번호 4자리"
        )
        
        user_rows = df[df['name'] == user_name]
        if not user_rows.empty:
            try:
                raw_pw = user_rows.iloc[0]['password']
                stored_pw = str(int(float(raw_pw))).strip()
            except:
                stored_pw = str(user_rows.iloc[0]['password']).strip()
            
            if pw_input.strip() == stored_pw:
                is_auth = True
                st.success(f"🔓 {user_name}님 인증되었습니다.")
            elif pw_input != "":
                st.error("❌ 비밀번호가 일치하지 않습니다.")

# 인증 성공 시 차트 출력
if is_auth:
    st.divider()
    my_data = df[df['name'] == user_name].copy()
    chart_df = my_data[['exercise', 'weight']].sort_values(by='weight', ascending=False)
    chart_df.columns = ['종목', '기록']
    
    st.write(f"📊 {user_name}님의 현재 1RM 현황")
    personal_chart = alt.Chart(chart_df).mark_bar(color="#29b5e8").encode(
        x=alt.X('종목:N', sort='-y', axis=alt.Axis(labelAngle=0, title=None)),
        y=alt.Y('기록:Q', title="중량 (lbs)")
    ).properties(height=250)
    
    st.altair_chart(personal_chart, use_container_width=True)

st.divider()

# --- 4. 강도별 가이드 및 기록 입력 ---
if user_name and (input_mode == "신규 등록" or is_auth):
    st.subheader("💪 오늘의 운동 및 가이드")
    
    exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
    exercise = st.selectbox("종목 선택", exercise_list)
    
    ex_record = df[(df['name'] == user_name) & (df['exercise'] == exercise)]
    current_pr = float(pd.to_numeric(ex_record['weight'], errors='coerce').max()) if not ex_record.empty else 0.0
    
    # 3열 구성 강도 가이드
    if current_pr > 0:
        st.info(f"💡 {exercise} 최고 기록: **{current_pr} lbs**")
        g_cols = st.columns(3)
        percents = [50, 60, 70, 75, 80, 85, 90, 95, 100]
        
        for i, p in enumerate(percents):
            with g_cols[i % 3]:
                calc_w = round((current_pr * p / 100) / 2.5) * 2.5
                st.metric(label=f"{p}%", value=f"{calc_w} lbs")
    
    st.divider()
    
    # 🏋️ 새로운 기록 저장
    st.subheader("📝 새로운 기록 저장")
    new_weight = st.number_input("오늘 성공한 무게 (lbs)", value=0.0, step=5.0)
    
    if input_mode == "신규 등록":
        new_user_pw = st.text_input("사용할 비밀번호 설정", type="password", key="new_pw_reg")

    if st.button("🏋️ 새로운 1RM 저장하기", use_container_width=True):
        if new_weight <= 0:
            st.error("무게를 입력해주세요.")
        elif input_mode == "신규 등록" and not new_user_pw:
            st.error("비밀번호를 설정해주세요.")
        else:
            current_date = datetime.now().strftime("%Y-%m-%d")
            final_save_pw = new_user_pw.strip() if input_mode == "신규 등록" else stored_pw
            
            new_record = pd.DataFrame([{
                "name": user_name, "exercise": exercise, "weight": new_weight, 
                "date": current_date, "password": final_save_pw
            }])
            
            updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
            
            try:
                conn.update(worksheet="sheet1", data=updated_df[['name', 'exercise', 'weight', 'date', 'password']])
                st.balloons()
                st.success("새로운 기록이 저장되었습니다! PR 경신을 축하합니다!")
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {e}")

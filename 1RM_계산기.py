import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import altair as alt
import time

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="centered")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def get_full_data():
    try:
        raw_df = conn.read(worksheet="sheet1", ttl=0)
        if raw_df is None or raw_df.empty:
            return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender'])
        # 필수 컬럼 누락 방지
        for col in ['password', 'gender']:
            if col not in raw_df.columns:
                raw_df[col] = "0000" if col == 'password' else "남성"
        return raw_df
    except Exception:
        return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender'])

df = get_full_data()

st.title("🏋️ 1RM을 기억해!!")

# --- 3. 사용자 인증 섹션 ---
with st.container():
    st.subheader("👤 사용자 인증")
    input_mode = st.radio("로그인 방식", ["기존 사용자", "신규 등록"], horizontal=True)
    
    if input_mode == "기존 사용자":
        user_list = sorted(df['name'].dropna().unique().tolist()) if not df.empty else []
        user_name = st.selectbox("이름 선택", ["선택하세요"] + user_list)
        if user_name == "선택하세요": user_name = ""
    else:
        reg_col1, reg_col2 = st.columns(2)
        with reg_col1:
            user_name = st.text_input("이름 입력", placeholder="예: 재효")
        with reg_col2:
            user_gender = st.radio("성별 선택", ["남성", "여성"], horizontal=True)

    is_auth = False
    stored_pw = "0000"
    user_gender_val = "남성" # 기본값

    if user_name:
        pw_input = st.text_input("비밀번호", type="password", key=f"pw_{user_name}", placeholder="비밀번호 4자리")
        user_rows = df[df['name'] == user_name]
        
        if not user_rows.empty:
            user_gender_val = user_rows.iloc[0]['gender']
            try:
                raw_pw = user_rows.iloc[0]['password']
                stored_pw = str(int(float(raw_pw))).strip()
            except:
                stored_pw = str(user_rows.iloc[0]['password']).strip()
            
            if pw_input.strip() == stored_pw:
                is_auth = True
                st.success(f"🔓 {user_name}({user_gender_val})님 인증되었습니다.")
            elif pw_input != "":
                st.error("❌ 비밀번호 불일치")

# 인증 성공 시 개인 차트
if is_auth:
    st.divider()
    my_data = df[df['name'] == user_name].copy()
    chart_df = my_data[['exercise', 'weight']].sort_values(by='weight', ascending=False)
    chart_df.columns = ['종목', '기록']
    
    personal_chart = alt.Chart(chart_df).mark_bar(color="#29b5e8").encode(
        x=alt.X('종목:N', sort='-y', axis=alt.Axis(labelAngle=0, title=None)),
        y=alt.Y('기록:Q', title="중량 (lbs)")
    ).properties(height=250)
    st.altair_chart(personal_chart, use_container_width=True)

st.divider()

# --- 4. 강도별 가이드 및 기록 저장 ---
if user_name and (input_mode == "신규 등록" or is_auth):
    st.subheader("💪 오늘의 운동 및 저장")
    exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
    exercise = st.selectbox("종목 선택", exercise_list)
    
    ex_record = df[(df['name'] == user_name) & (df['exercise'] == exercise)]
    prev_max = float(pd.to_numeric(ex_record['weight'], errors='coerce').max()) if not ex_record.empty else 0.0
    
    if prev_max > 0:
        st.info(f"💡 {exercise} 현재 최고 기록: **{prev_max} lbs**")
        st.write(f"🔢 **{exercise}** 강도별 가이드 (순차 정렬)")
        
        # ✨ 모바일 최적화 순차 정렬 로직 (50, 55, 60... 위에서 아래로)
        percents = [50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
        rows_per_col = (len(percents) + 2) // 3 # 3개 컬럼에 나눌 행 개수 계산
        
        g_cols = st.columns(3)
        for col_idx in range(3):
            with g_cols[col_idx]:
                start_idx = col_idx * rows_per_col
                end_idx = min(start_idx + rows_per_col, len(percents))
                for i in range(start_idx, end_idx):
                    p = percents[i]
                    calc_w = round((prev_max * p / 100) / 2.5) * 2.5
                    st.metric(label=f"{p}%", value=f"{calc_w} lbs")
    
    st.divider()
    
    # 📝 기록 저장
    new_weight = st.number_input("오늘 달성한 기록 (lbs)", value=0.0, step=5.0)
    if input_mode == "신규 등록":
        new_user_pw = st.text_input("비밀번호 설정", type="password", key="reg_pw")

    if st.button("🏋️ 새로운 1RM 저장하기", use_container_width=True):
        if new_weight <= 0:
            st.error("기록을 입력해주세요.")
        else:
            current_date = datetime.now().strftime("%Y-%m-%d")
            final_save_pw = new_user_pw.strip() if input_mode == "신규 등록" else stored_pw
            final_gender = user_gender if input_mode == "신규 등록" else user_gender_val
            
            new_record = pd.DataFrame([{
                "name": user_name, "exercise": exercise, "weight": new_weight, 
                "date": current_date, "password": final_save_pw, "gender": final_gender
            }])
            
            updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
            
            try:
                conn.update(worksheet="sheet1", data=updated_df[['name', 'exercise', 'weight', 'date', 'password', 'gender']])
                
                if new_weight > prev_max:
                    st.balloons()
                    st.header(f"🎊 NEW RECORD: {new_weight} lbs! 🎊")
                    st.subheader(f"🔥 {user_name}님, {exercise} PR 경신을 축하합니다!")
                    with st.spinner('기록 반영 중...'):
                        time.sleep(5)
                else:
                    st.success("기록이 저장되었습니다.")
                    time.sleep(1.5)
                
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {e}")

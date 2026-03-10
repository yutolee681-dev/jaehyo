import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import altair as alt
import time

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="centered")

# 2. 구글 시트 연결 및 데이터 로드
conn = st.connection("gsheets", type=GSheetsConnection)

def get_full_data():
    try:
        # 최신 데이터를 가져오기 위해 ttl=0 설정
        raw_df = conn.read(worksheet="sheet1", ttl=0)
        if raw_df is None or raw_df.empty:
            return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender'])
        
        # 필수 컬럼(비밀번호, 성별) 누락 시 기본값 채우기
        for col in ['password', 'gender']:
            if col not in raw_df.columns:
                raw_df[col] = "0000" if col == 'password' else "남성"
        return raw_df
    except Exception:
        return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender'])

df = get_full_data()

st.title("🏋️ 1RM을 기억해!!")

# --- 3. 사용자 인증 섹션 (위아래 배치) ---
with st.container():
    st.subheader("👤 사용자 인증")
    input_mode = st.radio("로그인 방식", ["기존 사용자", "신규 등록"], horizontal=True)
    
    user_name = ""
    user_gender_input = "남성" # 신규 등록용 변수 초기화
    
    if input_mode == "기존 사용자":
        user_list = sorted(df['name'].dropna().unique().tolist()) if not df.empty else []
        selected_name = st.selectbox("등록된 이름을 선택하세요", ["선택하세요"] + user_list)
        user_name = selected_name if selected_name != "선택하세요" else ""
    else:
        # 신규 등록 시 이름과 성별을 동시에 입력받음
        reg_col1, reg_col2 = st.columns(2)
        with reg_col1:
            user_name = st.text_input("새로운 이름 입력", placeholder="예: 재효")
        with reg_col2:
            user_gender_input = st.radio("성별 선택", ["남성", "여성"], horizontal=True)

    is_auth = False
    stored_pw = ""
    user_gender_val = "남성"

    # 이름이 입력/선택되면 비밀번호 칸 노출
    if user_name:
        pw_input = st.text_input(
            "비밀번호를 입력하세요", 
            type="password", 
            key=f"pw_{user_name}", # 이름 변경 시 자동 초기화
            placeholder="비밀번호 4자리"
        )
        
        # 기존 사용자 데이터 확인
        user_rows = df[df['name'] == user_name]
        
        if input_mode == "기존 사용자":
            if not user_rows.empty:
                user_gender_val = user_rows.iloc[0]['gender']
                try:
                    # 구글 시트 숫자를 문자열로 안전하게 변환
                    raw_pw = user_rows.iloc[0]['password']
                    stored_pw = str(int(float(raw_pw))).strip()
                except:
                    stored_pw = str(user_rows.iloc[0]['password']).strip()
                
                if pw_input.strip() == stored_pw:
                    is_auth = True
                    st.success(f"🔓 {user_name}({user_gender_val})님 인증되었습니다.")
                elif pw_input != "":
                    st.error("❌ 비밀번호가 일치하지 않습니다.")
        else:
            # 신규 등록 모드에서는 비밀번호 입력 자체가 인증 과정
            if pw_input:
                is_auth = True
                st.info("✨ 신규 등록 모드입니다. 아래에서 기록을 저장하면 가입이 완료됩니다.")

# 인증 성공 시 개인 기록 차트 노출
if is_auth and not df.empty:
    my_data = df[df['name'] == user_name].copy()
    if not my_data.empty:
        st.divider()
        chart_df = my_data[['exercise', 'weight']].sort_values(by='weight', ascending=False)
        chart_df.columns = ['종목', '기록']
        
        st.write(f"📊 {user_name}님의 현재 1RM 기록")
        personal_chart = alt.Chart(chart_df).mark_bar(color="#29b5e8").encode(
            x=alt.X('종목:N', sort='-y', axis=alt.Axis(labelAngle=0, title=None)),
            y=alt.Y('기록:Q', title="중량 (lbs)")
        ).properties(height=250)
        st.altair_chart(personal_chart, use_container_width=True)

st.divider()

# --- 4. 강도별 가이드 및 기록 저장 ---
if user_name and is_auth:
    st.subheader("💪 오늘의 운동 및 저장")
    exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
    exercise = st.selectbox("종목 선택", exercise_list)
    
    # 기존 최고 기록 찾기
    ex_record = df[(df['name'] == user_name) & (df['exercise'] == exercise)]
    prev_max = float(pd.to_numeric(ex_record['weight'], errors='coerce').max()) if not ex_record.empty else 0.0
    
    # 📊 모바일 최적화 강도 가이드 (순차 정렬)
    if prev_max > 0:
        st.info(f"💡 {exercise} 현재 최고 기록: **{prev_max} lbs**")
        st.write("🔢 **강도별 가이드** (50% → 100% 순차 정렬)")
        
        percents = [50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
        rows_per_col = (len(percents) + 2) // 3
        
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
    
    # 🏋️ 새로운 기록 저장
    new_weight = st.number_input("오늘 달성한 무게 (lbs)", value=0.0, step=5.0)
    
    if st.button("🏋️ 새로운 1RM 저장하기", use_container_width=True):
        if new_weight <= 0:
            st.error("무게를 정확히 입력해주세요.")
        elif not pw_input:
            st.error("비밀번호를 입력해야 저장할 수 있습니다.")
        else:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # ✨ 저장할 데이터 확정 (신규 가입 시 비밀번호 누락 방지)
            final_save_pw = pw_input.strip()
            final_gender = user_gender_input if input_mode == "신규 등록" else user_gender_val
            
            new_record = pd.DataFrame([{
                "name": user_name, 
                "exercise": exercise, 
                "weight": new_weight, 
                "date": current_date, 
                "password": final_save_pw, 
                "gender": final_gender
            }])
            
            # 기존 종목 기록이 있다면 교체, 없으면 추가
            updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
            
            try:
                # 1. 시트 업데이트 (컬럼 순서 유지)
                conn.update(worksheet="sheet1", data=updated_df[['name', 'exercise', 'weight', 'date', 'password', 'gender']])
                
                # 2. PR 축하 로직
                if new_weight > prev_max:
                    st.balloons()
                    st.header(f"🎊 NEW RECORD: {new_weight} lbs! 🎊")
                    st.subheader(f"🔥 {user_name}님, {exercise} PR 경신을 축하합니다!")
                    with st.spinner('서버에 기록을 반영 중입니다...'):
                        time.sleep(5)
                else:
                    st.success("기록이 안전하게 저장되었습니다.")
                    time.sleep(1.5)
                
                st.rerun()
            except Exception as e:
                st.error(f"❌ 저장 실패: {e}")

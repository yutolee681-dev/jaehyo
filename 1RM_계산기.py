import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import altair as alt

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="centered")

# 2. 구글 시트 연결 (오류가 났던 read_only 인자 제거)
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # 실시간 데이터 로드
    df = conn.read(ttl=0)
    if df is None or df.empty:
        df = pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password'])
    else:
        # 데이터 타입 보정 (중량 비교 시 오류 방지)
        df['weight'] = pd.to_numeric(df['weight'], errors='coerce').fillna(0)
except Exception:
    df = pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password'])

st.title("🏋️ 1RM을 기억해!!")

# --- 3. 사용자 정보 섹션 ---
st.subheader("👤 사용자 정보")
user_list = sorted(df['name'].dropna().unique().tolist()) if not df.empty else []

input_mode = st.radio("로그인 방식", ["기존 사용자 선택", "신규 사용자 등록"], horizontal=True)

user_name = ""
new_user_pw = ""

if input_mode == "기존 사용자 선택":
    if user_list:
        selected_name = st.selectbox("등록된 이름을 선택하세요", ["선택하세요"] + user_list)
        user_name = selected_name if selected_name != "선택하세요" else ""
    else:
        st.warning("등록된 사용자가 없습니다. '신규 사용자 등록'을 먼저 진행해 주세요.")
else:
    user_name = st.text_input("이름을 입력하세요", placeholder="예: 재효")
    new_user_pw = st.text_input("비밀번호 설정 (숫자 4자리 권장)", type="password")

exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
exercise = st.selectbox("운동 선택", exercise_list)

# --- 4. 기존 최고 기록 확인 (PR 체크용) ---
prev_max = 0.0
if user_name and not df.empty:
    user_exercise_data = df[(df['name'] == user_name) & (df['exercise'] == exercise)]
    if not user_exercise_data.empty:
        prev_max = float(user_exercise_data['weight'].max())
        st.info(f"💡 {user_name}님의 {exercise} 현재 최고 기록: {prev_max} lbs")

# --- 5. 중량 입력 및 저장 ---
new_weight = st.number_input(f"{exercise} 1RM 입력 (lbs)", value=0.0, step=5.0)

if st.button("기록 저장하기"):
    if not user_name:
        st.error("⚠️ 이름을 확인해 주세요!")
    elif input_mode == "신규 사용자 등록" and not new_user_pw:
        st.error("⚠️ 비밀번호 설정은 필수입니다!")
    elif new_weight <= 0:
        st.error("⚠️ 0보다 큰 중량을 입력해 주세요!")
    else:
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # 비밀번호 결정 로직
        if input_mode == "신규 사용자 등록":
            final_pw = str(new_user_pw)
        else:
            # 기존 사용자의 비밀번호 유지
            user_pw_row = df[df['name'] == user_name]['password']
            final_pw = str(user_pw_row.iloc[0]) if not user_pw_row.empty else "0000"

        # 새로운 레코드 생성
        new_record = pd.DataFrame([{
            "name": user_name, "exercise": exercise, "weight": new_weight, 
            "date": current_date, "password": final_pw
        }])
        
        # 동일 종목의 기존 데이터는 제거하고 최신 기록으로 업데이트
        updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
        
        try:
            # 구글 시트에 업데이트 (시트 이름이 '시트1'인지 꼭 확인!)
            conn.update(worksheet="시트1", data=updated_df)
            
            # 기록 경신 여부 확인 및 축하 메시지
            if prev_max > 0 and new_weight > prev_max:
                st.balloons()
                st.success(f"🎊 축하합니다!! {new_weight - prev_max}lbs 증량 성공! 새로운 기록을 경신했습니다! 🎊")
            else:
                st.success(f"저장 완료! (날짜: {current_date})")
            
            st.rerun()
        except Exception as e:
            st.error("❌ 저장 실패! 구글 시트 탭 이름이 '시트1'이 맞는지 확인해 주세요.")

st.divider()

# --- 6. 강도별 가이드 ---
if new_weight > 0:
    st.subheader(f"📊 {exercise} 강도별 가이드")
    cols = st.columns(3)
    percents = [50, 60, 70, 75, 80, 85, 90, 95, 100]
    for i, p in enumerate(percents):
        with cols[i % 3]:
            calc_w = round((new_weight * p / 100) / 2.5) * 2.5
            st.metric(label=f"{p}%", value=f"{calc_w} lbs")

# --- 7. 개인 대시보드 (글자 가로 고정 차트) ---
if user_name and input_mode == "기존 사용자 선택":
    st.divider()
    st.subheader(f"🔐 {user_name}님의 기록 확인")
    pw_check = st.text_input("비밀번호를 입력하세요", type="password", key="auth_pw")
    
    # 해당 사용자의 실제 저장된 비밀번호 확인
    user_pw_data = df[df['name'] == user_name]['password']
    correct_pw = str(user_pw_data.iloc[0]) if not user_pw_data.empty else "0000"
    
    if pw_check == correct_pw:
        st.success("🔓 확인되었습니다!")
        my_data = df[df['name'] == user_name].copy()
        if not my_data.empty:
            chart_df = my_data[['exercise', 'weight']].sort_values(by='weight', ascending=False)
            chart_df.columns = ['종목', '기록']

            # Altair 차트를 사용하여 라벨 각도를 0도로 고정
            personal_chart = alt.Chart(chart_df).mark_bar(color="#29b5e8").encode(
                x=alt.X('종목:N', sort='-y', axis=alt.Axis(labelAngle=0)),
                y=alt.Y('기록:Q', title="기록 (lbs)")
            ).properties(height=400)

            st.altair_chart(personal_chart, use_container_width=True)
            st.dataframe(chart_df, use_container_width=True, hide_index=True)
    elif pw_check != "":
        st.error("❌ 비밀번호가 틀렸습니다.")

# --- 8. 관리자 도구 ---
with st.sidebar.expander("🛠️ Admin Tools"):
    admin_pw = st.text_input("관리자 암호", type="password")
    if admin_pw == "admin777":
        target = st.selectbox("비번 초기화 유저", user_list)
        if st.button("0000으로 초기화"):
            df.loc[df['name'] == target, 'password'] = "0000"
            conn.update(worksheet="시트1", data=df)
            st.success("초기화 완료!")
            st.rerun()

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import altair as alt

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="centered")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # ttl=0으로 설정하여 실시간 데이터를 가져옵니다.
    df = conn.read(ttl=0)
    if df is None or df.empty:
        df = pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password'])
except Exception:
    df = pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password'])

st.title("🏋️ 1RM을 기억해!!")

# --- 3. 사용자 정보 섹션 ---
st.subheader("👤 사용자 정보")

# 시트에서 이름 리스트 추출
user_list = sorted(df['name'].dropna().unique().tolist()) if not df.empty else []

input_mode = st.radio("로그인 방식", ["기존 사용자 선택", "신규 사용자 등록"], horizontal=True)

user_name = ""
new_user_pw = ""

if input_mode == "기존 사용자 선택":
    if user_list:
        selected_name = st.selectbox("등록된 이름을 선택하세요", ["선택하세요"] + user_list)
        user_name = selected_name if selected_name != "선택하세요" else ""
    else:
        st.warning("등록된 사용자가 없습니다. '신규 사용자 등록'을 먼저 해주세요.")
else:
    user_name = st.text_input("이름을 입력하세요", placeholder="예: 재효")
    new_user_pw = st.text_input("초기 비밀번호 설정", type="password")

exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
exercise = st.selectbox("운동 선택", exercise_list)

# --- 4. 기존 최고 기록 확인 (PR 알림용) ---
prev_max = 0.0
if user_name:
    user_records = df[(df['name'] == user_name) & (df['exercise'] == exercise)]
    if not user_records.empty:
        prev_max = float(user_records['weight'].max())
        st.info(f"💡 {user_name}님의 {exercise} 현재 최고 기록: {prev_max} lbs")

# --- 5. 중량 입력 및 저장 ---
new_weight = st.number_input(f"{exercise} 1RM 입력 (lbs)", value=0.0, step=5.0)

if st.button("기록 저장하기"):
    if not user_name:
        st.error("⚠️ 이름을 입력해주세요!")
    elif input_mode == "신규 사용자 등록" and not new_user_pw:
        st.error("⚠️ 신규 등록 시 비밀번호 설정은 필수입니다!")
    elif new_weight <= 0:
        st.error("⚠️ 중량을 입력해주세요!")
    else:
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # 비밀번호 결정 로직
        if input_mode == "신규 사용자 등록":
            final_pw = str(new_user_pw)
        else:
            # 기존 사용자의 비밀번호 유지
            user_row = df[df['name'] == user_name]
            final_pw = str(user_row['password'].values[0]) if 'password' in df.columns else "0000"

        new_record = pd.DataFrame([{
            "name": user_name, "exercise": exercise, "weight": new_weight, 
            "date": current_date, "password": final_pw
        }])
        
        # 데이터 업데이트 (기존 동일 종목 기록 제거 후 신규 추가)
        updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
        
        try:
            conn.update(worksheet="시트1", data=updated_df)
            
            # 기록 경신 알림
            if prev_max > 0 and new_weight > prev_max:
                st.balloons()
                st.success(f"🎊 대박!! {new_weight - prev_max}lbs 증량 성공! 새로운 기록입니다! 🎊")
            else:
                st.success(f"저장 완료! (날짜: {current_date})")
            
            st.rerun()
        except Exception as e:
            st.error("❌ 구글 시트 저장 실패! 공유 설정에서 '편집자' 권한을 확인하세요.")
            st.debug(e)

st.divider()

# --- 6. 강도별 가이드 ---
if new_weight > 0:
    st.subheader(f"📊 {exercise} 강도별 가이드")
    cols = st.columns(3)
    for i, p in enumerate([50, 60, 70, 75, 80, 85, 90, 95, 100]):
        with cols[i % 3]:
            calc_w = round((new_weight * p / 100) / 2.5) * 2.5
            st.metric(label=f"{p}%", value=f"{calc_w} lbs")

# --- 7. 개인 대시보드 (비밀번호 확인) ---
if user_name and input_mode == "기존 사용자 선택":
    st.divider()
    st.subheader(f"🔐 {user_name}님의 개인 기록 확인")
    pw_input = st.text_input("비밀번호를 입력하세요", type="password")
    
    # 비밀번호 검증
    correct_pw = str(df[df['name'] == user_name]['password'].values[0]) if 'password' in df.columns else "0000"
    
    if pw_input == correct_pw:
        st.success("🔓 확인되었습니다!")
        my_data = df[df['name'] == user_name].copy()
        if not my_data.empty:
            chart_df = my_data[['exercise', 'weight']].sort_values(by='weight', ascending=False)
            chart_df.columns = ['종목', '기록']

            personal_chart = alt.Chart(chart_df).mark_bar(color="#29b5e8").encode(
                x=alt.X('종목:N', sort='-y', axis=alt.Axis(labelAngle=0)),
                y=alt.Y('기록:Q', title="중량 (lbs)")
            ).properties(height=400)

            st.altair_chart(personal_chart, use_container_width=True)
            st.dataframe(chart_df, use_container_width=True, hide_index=True)
    elif pw_input != "":
        st.error("❌ 비밀번호가 틀렸습니다.")

# --- 8. 관리자 도구 (사이드바) ---
with st.sidebar.expander("🛠️ 관리자 설정"):
    admin_pw = st.text_input("Admin Password", type="password")
    if admin_pw == "wogydi12":
        target = st.selectbox("비번 초기화 대상", user_list)
        if st.button("0000으로 초기화"):
            df.loc[df['name'] == target, 'password'] = "0000"
            conn.update(worksheet="시트1", data=df)
            st.success("초기화 완료!")
            st.rerun()

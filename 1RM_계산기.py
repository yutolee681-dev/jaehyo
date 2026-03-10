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
    df = conn.read(ttl=0)
    # 데이터가 비어있거나 컬럼이 없을 경우 초기화
    if df.empty or 'name' not in df.columns:
        df = pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password'])
except Exception:
    df = pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password'])

st.title("🏋️ 1RM을 기억해!!")

# --- 3. 사용자 정보 섹션 ---
st.subheader("👤 사용자 정보")

# 실시간 사용자 리스트 추출 (중복 제거 및 정렬)
user_list = sorted(df['name'].dropna().unique().tolist()) if not df.empty else []

input_mode = st.radio("로그인 방식", ["기존 사용자 선택", "신규 사용자 등록"], horizontal=True)

user_name = ""
new_user_pw = ""

if input_mode == "기존 사용자 선택":
    if user_list:
        selected_user = st.selectbox("등록된 이름을 선택하세요", ["선택하세요"] + user_list)
        user_name = selected_user if selected_user != "선택하세요" else ""
    else:
        st.warning("등록된 사용자가 없습니다. '신규 사용자 등록'을 먼저 진행해 주세요.")
else:
    user_name = st.text_input("이름을 입력하세요", placeholder="예: 재효")
    new_user_pw = st.text_input("사용할 비밀번호 설정", type="password")

exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
exercise = st.selectbox("운동 선택", exercise_list)

# --- 4. 기존 기록 확인 ---
prev_max_weight = 0.0
if user_name:
    user_exercise_data = df[(df['name'] == user_name) & (df['exercise'] == exercise)]
    if not user_exercise_data.empty:
        prev_max_weight = float(user_exercise_data['weight'].max())
        st.info(f"💡 {user_name}님의 {exercise} 현재 최고 기록: {prev_max_weight} lbs")

# --- 5. 중량 입력 및 저장 ---
new_weight = st.number_input(f"{exercise} 1RM 입력 (lbs)", value=0.0, step=5.0)

if st.button("기록 저장하기"):
    if not user_name:
        st.error("⚠️ 이름을 확인해 주세요!")
    elif input_mode == "신규 사용자 등록" and not new_user_pw:
        st.error("⚠️ 비밀번호를 설정해 주세요!")
    else:
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # 비밀번호 결정
        if input_mode == "신규 사용자 등록":
            final_pw = str(new_user_pw)
        else:
            final_pw = str(df[df['name'] == user_name]['password'].values[0])

        # 기록 갱신 여부 확인
        is_pr = new_weight > prev_max_weight
        
        new_record = pd.DataFrame([{
            "name": user_name, "exercise": exercise, "weight": new_weight, 
            "date": current_date, "password": final_pw
        }])
        
        # 동일 종목 기존 기록 제거 후 새 기록 추가 (최신화)
        updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
        conn.update(worksheet="시트1", data=updated_df)
        
        if is_pr and prev_max_weight > 0:
            st.balloons()
            st.success(f"🎊 대박!! {new_weight - prev_max_weight}lbs 증량 성공! 새로운 기록을 경신했습니다! 🎊")
        else:
            st.success("기록이 안전하게 저장되었습니다.")
        
        st.rerun()

st.divider()

# --- 6. 강도별 가이드 ---
if new_weight > 0:
    st.subheader(f"📊 {exercise} 강도별 가이드")
    cols = st.columns(3)
    target_percents = [50, 60, 70, 75, 80, 85, 90, 95, 100]
    for i, p in enumerate(target_percents):
        with cols[i % 3]:
            calc_w = round((new_weight * p / 100) / 2.5) * 2.5
            st.metric(label=f"{p}%", value=f"{calc_w} lbs")

# --- 7. 개인 대시보드 ---
if user_name and input_mode == "기존 사용자 선택":
    st.divider()
    st.subheader(f"🏆 {user_name}님의 개인 대시보드")
    pw_check = st.text_input("비밀번호를 입력하여 기록 보기", type="password")
    
    stored_pw = str(df[df['name'] == user_name]['password'].values[0])
    
    if pw_check == stored_pw:
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
    elif pw_check != "":
        st.error("❌ 비밀번호가 올바르지 않습니다.")

# --- 8. 관리자 도구 ---
with st.sidebar.expander("🛠️ Admin Tools"):
    admin_pw = st.text_input("Admin Password", type="password")
    if admin_pw == "admin777":
        target = st.selectbox("Reset User", user_list)
        if st.button("Reset to '0000'"):
            df.loc[df['name'] == target, 'password'] = "0000"
            conn.update(worksheet="시트1", data=df)
            st.success("초기화 완료!")
            st.rerun()

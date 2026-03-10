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
except Exception:
    df = pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password'])

st.title("🏋️ 1RM을 기억해!!")

# --- 3. 사용자 정보 섹션 ---
st.subheader("👤 사용자 정보")

user_list = sorted(df['name'].dropna().unique().tolist()) if not df.empty else []
input_mode = st.radio("로그인 방식", ["기존 사용자 선택", "신규 사용자 등록"], horizontal=True)

user_name = ""
if input_mode == "기존 사용자 선택":
    if user_list:
        selected_name = st.selectbox("등록된 이름을 선택하세요", ["선택하세요"] + user_list)
        user_name = selected_name if selected_name != "선택하세요" else ""
    else:
        st.warning("등록된 사용자가 없습니다.")
else:
    user_name = st.text_input("이름을 입력하세요", placeholder="예: 재효")
    new_user_pw = st.text_input("사용할 비밀번호 설정", type="password", help="처음 등록 시 사용할 비번입니다.")

exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
exercise = st.selectbox("운동 선택", exercise_list)

# --- 4. 기존 기록 및 5. 저장 로직 ---
if user_name:
    existing_data = df[(df['name'] == user_name) & (df['exercise'] == exercise)] if not df.empty else pd.DataFrame()
    if not existing_data.empty:
        last_record = existing_data.iloc[-1]
        st.success(f"✅ {user_name}님의 기존 기록: {last_record['weight']} lbs")

new_weight = st.number_input(f"{exercise} 1RM 입력 (lbs)", value=0.0, step=5.0)

if st.button("기록 저장하기"):
    if not user_name:
        st.error("⚠️ 이름을 입력해주세요!")
    elif input_mode == "신규 사용자 등록" and not new_user_pw:
        st.error("⚠️ 신규 등록 시 비밀번호 설정은 필수입니다!")
    else:
        current_date = datetime.now().strftime("%Y-%m-%d")
        # 신규면 입력한 비번, 기존이면 시트 데이터에서 가져옴
        final_pw = new_user_pw if input_mode == "신규 사용자 등록" else df[df['name'] == user_name]['password'].values[0]

        new_record = pd.DataFrame([{
            "name": user_name, "exercise": exercise, "weight": new_weight, 
            "date": current_date, "password": str(final_pw)
        }])
        
        updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
        conn.update(worksheet="시트1", data=updated_df)
        st.balloons()
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

# --- 7. 사용자별 비밀번호 확인 및 대시보드 ---
if user_name and input_mode == "기존 사용자 선택":
    st.divider()
    st.subheader(f"🏆 {user_name}님의 개인 기록")
    pw_check = st.text_input("본인 비밀번호를 입력하세요", type="password", key="user_pw")
    
    # 실제 비밀번호와 대조 (문자열로 변환하여 비교)
    stored_pw = str(df[df['name'] == user_name]['password'].values[0])
    
    if pw_check == stored_pw:
        st.success("🔓 인증되었습니다.")
        my_data = df[df['name'] == user_name].copy()
        chart_df = my_data[['exercise', 'weight']].sort_values(by='weight', ascending=False)
        chart_df.columns = ['종목', '기록']

        personal_chart = alt.Chart(chart_df).mark_bar(color="#29b5e8").encode(
            x=alt.X('종목:N', sort='-y', axis=alt.Axis(labelAngle=0)),
            y=alt.Y('기록:Q')
        ).properties(height=400)

        st.altair_chart(personal_chart, use_container_width=True)
        st.dataframe(chart_df, use_container_width=True, hide_index=True)
    elif pw_check != "":
        st.error("❌ 비밀번호가 틀렸습니다.")

# --- 8. [🛠️ 관리자 도구] ---
st.sidebar.divider()
with st.sidebar.expander("🛠️ 관리자 도구"):
    admin_pw = st.text_input("관리자 암호", type="password")
    if admin_pw == "admin777": # 관리자용 비밀번호 설정
        st.write("🔧 사용자 비밀번호 초기화")
        target_user = st.selectbox("대상 사용자 선택", user_list)
        if st.button("0000으로 초기화"):
            # 해당 사용자의 모든 행에서 비밀번호를 '0000'으로 업데이트
            df.loc[df['name'] == target_user, 'password'] = "0000"
            conn.update(worksheet="시트1", data=df)
            st.success(f"{target_user}님의 비밀번호가 '0000'으로 초기화되었습니다!")
            st.rerun()

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import altair as alt

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="centered")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(ttl=0)
        # 만약 시트가 완전히 비어있거나 password 컬럼이 없다면 강제로 틀을 만듭니다.
        if df is None or df.empty:
            return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password'])
        if 'password' not in df.columns:
            df['password'] = "0000" # 없는 경우 기본값 채움
        return df
    except Exception:
        return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password'])

df = load_data()

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
        st.warning("등록된 사용자가 없습니다. 신규 등록을 해주세요.")
else:
    user_name = st.text_input("이름을 입력하세요", placeholder="예: 재효")
    new_user_pw = st.text_input("비밀번호 설정", type="password")

exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
exercise = st.selectbox("운동 선택", exercise_list)

# --- 4. 최고 기록 확인 ---
prev_max = 0.0
if user_name:
    user_records = df[(df['name'] == user_name) & (df['exercise'] == exercise)]
    if not user_records.empty:
        # 숫자로 변환하여 최고점 계산
        df_temp = user_records.copy()
        df_temp['weight'] = pd.to_numeric(df_temp['weight'], errors='coerce')
        prev_max = float(df_temp['weight'].max())
        st.info(f"💡 {user_name}님의 {exercise} 현재 최고 기록: {prev_max} lbs")

# --- 5. 중량 입력 및 저장 ---
new_weight = st.number_input(f"{exercise} 1RM 입력 (lbs)", value=0.0, step=5.0)

if st.button("기록 저장하기"):
    if not user_name:
        st.error("⚠️ 이름을 입력해주세요!")
    elif input_mode == "신규 사용자 등록" and not new_user_pw:
        st.error("⚠️ 비밀번호를 설정해주세요!")
    else:
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # 비밀번호 로직
        if input_mode == "신규 사용자 등록":
            final_pw = str(new_user_pw)
        else:
            # 기존 비번 가져오기
            user_pw_row = df[df['name'] == user_name]['password']
            final_pw = str(user_pw_row.iloc[0]) if not user_pw_row.empty else "0000"

        new_record = pd.DataFrame([{
            "name": user_name, "exercise": exercise, "weight": new_weight, 
            "date": current_date, "password": final_pw
        }])
        
        # 업데이트 (동일인/동일종목 기존 데이터 필터링 후 신규 추가)
        updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
        
        try:
            # 컬럼 순서 고정 (name, exercise, weight, date, password 순서로 시트에 저장됨)
            updated_df = updated_df[['name', 'exercise', 'weight', 'date', 'password']]
            conn.update(worksheet="시트1", data=updated_df)
            
            if prev_max > 0 and new_weight > prev_max:
                st.balloons()
                st.success(f"🎊 경축! {new_weight - prev_max}lbs 증량! 기록 경신! 🎊")
            else:
                st.success("기록이 저장되었습니다.")
            st.rerun()
        except Exception as e:
            st.error("❌ 저장 실패! 구글 시트 E1 셀에 'password'가 입력되어 있는지 확인하세요.")

st.divider()

# --- 6. 강도별 가이드 ---
if new_weight > 0:
    st.subheader(f"📊 {exercise} 강도별 가이드")
    cols = st.columns(3)
    for i, p in enumerate([50, 60, 70, 75, 80, 85, 90, 95, 100]):
        with cols[i % 3]:
            calc_w = round((new_weight * p / 100) / 2.5) * 2.5
            st.metric(label=f"{p}%", value=f"{calc_w} lbs")

# --- 7. 개인 기록 차트 ---
if user_name and input_mode == "기존 사용자 선택":
    st.divider()
    st.subheader(f"🏆 {user_name}님의 개인 기록")
    pw_auth = st.text_input("비밀번호 확인", type="password")
    
    # 저장된 비번 확인
    user_pw_data = df[df['name'] == user_name]['password']
    correct_pw = str(user_pw_data.iloc[0]) if not user_pw_data.empty else "0000"
    
    if pw_auth == correct_pw:
        st.success("🔓 인증 완료")
        my_data = df[df['name'] == user_name].copy()
        my_data['weight'] = pd.to_numeric(my_data['weight'])
        chart_df = my_data[['exercise', 'weight']].sort_values(by='weight', ascending=False)
        chart_df.columns = ['종목', '기록']

        personal_chart = alt.Chart(chart_df).mark_bar(color="#29b5e8").encode(
            x=alt.X('종목:N', sort='-y', axis=alt.Axis(labelAngle=0)),
            y=alt.Y('기록:Q')
        ).properties(height=400)

        st.altair_chart(personal_chart, use_container_width=True)
    elif pw_auth != "":
        st.error("비밀번호가 틀립니다.")

# --- 8. 관리자 도구 ---
with st.sidebar.expander("🛠️ Admin"):
    admin_input = st.text_input("Admin PW", type="password")
    if admin_input == "admin777":
        target = st.selectbox("Reset User", user_list)
        if st.button("Reset to 0000"):
            df.loc[df['name'] == target, 'password'] = "0000"
            conn.update(worksheet="시트1", data=df)
            st.rerun()

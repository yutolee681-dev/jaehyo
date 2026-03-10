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
        # 실시간 데이터 로드
        raw_df = conn.read(ttl=0)
        
        # 데이터가 아예 없거나 컬럼이 비어있는 경우 초기화
        if raw_df is None or raw_df.empty:
            return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password'])
        
        # 만약 password 컬럼만 누락되었다면 추가
        if 'password' not in raw_df.columns:
            raw_df['password'] = "0000"
            
        return raw_df
    except Exception:
        return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password'])

df = get_full_data()

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
        st.warning("등록된 사용자가 없습니다. 신규 등록을 먼저 진행해 주세요.")
else:
    user_name = st.text_input("이름을 입력하세요", placeholder="예: 재효")
    new_user_pw = st.text_input("비밀번호 설정", type="password", help="처음 등록할 때 사용할 비번입니다.")

exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
exercise = st.selectbox("운동 선택", exercise_list)

# --- 4. 기존 최고 기록 확인 (PR 체크) ---
prev_max = 0.0
if user_name and not df.empty:
    user_ex_data = df[(df['name'] == user_name) & (df['exercise'] == exercise)]
    if not user_ex_data.empty:
        prev_max = float(pd.to_numeric(user_ex_data['weight']).max())
        st.info(f"💡 {user_name}님의 {exercise} 최고 기록: {prev_max} lbs")

# --- 5. 중량 입력 및 저장 ---
new_weight = st.number_input(f"{exercise} 1RM 입력 (lbs)", value=0.0, step=5.0)

if st.button("기록 저장하기"):
    if not user_name:
        st.error("⚠️ 이름을 확인해 주세요!")
    elif input_mode == "신규 사용자 등록" and not new_user_pw:
        st.error("⚠️ 비밀번호를 입력해 주세요!")
    elif new_weight <= 0:
        st.error("⚠️ 0보다 큰 중량을 입력해 주세요!")
    else:
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # 비밀번호 결정
        if input_mode == "신규 사용자 등록":
            final_pw = str(new_user_pw)
        else:
            # 기존 비번 찾기 (없으면 0000)
            user_pw_rows = df[df['name'] == user_name]['password']
            final_pw = str(user_pw_rows.iloc[0]) if not user_pw_rows.empty else "0000"

        new_record = pd.DataFrame([{
            "name": user_name, "exercise": exercise, "weight": new_weight, 
            "date": current_date, "password": final_pw
        }])
        
        # 중복 제거 및 합치기
        if not df.empty:
            updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
        else:
            updated_df = new_record
        
        try:
            # 컬럼 순서 강제 고정
            updated_df = updated_df[['name', 'exercise', 'weight', 'date', 'password']]
            # 시트 이름이 하단 탭 이름("시트1")과 일치해야 합니다.
            conn.update(worksheet="시트1", data=updated_df)
            
            if prev_max > 0 and new_weight > prev_max:
                st.balloons()
                st.success(f"🎊 PR 경신! {new_weight} lbs!! 축하합니다! 🎊")
            else:
                st.success("성공적으로 저장되었습니다.")
            st.rerun()
        except Exception as e:
            st.error(f"❌ 저장 실패: 탭 이름이 '시트1'인지 확인하세요.")
            st.info("시트 하단 탭 이름이 '시트1'이 아니라면 코드를 그 이름에 맞춰 수정해야 합니다.")

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

# --- 7. 개인 기록 대시보드 (차트 라벨 가로 고정) ---
if user_name and input_mode == "기존 사용자 선택":
    st.divider()
    st.subheader(f"🏆 {user_name}님의 개인 기록")
    pw_check = st.text_input("비밀번호 입력", type="password", key="auth_check")
    
    stored_pw = str(df[df['name'] == user_name]['password'].iloc[0]) if not df.empty and user_name in df['name'].values else "0000"
    
    if pw_check == stored_pw:
        st.success("🔓 인증되었습니다.")
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
        st.error("비밀번호가 올바르지 않습니다.")

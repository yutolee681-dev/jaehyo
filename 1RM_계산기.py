import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", layout="centered")

# 1. 구글 시트 연결 (secrets.toml 설정 기반)
conn = st.connection("gsheets", type=GSheetsConnection)

# 기존 데이터 읽어오기 (없으면 빈 데이터프레임 생성)
try:
    df = conn.read()
except:
    df = pd.DataFrame(columns=['name', 'exercise', 'weight'])

st.title("🏋️ 나의 1RM 저장소")

# 2. 사용자 입력 섹션
user_name = st.text_input("사용자 이름을 입력하세요 (예: 재효)", value="재효")
exercise_list = ["Clean", "Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
exercise = st.selectbox("운동 선택", exercise_list)

# 해당 사용자의 기존 기록 찾기
existing_data = df[(df['name'] == user_name) & (df['exercise'] == exercise)]

if not existing_data.empty:
    default_weight = float(existing_data.iloc[0]['weight'])
    st.success(f"✅ 기존 기록을 불러왔습니다: {default_weight} lbs")
else:
    default_weight = 0.0
    st.info("기록이 없습니다. 새로운 중량을 입력해 주세요.")

# 3. 중량 입력 및 저장 버튼
new_weight = st.number_input(f"{exercise} 1RM 입력 (lbs)", value=default_weight, step=5.0)

if st.button("기록 저장하기"):
    # 데이터 업데이트: 기존 기록은 지우고 새 기록 추가
    new_record = pd.DataFrame([{"name": user_name, "exercise": exercise, "weight": new_weight}])
    updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
    
    # 구글 시트에 반영
    conn.update(worksheet="시트1", data=updated_df)
    st.balloons()
    st.success(f"'{user_name}'님의 {exercise} 기록이 {new_weight}lbs로 저장되었습니다!")

st.divider()

# 4. 강도별 중량 계산 출력
if new_weight > 0:
    st.subheader(f"📊 {exercise} {new_weight}lbs 기준 강도")
    target_percents = [50, 60, 70, 75, 80, 85, 90, 95, 100]
    cols = st.columns(3)

    for i, p in enumerate(target_percents):
        with cols[i % 3]:
            # 2.5단위 반올림 (플레이트 세팅용)
            calc_w = round((new_weight * p / 100) / 2.5) * 2.5
            st.metric(label=f"{p}%", value=f"{calc_w} lbs")

st.info("💡 기록을 저장하면 다음 접속 시 자동으로 불러옵니다.")


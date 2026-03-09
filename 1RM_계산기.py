import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", layout="centered")

# 2. 구글 시트 연결 설정
conn = st.connection("gsheets", type=GSheetsConnection)

# [핵심 수정] ttl=0을 설정해야 새로고침 시 구글 시트의 최신 데이터를 즉시 가져옵니다.
try:
    df = conn.read(ttl=0)
except Exception:
    df = pd.DataFrame(columns=['name', 'exercise', 'weight'])

st.title("🏋️ 윤아게이트 1RM을 기억해!! ")

# 3. 사용자 입력 섹션
user_name = st.text_input("사용자 이름을 입력하세요 (예: 재효)", value="재효")
exercise_list = ["Clean", "Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
exercise = st.selectbox("운동 선택", exercise_list)

# 기존 기록 불러오기
if not df.empty:
    existing_data = df[(df['name'] == user_name) & (df['exercise'] == exercise)]
else:
    existing_data = pd.DataFrame()

if not existing_data.empty:
    # 가장 최근 저장된 중량을 불러옴
    default_weight = float(existing_data.iloc[-1]['weight'])
    st.success(f"✅ 기존 기록을 불러왔습니다: {default_weight} lbs")
else:
    default_weight = 0.0
    st.info("기록이 없습니다. 새로운 중량을 입력해 주세요.")

# 4. 중량 입력 및 저장 버튼
new_weight = st.number_input(f"{exercise} 1RM 입력 (lbs)", value=default_weight, step=5.0)

if st.button("기록 저장하기"):
    # 데이터 업데이트 로직
    new_record = pd.DataFrame([{"name": user_name, "exercise": exercise, "weight": new_weight}])
    
    if not df.empty:
        # 기존 기록 중 현재 선택한 운동 데이터만 지우고 새 데이터 추가
        updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
    else:
        updated_df = new_record
    
    # 구글 시트 업데이트 (탭 이름 '시트1' 확인 필수)
    conn.update(worksheet="시트1", data=updated_df)
    
    st.balloons()
    st.success(f"'{user_name}'님의 {exercise} 기록이 {new_weight}lbs로 저장되었습니다!")
    
    # [핵심 추가] 저장 후 즉시 화면을 새로고침하여 최신 기록을 반영합니다.
    st.rerun()

st.divider()

# 5. 강도별 중량 계산 출력
if new_weight > 0:
    st.subheader(f"📊 {exercise} {new_weight}lbs 기준 강도")
    # 체육관 플레이트 세팅을 위한 퍼센트 구성
    target_percents = [50, 60, 70, 75, 80, 85, 90, 95, 100]
    cols = st.columns(3)

    for i, p in enumerate(target_percents):
        with cols[i % 3]:
            # 2.5lbs 단위로 반올림하여 계산
            calc_w = round((new_weight * p / 100) / 2.5) * 2.5
            st.metric(label=f"{p}%", value=f"{calc_w} lbs")

st.info("💡 기록을 저장하면 다음 접속 시 자동으로 불러옵니다.")


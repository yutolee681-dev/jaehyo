import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. 페이지 설정 및 다크 테마 느낌을 위한 아이콘 추가
st.set_page_config(
    page_title="CrossFit 1RM Tracker", 
    page_icon="🏋️", 
    layout="centered"
)

# 2. 구글 시트 연결 설정
conn = st.connection("gsheets", type=GSheetsConnection)

# [핵심] ttl=0으로 실시간 데이터 로드
try:
    df = conn.read(ttl=0)
except Exception:
    # 데이터가 없을 때 날짜(date) 컬럼을 포함한 빈 프레임 생성
    df = pd.DataFrame(columns=['name', 'exercise', 'weight', 'date'])

st.title("🏋️ 1RM을 기억해!!")

# 3. 사용자 입력 섹션
user_name = st.text_input("사용자 이름을 입력하세요 (예: 재효)", value="재효")
# 운동 리스트 세분화 (Power/Squat 구분)
exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
exercise = st.selectbox("운동 선택", exercise_list)

# 기존 기록 불러오기
if not df.empty and 'name' in df.columns:
    existing_data = df[(df['name'] == user_name) & (df['exercise'] == exercise)]
else:
    existing_data = pd.DataFrame()

if not existing_data.empty:
    last_record = existing_data.iloc[-1]
    default_weight = float(last_record['weight'])
    # 날짜 정보가 있다면 가져오기
    last_date = last_record.get('date', '기록 없음')
    st.success(f"✅ 기존 기록: {default_weight} lbs (최근 업데이트: {last_date})")
else:
    default_weight = 0.0
    st.info("기록이 없습니다. 새로운 중량을 입력해 주세요.")

# 4. 중량 입력 및 저장 버튼
new_weight = st.number_input(f"{exercise} 1RM 입력 (lbs)", value=default_weight, step=5.0)

if st.button("기록 저장하기"):
    # 현재 날짜 기록 (RPA 개발자답게 정확한 타임스탬프!)
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # 데이터 업데이트 로직 (날짜 포함)
    new_record = pd.DataFrame([{
        "name": user_name, 
        "exercise": exercise, 
        "weight": new_weight,
        "date": current_date
    }])
    
    if not df.empty:
        updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
    else:
        updated_df = new_record
    
    # 구글 시트 업데이트
    conn.update(worksheet="시트1", data=updated_df)
    
    st.balloons()
    st.success(f"저장 성공! {new_weight}lbs (날짜: {current_date})")
    
    # 즉시 화면 갱신
    st.rerun()

st.divider()

# 5. 강도별 중량 계산 출력
if new_weight > 0:
    st.subheader(f"📊 {exercise} {new_weight}lbs 기준 강도")
    target_percents = [50, 60, 70, 75, 80, 85, 90, 95, 100]
    cols = st.columns(3)

    for i, p in enumerate(target_percents):
        with cols[i % 3]:
            # 2.5lbs 단위로 반올림
            calc_w = round((new_weight * p / 100) / 2.5) * 2.5
            st.metric(label=f"{p}%", value=f"{calc_w} lbs")

st.info("💡 기록을 저장하면 다음 접속 시 자동으로 불러옵니다.")

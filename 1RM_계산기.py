import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(
    page_title="CrossFit 1RM Tracker", 
    page_icon="🏋️", 
    layout="centered"
)

# 2. 구글 시트 연결 설정 (실시간 로드)
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df = conn.read(ttl=0)
except Exception:
    df = pd.DataFrame(columns=['name', 'exercise', 'weight', 'date'])

st.title("🏋️ 1RM을 기억해!!")

# --- 3. 사용자 입력 섹션 (스크롤 선택 기능 추가) ---
st.subheader("👤 사용자 정보")

# 구글 시트에서 등록된 이름 목록 추출 및 정렬
if not df.empty and 'name' in df.columns:
    user_list = sorted(df['name'].dropna().unique().tolist())
else:
    user_list = []

# 입력 방식 선택 (UI를 깔끔하게 라디오 버튼으로 구성)
input_mode = st.radio("로그인 방식", ["기존 사용자 선택", "신규 사용자 등록"], horizontal=True)

if input_mode == "기존 사용자 선택" and user_list:
    user_name = st.selectbox("등록된 이름을 선택하세요", user_list)
else:
    user_name = st.text_input("이름을 입력하세요", value="재효")

# 운동 종목 선택
exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
exercise = st.selectbox("운동 선택", exercise_list)

# --- 4. 기존 기록 불러오기 ---
existing_data = df[(df['name'] == user_name) & (df['exercise'] == exercise)] if not df.empty else pd.DataFrame()

if not existing_data.empty:
    last_record = existing_data.iloc[-1]
    default_weight = float(last_record['weight'])
    last_date = last_record.get('date', '기록 없음')
    st.success(f"✅ {user_name}님의 기존 기록: {default_weight} lbs (업데이트: {last_date})")
else:
    default_weight = 0.0
    st.info(f"'{user_name}'님의 {exercise} 기록이 없습니다. 새로운 기록을 측정해 보세요!")

# --- 5. 중량 입력 및 저장 섹션 ---
new_weight = st.number_input(f"{exercise} 1RM 입력 (lbs)", value=default_weight, step=5.0)

if st.button("기록 저장하기"):
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # 새로운 레코드 생성
    new_record = pd.DataFrame([{
        "name": user_name, 
        "exercise": exercise, 
        "weight": new_weight,
        "date": current_date
    }])
    
    # 데이터 업데이트 (기존 기록은 제외하고 새 기록 합치기)
    if not df.empty:
        updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
    else:
        updated_df = new_record
    
    # 구글 시트에 최종 반영
    conn.update(worksheet="시트1", data=updated_df)
    
    st.balloons()
    st.success(f"'{user_name}'님의 기록이 {new_weight}lbs로 저장되었습니다! (날짜: {current_date})")
    
    # 즉시 화면을 새로고침하여 드롭다운 등에 반영
    st.rerun()

st.divider()

# --- 6. 강도별 중량 계산 출력 ---
if new_weight > 0:
    st.subheader(f"📊 {exercise} {new_weight}lbs 기준 강도")
    target_percents = [50, 60, 70, 75, 80, 85, 90, 95, 100]
    cols = st.columns(3)

    for i, p in enumerate(target_percents):
        with cols[i % 3]:
            # 실제 플레이트 세팅용 2.5단위 반올림
            calc_w = round((new_weight * p / 100) / 2.5) * 2.5
            st.metric(label=f"{p}%", value=f"{calc_w} lbs")

st.info("💡 이름을 선택하면 본인의 과거 기록을 자동으로 불러옵니다.")

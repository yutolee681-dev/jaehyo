import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(
    page_title="1RM을 기억해!!", 
    page_icon="🏋️", 
    layout="centered"
)

# 2. 구글 시트 연결 (실시간 데이터 로드)
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df = conn.read(ttl=0)
except Exception:
    df = pd.DataFrame(columns=['name', 'exercise', 'weight', 'date'])

st.title("🏋️ 1RM을 기억해!!")

# --- 3. 사용자 정보 섹션 (Placeholder & 선택 강제) ---
st.subheader("👤 사용자 정보")

# 등록된 이름 목록 추출
if not df.empty and 'name' in df.columns:
    user_list = sorted(df['name'].dropna().unique().tolist())
else:
    user_list = []

# 입력 방식 선택
input_mode = st.radio("로그인 방식", ["기존 사용자 선택", "신규 사용자 등록"], horizontal=True)

# 변수 초기화
user_name = ""

if input_mode == "기존 사용자 선택":
    if user_list:
        # 맨 앞에 '선택하세요'를 넣어 아무것도 선택 안 된 상태를 만듦
        selected_name = st.selectbox("등록된 이름을 선택하세요", ["선택하세요"] + user_list)
        if selected_name != "선택하세요":
            user_name = selected_name
    else:
        st.warning("등록된 사용자가 없습니다. '신규 사용자 등록'을 선택해 주세요.")
else:
    # value 대신 placeholder를 사용해 흐린 글씨 표시
    user_name = st.text_input("이름을 입력하세요", placeholder="예: 재효, 안뉴")

# 운동 종목 선택
exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
exercise = st.selectbox("운동 선택", exercise_list)

# --- 4. 기존 기록 불러오기 ---
# 이름이 입력/선택된 경우에만 기록을 찾아옴
if user_name:
    existing_data = df[(df['name'] == user_name) & (df['exercise'] == exercise)] if not df.empty else pd.DataFrame()
    
    if not existing_data.empty:
        last_record = existing_data.iloc[-1]
        default_weight = float(last_record['weight'])
        last_date = last_record.get('date', '기록 없음')
        st.success(f"✅ {user_name}님의 기존 기록: {default_weight} lbs (최근 업데이트: {last_date})")
    else:
        default_weight = 0.0
        st.info(f"'{user_name}'님의 {exercise} 기록이 없습니다. 새로운 기록을 입력해 주세요.")
else:
    default_weight = 0.0
    st.write("이름을 선택하거나 입력하면 기존 기록이 표시됩니다.")

# --- 5. 중량 입력 및 저장 섹션 (검증 로직 포함) ---
new_weight = st.number_input(f"{exercise} 1RM 입력 (lbs)", value=default_weight, step=5.0)

if st.button("기록 저장하기"):
    # [Validation] 이름이 비어있는지 체크
    if not user_name:
        st.error("⚠️ 이름을 먼저 입력하거나 선택해야 저장이 가능합니다!")
    elif new_weight <= 0:
        st.error("⚠️ 0보다 큰 중량을 입력해 주세요!")
    else:
        # 정상 저장 로직
        current_date = datetime.now().strftime("%Y-%m-%d")
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
        
        conn.update(worksheet="시트1", data=updated_df)
        st.balloons()
        st.success(f"'{user_name}'님의 {exercise} 기록이 저장되었습니다! (날짜: {current_date})")
        
        # 즉시 반영을 위해 재실행
        st.rerun()

st.divider()

# --- 6. 강도별 중량 계산 출력 ---
if new_weight > 0:
    st.subheader(f"📊 {exercise} {new_weight}lbs 기준 강도")
    target_percents = [50, 60, 70, 75, 80, 85, 90, 95, 100]
    cols = st.columns(3)

    for i, p in enumerate(target_percents):
        with cols[i % 3]:
            # 실제 원판 세팅용 2.5lbs 반올림
            calc_w = round((new_weight * p / 100) / 2.5) * 2.5
            st.metric(label=f"{p}%", value=f"{calc_w} lbs")

st.info("💡 이름을 선택하면 본인의 과거 기록을 자동으로 불러옵니다.")


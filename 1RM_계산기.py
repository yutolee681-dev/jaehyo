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

# --- 3. 사용자 정보 섹션 ---
st.subheader("👤 사용자 정보")

if not df.empty and 'name' in df.columns:
    user_list = sorted(df['name'].dropna().unique().tolist())
else:
    user_list = []

input_mode = st.radio("로그인 방식", ["기존 사용자 선택", "신규 사용자 등록"], horizontal=True)

user_name = ""
if input_mode == "기존 사용자 선택":
    if user_list:
        selected_name = st.selectbox("등록된 이름을 선택하세요", ["선택하세요"] + user_list)
        if selected_name != "선택하세요":
            user_name = selected_name
    else:
        st.warning("등록된 사용자가 없습니다. '신규 사용자 등록'을 선택해 주세요.")
else:
    user_name = st.text_input("이름을 입력하세요", placeholder="예: 재효, 홍길동")

exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
exercise = st.selectbox("운동 선택", exercise_list)

# --- 4. 기존 기록 불러오기 ---
if user_name:
    existing_data = df[(df['name'] == user_name) & (df['exercise'] == exercise)] if not df.empty else pd.DataFrame()
    
    if not existing_data.empty:
        last_record = existing_data.iloc[-1]
        default_weight = float(last_record['weight'])
        last_date = last_record.get('date', '기록 없음')
        st.success(f"✅ {user_name}님의 기존 기록: {default_weight} lbs (최근 업데이트: {last_date})")
    else:
        default_weight = 0.0
        st.info(f"'{user_name}'님의 {exercise} 기록이 없습니다.")
else:
    default_weight = 0.0

# --- 5. 중량 입력 및 저장 ---
new_weight = st.number_input(f"{exercise} 1RM 입력 (lbs)", value=default_weight, step=5.0)

if st.button("기록 저장하기"):
    if not user_name:
        st.error("⚠️ 이름을 입력하거나 선택해 주세요!")
    elif new_weight <= 0:
        st.error("⚠️ 중량을 입력해 주세요!")
    else:
        current_date = datetime.now().strftime("%Y-%m-%d")
        new_record = pd.DataFrame([{"name": user_name, "exercise": exercise, "weight": new_weight, "date": current_date}])
        
        if not df.empty:
            updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
        else:
            updated_df = new_record
        
        conn.update(worksheet="시트1", data=updated_df)
        st.balloons()
        st.rerun()

st.divider()

# --- 6. 강도별 가이드 (메트릭만 표시) ---
if new_weight > 0:
    st.subheader(f"📊 {exercise} 강도별 가이드")
    target_percents = [50, 60, 70, 75, 80, 85, 90, 95, 100]
    cols = st.columns(3)
    for i, p in enumerate(target_percents):
        with cols[i % 3]:
            calc_w = round((new_weight * p / 100) / 2.5) * 2.5
            st.metric(label=f"{p}%", value=f"{calc_w} lbs")

# --- 7. 내 전체 기록 대시보드 (가로 차트로 수정) ---
if user_name:
    st.divider()
    st.subheader(f"🏆 {user_name}님의 종목별 최고 기록")
    
    my_data = df[df['name'] == user_name].copy()
    
    if not my_data.empty:
        display_df = my_data[['exercise', 'weight', 'date']].sort_values(by='weight', ascending=True) # 중량순 정렬
        display_df.columns = ['종목', '기록(lbs)', '최근 업데이트']
        
        # [핵심] 가로 바 차트(horizontal) 적용을 위해 Altair 차트 활용
        # st.bar_chart에서 가로/세로는 데이터 형태에 따라 자동 결정되지만, 
        # 명확하게 하기 위해 아래 표 바로 위에 시각화합니다.
        st.bar_chart(data=display_df, x="기록(lbs)", y="종목", color="#29b5e8")
        
        st.dataframe(display_df.sort_values(by='기록(lbs)', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.write("아직 등록된 기록이 없습니다.")

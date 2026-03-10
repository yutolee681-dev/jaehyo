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
            # 같은 사용자-같은 종목의 기존 데이터는 제외하고 업데이트
            updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
        else:
            updated_df = new_record
        
        conn.update(worksheet="시트1", data=updated_df)
        st.balloons()
        st.rerun()

st.divider()

# --- 6. 강도별 중량 계산 및 그래프 출력 ---
if new_weight > 0:
    st.subheader(f"📊 {exercise} 강도별 가이드")
    
    target_percents = [50, 60, 70, 75, 80, 85, 90, 95, 100]
    calc_data = []

    for p in target_percents:
        calc_w = round((new_weight * p / 100) / 2.5) * 2.5
        calc_data.append({"Percentage": f"{p}%", "Weight (lbs)": calc_w})
    
    calc_df = pd.DataFrame(calc_data)
    st.bar_chart(data=calc_df, x="Percentage", y="Weight (lbs)", color="#ff4b4b")

    cols = st.columns(3)
    for i, row in calc_df.iterrows():
        with cols[i % 3]:
            st.metric(label=row["Percentage"], value=f"{row['Weight (lbs)']} lbs")

# --- 7. [신규 추가] 내 전체 기록 대시보드 ---
if user_name:
    st.divider()
    st.subheader(f"🏆 {user_name}님의 종목별 1RM 현황")
    
    # 내 이름으로 된 데이터만 필터링
    my_data = df[df['name'] == user_name].copy()
    
    if not my_data.empty:
        # 가독성을 위해 컬럼명 변경 및 표시
        display_df = my_data[['exercise', 'weight', 'date']].sort_values(by='weight', ascending=False)
        display_df.columns = ['종목', '기록(lbs)', '최근 업데이트']
        
        # 표로 보여주기
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # 내 기록을 한눈에 보는 가로 바 차트
        st.bar_chart(data=display_df, x="종목", y="기록(lbs)", color="#29b5e8")
    else:
        st.write("아직 등록된 기록이 없습니다.")

st.info("💡 이름을 선택하면 하단에서 본인의 모든 기록을 한눈에 볼 수 있습니다.")

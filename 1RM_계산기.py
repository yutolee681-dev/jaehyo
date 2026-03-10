import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import altair as alt # 차트 세부 설정을 위한 라이브러리

# 1. 페이지 설정
st.set_page_config(
    page_title="CrossFit 1RM Tracker", 
    page_icon="🏋️", 
    layout="centered"
)

# 2. 구글 시트 연결 설정
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df = conn.read(ttl=0)
except Exception:
    df = pd.DataFrame(columns=['name', 'exercise', 'weight', 'date'])

st.title("🏋️ 1RM을 기억해!!")

# --- 3. 사용자 정보 섹션 (검증 및 Placeholder) ---
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
    user_name = st.text_input("이름을 입력하세요", placeholder="예: 재효, 예삐, 안뉴")

exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
exercise = st.selectbox("운동 선택", exercise_list)

# --- 4. 기존 기록 불러오기 ---
if user_name:
    existing_data = df[(df['name'] == user_name) & (df['exercise'] == exercise)] if not df.empty else pd.DataFrame()
    
    if not existing_data.empty:
        last_record = existing_data.iloc[-1]
        default_weight = float(last_record['weight'])
        last_date = last_record.get('date', '기록 없음')
        st.success(f"✅ {user_name}님의 기존 기록: {default_weight} lbs (업데이트: {last_date})")
    else:
        default_weight = 0.0
        st.info(f"'{user_name}'님의 {exercise} 기록이 없습니다.")
else:
    default_weight = 0.0

# --- 5. 중량 입력 및 저장 ---
new_weight = st.number_input(f"{exercise} 1RM 입력 (lbs)", value=default_weight, step=5.0)

if st.button("기록 저장하기"):
    if not user_name:
        st.error("⚠️ 이름을 먼저 입력하거나 선택해야 저장이 가능합니다!")
    elif new_weight <= 0:
        st.error("⚠️ 0보다 큰 중량을 입력해 주세요!")
    else:
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
        st.success(f"저장 완료! (날짜: {current_date})")
        st.rerun()

st.divider()

# --- 6. 강도별 가이드 (숫자 메트릭) ---
if new_weight > 0:
    st.subheader(f"📊 {exercise} 강도별 가이드")
    target_percents = [50, 60, 70, 75, 80, 85, 90, 95, 100]
    cols = st.columns(3)
    for i, p in enumerate(target_percents):
        with cols[i % 3]:
            calc_w = round((new_weight * p / 100) / 2.5) * 2.5
            st.metric(label=f"{p}%", value=f"{calc_w} lbs")

# --- 7. 내 전체 기록 대시보드 (글자 가로 고정 차트) ---
if user_name:
    st.divider()
    st.subheader(f"🏆 {user_name}님의 종목별 최고 기록")
    
    my_data = df[df['name'] == user_name].copy()
    
    if not my_data.empty:
        # 차트용 데이터 정리
        chart_df = my_data[['exercise', 'weight']].sort_values(by='weight', ascending=False)
        chart_df.columns = ['종목', '기록']

        # [Altair 차트 설정] labelAngle=0 설정으로 글자를 가로로 고정합니다.
        personal_chart = alt.Chart(chart_df).mark_bar(color="#29b5e8").encode(
            x=alt.X('종목:N', sort='-y', axis=alt.Axis(labelAngle=0, title="운동 종목")),
            y=alt.Y('기록:Q', title="중량 (lbs)"),
            tooltip=['종목', '기록']
        ).properties(height=400)

        st.altair_chart(personal_chart, use_container_width=True)
        
        # 상세 데이터 표
        st.dataframe(chart_df, use_container_width=True, hide_index=True)
    else:
        st.write("등록된 기록이 없습니다.")


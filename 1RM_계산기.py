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
        raw_df = conn.read(worksheet="sheet1", ttl=0)
        if raw_df is None or raw_df.empty:
            return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password'])
        if 'password' not in raw_df.columns:
            raw_df['password'] = "0000"
        return raw_df
    except Exception:
        return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password'])

df = get_full_data()

st.title("🏋️ 1RM을 기억해!!")

# --- 3. 사용자 인증 및 개인 기록 대시보드 ---
with st.container():
    st.subheader("👤 사용자 인증 및 기록 확인")
    
    top_col1, top_col2 = st.columns([1, 1])
    
    with top_col1:
        input_mode = st.radio("로그인 방식", ["기존 사용자", "신규 등록"], horizontal=True)
        if input_mode == "기존 사용자":
            user_list = sorted(df['name'].dropna().unique().tolist()) if not df.empty else []
            user_name = st.selectbox("이름 선택", ["선택하세요"] + user_list, label_visibility="collapsed")
            if user_name == "선택하세요": user_name = ""
        else:
            user_name = st.text_input("이름 입력", placeholder="예: 재효", label_visibility="collapsed")

    is_auth = False
    stored_pw = "0000"

    with top_col2:
        if user_name:
            # ✨ 핵심: key에 user_name을 포함시켜 이름이 바뀔 때마다 입력창을 강제 초기화합니다.
            pw_input = st.text_input(
                "비밀번호", 
                type="password", 
                key=f"pw_{user_name}", # 이름별로 고유 키 생성
                placeholder="비밀번호 입력",
                label_visibility="collapsed"
            )
            
            user_rows = df[df['name'] == user_name]
            if not user_rows.empty:
                try:
                    raw_pw = user_rows.iloc[0]['password']
                    # 시트 데이터가 숫자/문자 섞여있어도 안전하게 처리
                    stored_pw = str(int(float(raw_pw))).strip()
                except:
                    stored_pw = str(user_rows.iloc[0]['password']).strip()
                
                if pw_input.strip() == stored_pw:
                    is_auth = True
                    st.success(f"✅ {user_name}님 인증 완료")
                elif pw_input != "":
                    st.error("❌ 비밀번호 불일치")

if is_auth:
    my_data = df[df['name'] == user_name].copy()
    chart_df = my_data[['exercise', 'weight']].sort_values(by='weight', ascending=False)
    chart_df.columns = ['종목', '기록']
    
    personal_chart = alt.Chart(chart_df).mark_bar(color="#29b5e8").encode(
        x=alt.X('종목:N', sort='-y', axis=alt.Axis(labelAngle=0, title=None)),
        y=alt.Y('기록:Q', title="중량 (lbs)")
    ).properties(height=300)
    
    st.altair_chart(personal_chart, use_container_width=True)

st.divider()

# --- 4. 강도별 가이드 및 기록 입력 ---
if user_name and (input_mode == "신규 등록" or is_auth):
    st.subheader("💪 오늘의 운동 및 가이드")
    
    exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
    exercise = st.selectbox("종목 선택", exercise_list)
    
    ex_record = df[(df['name'] == user_name) & (df['exercise'] == exercise)]
    current_pr = float(pd.to_numeric(ex_record['weight'], errors='coerce').max()) if not ex_record.empty else 0.0
    
    if current_pr > 0:
        st.info(f"💡 현재 {exercise} 최고 기록: **{current_pr} lbs**")
        
        # 3열 구성 강도 가이드
        percents = [50, 60, 70, 75, 80, 85, 90, 95, 100]
        g_cols = st.columns(3)
        
        for i, p in enumerate(percents):
            with g_cols[i % 3]:
                calc_w = round((current_pr * p / 100) / 2.5) * 2.5
                st.metric(label=f"{p}%", value=f"{calc_w} lbs")
    
    st.divider()
    
    # 🏋️ 새로운 기록 저장
    st.subheader("📝 새로운 기록 저장")
    save_col1, save_col2 = st.columns(2)
    
    with save_col1:
        new_weight = st.number_input("오늘 달성 기록 (lbs)", value=0.0, step=5.0)
    
    with save_col2:
        if input_mode == "신규 등록":
            new_user_pw = st.text_input("비번 설정 (4자리)", type="password", key="new_pw_input")
        else:
            st.info(f"📅 기록일: {datetime.now().strftime('%Y-%m-%d')}")

    if st.button("🏋️ 새로운 1RM 저장하기", use_container_width=True):
        if new_weight <= 0:
            st.error("중량을 입력해주세요.")
        else:
            current_date = datetime.now().strftime("%Y-%m-%d")
            final_save_pw = new_user_pw.strip() if input_mode == "신규 등록" else stored_pw
            
            new_record = pd.DataFrame([{"name": user_name, "exercise": exercise, "weight": new_weight, "date": current_date, "password": final_save_pw}])
            updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
            
            try:
                conn.update(worksheet="sheet1", data=updated_df[['name', 'exercise', 'weight', 'date', 'password']])
                st.balloons()
                st.success("기록이 저장되었습니다!")
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {e}")

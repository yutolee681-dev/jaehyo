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
        # 탭 이름을 'sheet1'로 명시하여 읽어옵니다.
        raw_df = conn.read(worksheet="sheet1", ttl=0)
        
        if raw_df is None or raw_df.empty:
            return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password'])
        
        # password 컬럼 누락 방지
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
        st.warning("등록된 사용자가 없습니다. '신규 사용자 등록'을 먼저 진행해 주세요.")
else:
    user_name = st.text_input("이름을 입력하세요", placeholder="예: 재효")
    new_user_pw = st.text_input("비밀번호 설정 (숫자 4자리 권장)", type="password")

exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]
exercise = st.selectbox("운동 선택", exercise_list)

# --- 4. 기존 최고 기록 확인 (PR 체크) ---
prev_max = 0.0
if user_name and not df.empty:
    user_ex_data = df[(df['name'] == user_name) & (df['exercise'] == exercise)]
    if not user_ex_data.empty:
        prev_max = float(pd.to_numeric(user_ex_data['weight'], errors='coerce').max())
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
        
        # 비밀번호 처리: 숫자로 저장하되 실패 시 문자열 유지
        if input_mode == "신규 사용자 등록":
            try:
                final_pw = int(new_user_pw)
            except ValueError:
                final_pw = str(new_user_pw).strip()
        else:
            user_pw_rows = df[df['name'] == user_name]['password']
            # 기존 비번 로드 시에도 타입 안정성 확보
            try:
                final_pw = int(user_pw_rows.iloc[0]) if not user_pw_rows.empty else 0
            except (ValueError, TypeError):
                final_pw = str(user_pw_rows.iloc[0]).strip() if not user_pw_rows.empty else "0000"

        new_record = pd.DataFrame([{
            "name": user_name, "exercise": exercise, "weight": new_weight, 
            "date": current_date, "password": final_pw
        }])
        
        if not df.empty:
            updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == exercise))], new_record], ignore_index=True)
        else:
            updated_df = new_record
        
        try:
            updated_df = updated_df[['name', 'exercise', 'weight', 'date', 'password']]
            conn.update(worksheet="sheet1", data=updated_df)
            
            if prev_max > 0 and new_weight > prev_max:
                st.balloons()
                st.success(f"🎊 PR 경신! {new_weight} lbs!! 축하합니다! 🎊")
            else:
                st.success("성공적으로 저장되었습니다.")
            st.rerun()
        except Exception as e:
            st.error(f"❌ 저장 실패! 실제 에러: {e}")

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

# --- 7. 개인 기록 대시보드 (비밀번호 비교 강화) ---
if user_name and input_mode == "기존 사용자 선택":
    st.divider()
    st.subheader(f"🏆 {user_name}님의 개인 기록")
    pw_check = st.text_input("비밀번호 입력", type="password", key="auth_check")
    
    user_rows = df[df['name'] == user_name]
    
    if not user_rows.empty:
        # 핵심 해결책: 시트의 값(숫자/실수/문자)을 모두 문자열로 변환하여 비교
        # float로 읽힐 경우 '1111.0'이 될 수 있으므로 int로 먼저 변환 시도 후 str 처리
        try:
            raw_stored_pw = user_rows.iloc[0]['password']
            # 숫자인 경우 소수점을 떼기 위해 int -> str 순서로 변환
            stored_pw = str(int(float(raw_stored_pw))).strip()
        except (ValueError, TypeError):
            stored_pw = str(user_rows.iloc[0]['password']).strip()
            
        input_pw = str(pw_check).strip()
        
        if pw_check != "" and input_pw == stored_pw:
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
            st.error("비밀번호가 일치하지 않습니다.")

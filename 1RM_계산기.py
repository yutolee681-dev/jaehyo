import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import altair as alt
import time

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="centered")

# --- 종목 리스트 및 차트용 단축어 설정 (더 짧게 수정) ---
exercise_list = [
    "Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", 
    "Deadlift", "Back Squat", "Shoulder Press",
    "Thruster", "Bench Press", "Jerk", "Overhead Squat"
]

# 모바일 가독성을 위해 더 짧은 약어 사용
rename_map = {
    "Power Clean": "P.Clean", "Squat Clean": "S.Clean",
    "Power Snatch": "P.Snatch", "Squat Snatch": "S.Snatch",
    "Deadlift": "Dead", "Back Squat": "B.Squat",
    "Shoulder Press": "S.Press", "Thruster": "Thrust",
    "Bench Press": "Bench", "Jerk": "Jerk",
    "Overhead Squat": "OHS"
}

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def get_full_data():
    try:
        raw_df = conn.read(worksheet="sheet1", ttl=0)
        if raw_df is None or raw_df.empty:
            return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender'])
        for col in ['password', 'gender']:
            if col not in raw_df.columns:
                raw_df[col] = "0000" if col == 'password' else "남성"
        return raw_df
    except Exception:
        return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender'])

df = get_full_data()

st.markdown("<div id='link_to_top'></div>", unsafe_allow_html=True)
st.title("🏋️ 1RM을 기억해")

# --- 3. [최상단] 실시간 박스 랭킹판 (TOP 5) ---
selected_rank_exercise = st.selectbox("🏆 실시간 랭킹 종목 선택", exercise_list, index=0)
rank_df = df[df['exercise'] == selected_rank_exercise].copy()

with st.expander(f"🔥 {selected_rank_exercise} TOP 5 리더보드", expanded=True):
    if not rank_df.empty:
        tab_m, tab_f = st.tabs(["♂️ M", "♀️ F"])
        def display_rank(data):
            sorted_data = data.sort_values(by='weight', ascending=False).head(5)
            if sorted_data.empty:
                st.write("기록 없음")
            else:
                for i, row in enumerate(sorted_data.itertuples(), 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}th**"
                    st.markdown(f"{medal} **{row.name}** : `{row.weight} lbs`")
        with tab_m: display_rank(rank_df[rank_df['gender'] == "남성"])
        with tab_f: display_rank(rank_df[rank_df['gender'] == "여성"])
    else:
        st.write("첫 주인공이 되어보세요!")

st.divider()

# --- 4. 사용자 인증 섹션 ---
with st.container():
    st.subheader("👤 사용자 인증")
    input_mode = st.radio("로그인 방식", ["기존 사용자", "신규 등록"], horizontal=True)
    
    user_name = ""
    user_gender_input = "남성"
    
    if input_mode == "기존 사용자":
        user_list = sorted(df['name'].dropna().unique().tolist()) if not df.empty else []
        selected_name = st.selectbox("등록된 이름을 선택하세요", ["선택하세요"] + user_list)
        user_name = selected_name if selected_name != "선택하세요" else ""
    else:
        reg_col1, reg_col2 = st.columns(2)
        with reg_col1: user_name = st.text_input("이름 입력", placeholder="예: 재효")
        with reg_col2: user_gender_input = st.radio("성별", ["남성", "여성"], horizontal=True)

    is_auth = False
    if user_name:
        pw_input = st.text_input("비밀번호", type="password", key=f"pw_{user_name}")
        user_rows = df[df['name'] == user_name]
        if input_mode == "기존 사용자":
            if not user_rows.empty:
                user_gender_val = user_rows.iloc[0]['gender']
                try: stored_pw = str(int(float(user_rows.iloc[0]['password']))).strip()
                except: stored_pw = str(user_rows.iloc[0]['password']).strip()
                if pw_input.strip() == stored_pw: is_auth = True
        else:
            if pw_input: is_auth = True

# --- [수정 핵심] 개인 차트 모바일 최적화 (가로형 차트) ---
if is_auth and not df.empty:
    my_data = df[df['name'] == user_name].copy()
    if not my_data.empty:
        st.divider()
        chart_df = my_data[['exercise', 'weight']].sort_values(by='weight', ascending=False)
        chart_df['exercise'] = chart_df['exercise'].map(rename_map).fillna(chart_df['exercise'])
        chart_df.columns = ['종목', '기록']
        
        st.write(f"📊 {user_name}님의 종목별 1RM 현황")
        
        # 가로형 막대 차트로 변경 (y축에 종목, x축에 기록)
        personal_chart = alt.Chart(chart_df).mark_bar(
            color="#29b5e8", 
            cornerRadiusEnd=5 # 막대 끝을 둥글게 해서 세련되게
        ).encode(
            y=alt.Y('종목:N', sort='-x', title=None), # 세로로 종목 나열
            x=alt.X('기록:Q', title="중량 (lbs)"),
            text=alt.Text('기록:Q') # 막대 위에 숫자 표시
        ).properties(height=alt.Step(30)) # 종목 개수에 따라 차트 높이 자동 조절
        
        # 막대 옆에 숫자 표시 추가
        chart_with_text = personal_chart + personal_chart.mark_text(align='left', dx=5)
        
        st.altair_chart(chart_with_text, use_container_width=True)

st.divider()

# --- 5. 기록 저장 및 가이드 ---
if user_name and is_auth:
    st.subheader("💪 오늘의 기록 업데이트")
    save_exercise = st.selectbox("저장할 종목", exercise_list, index=exercise_list.index(selected_rank_exercise))
    
    ex_record = df[(df['name'] == user_name) & (df['exercise'] == save_exercise)]
    prev_max = float(pd.to_numeric(ex_record['weight'], errors='coerce').max()) if not ex_record.empty else 0.0
    
    if prev_max > 0:
        st.info(f"💡 최고 기록: **{prev_max} lbs**")
        percents = [50, 60, 70, 80, 90, 100] # 모바일용으로 주요 퍼센트만 축소 노출 가능
        g_cols = st.columns(3)
        for i, p in enumerate(percents):
            with g_cols[i % 3]:
                calc_w = round((prev_max * p / 100) / 2.5) * 2.5
                st.metric(label=f"{p}%", value=f"{calc_w}")
    
    new_weight = st.number_input("오늘 달성 (lbs)", value=0.0, step=5.0)
    if st.button("🏋️ 새로운 1RM 저장", use_container_width=True):
        if new_weight > 0 and pw_input:
            final_gender = user_gender_input if input_mode == "신규 등록" else user_rows.iloc[0]['gender']
            new_record = pd.DataFrame([{"name": user_name, "exercise": save_exercise, "weight": new_weight, "date": datetime.now().strftime("%Y-%m-%d"), "password": pw_input.strip(), "gender": final_gender}])
            updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == save_exercise))], new_record], ignore_index=True)
            conn.update(worksheet="sheet1", data=updated_df)
            st.balloons()
            time.sleep(1)
            st.rerun()

    st.markdown("<br><a href='#link_to_top' style='text-decoration:none;'><button style='width:100%; border-radius:10px; border:1px solid #ddd; background-color:#f9f9f9; padding:10px; cursor:pointer;'>🔝 맨 위로 가기</button></a>", unsafe_allow_html=True)

# --- 6. 🛠️ 관리자 모드 (5207) ---
with st.expander("🛠️ Admin"):
    admin_pw = st.text_input("Key", type="password")
    if admin_pw == "5207":
        st.dataframe(df)

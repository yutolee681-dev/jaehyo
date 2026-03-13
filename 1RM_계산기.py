import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import altair as alt
import time

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="centered")

# --- 종목 및 단축어 설정 ---
exercise_list = [
    "Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", 
    "Deadlift", "Back Squat", "Shoulder Press",
    "Thruster", "Bench Press", "Jerk", "Overhead Squat"
]

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
            return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo'])
        
        required_cols = {'password': '0000', 'gender': '남성', 'memo': ''}
        for col, default in required_cols.items():
            if col not in raw_df.columns:
                raw_df[col] = default
        return raw_df
    except Exception:
        return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo'])

df = get_full_data()

if 'is_auth' not in st.session_state:
    st.session_state.is_auth = False
    st.session_state.user_name = ""
    st.session_state.user_gender = "남성"

st.markdown("<div id='link_to_top'></div>", unsafe_allow_html=True)
st.title("🏋️ 1RM을 기억해")

# --- 3. 최상단 환영 메시지 ---
if st.session_state.is_auth:
    col_welcome, col_logout = st.columns([3, 1])
    with col_welcome:
        st.subheader(f"👋 {st.session_state.user_name}님")
    with col_logout:
        if st.button("로그아웃", use_container_width=True):
            st.session_state.is_auth = False
            st.session_state.user_name = ""
            st.rerun()
    st.divider()

# --- 4. 실시간 박스 랭킹판 ---
selected_rank_exercise = st.selectbox("🏆 실시간 랭킹 종목 선택", exercise_list, index=0)

rank_df = df[df['exercise'] == selected_rank_exercise].copy()
rank_df['weight'] = pd.to_numeric(rank_df['weight'], errors='coerce')
best_rank_df = rank_df.sort_values('weight', ascending=False).drop_duplicates('name')

with st.expander(f"🔥 {selected_rank_exercise} TOP 5", expanded=True):
    if not best_rank_df.empty:
        tab_m, tab_f = st.tabs(["♂️ M", "♀️ F"])
        def display_rank(data):
            sorted_data = data.sort_values(by='weight', ascending=False).head(5)
            if sorted_data.empty: st.write("기록 없음")
            else:
                for i, row in enumerate(sorted_data.itertuples(), 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}th**"
                    st.markdown(f"{medal} **{row.name}** : `{row.weight} lbs` ")
        with tab_m: display_rank(best_rank_df[best_rank_df['gender'] == "남성"])
        with tab_f: display_rank(best_rank_df[best_rank_df['gender'] == "여성"])
    else: st.write("첫 주인공이 되어보세요!")

st.divider()

# --- 5. 사용자 인증 (생략 가능하지만 전체 코드 유지) ---
if not st.session_state.is_auth:
    with st.container():
        st.subheader("👤 사용자 인증")
        input_mode = st.radio("로그인 방식", ["기존 사용자", "신규 등록"], horizontal=True)
        if input_mode == "기존 사용자":
            user_list = sorted(df['name'].dropna().unique().tolist()) if not df.empty else []
            selected_name = st.selectbox("이름 선택", ["선택하세요"] + user_list)
            if selected_name != "선택하세요":
                pw_input = st.text_input("비밀번호", type="password")
                if st.button("로그인", use_container_width=True):
                    user_rows = df[df['name'] == selected_name]
                    stored_pw = str(user_rows.iloc[-1]['password']).strip()
                    if pw_input.strip() == stored_pw:
                        st.session_state.is_auth = True
                        st.session_state.user_name = selected_name
                        st.session_state.user_gender = user_rows.iloc[-1]['gender']
                        st.rerun()
                    else: st.error("비밀번호 불일치")
        else:
            reg_col1, reg_col2 = st.columns(2)
            new_name = reg_col1.text_input("새 이름", placeholder="예: 재효")
            new_gender = reg_col2.radio("성별", ["남성", "여성"], horizontal=True)
            new_pw = st.text_input("비밀번호 설정", type="password")
            if st.button("등록 및 로그인", use_container_width=True):
                if new_name and new_pw:
                    st.session_state.is_auth = True
                    st.session_state.user_name = new_name
                    st.session_state.user_gender = new_gender
                    st.session_state.temp_pw = new_pw
                    st.rerun()

# --- 6. 개인 차트 가독성 개선 버전 (다크모드 지원) ---
if st.session_state.is_auth:
    my_data = df[df['name'] == st.session_state.user_name].copy()
    my_data['weight'] = pd.to_numeric(my_data['weight'], errors='coerce')
    
    if not my_data.empty:
        # 차트 데이터 준비 (기존 로직 유지)
        chart_df = my_data.sort_values('weight', ascending=False).drop_duplicates('exercise').copy()
        chart_df['exercise_short'] = chart_df['exercise'].map(rename_map).fillna(chart_df['exercise'])
        
        st.write(f"📊 {st.session_state.user_name}님의 종목별 최고 기록")
        
        # 차트 기본 설정
        base = alt.Chart(chart_df).encode(
            y=alt.Y('exercise_short:N', sort='-x', title=None),
            x=alt.X('weight:Q', title="중량 (lbs)")
        )

        # 막대 그래프
        bars = base.mark_bar(color="#29b5e8", cornerRadiusEnd=5)
        
        # [개선 핵심] 숫자를 막대 안쪽(right-aligned)에 표시
        text = base.mark_text(
            align='right',   # 오른쪽 정렬
            dx=-5,           # 막대 끝에서 안쪽으로 5픽셀 이동
            color='white',   # 배경이 하늘색이니 글자는 흰색이 가장 잘 보임 (다크모드 포함)
            fontWeight='bold'
        ).encode(
            text=alt.Text('weight:Q', format='.0f') # 소수점 없이 깔끔하게
        )
        
        # 막대와 텍스트를 합쳐서 출력
        st.altair_chart(bars + text, use_container_width=True)
        
        # 히스토리 필터링 로직 (기존 유지)
        st.divider()
        st.subheader("📋 상세 기록 조회")
        my_exercises = sorted(my_data['exercise'].unique().tolist())
        selected_history_ex = st.selectbox("조회할 종목", ["전체 보기"] + my_exercises, key="history_filter")
        
        history_display_df = my_data if selected_history_ex == "전체 보기" else my_data[my_data['exercise'] == selected_history_ex]
        history_display_df = history_display_df[['date', 'exercise', 'weight', 'memo']].sort_values(by='date', ascending=False)
        st.dataframe(history_display_df, hide_index=True, use_container_width=True)

    
# --- 7. 기록 업데이트 (종목 변경 시 자동 초기화 및 1열 배치) ---
    st.subheader("💪 오늘의 기록 업데이트")
    save_exercise = st.selectbox("종목 선택", exercise_list, index=exercise_list.index(selected_rank_exercise))
    
    ex_record = my_data[my_data['exercise'] == save_exercise]
    prev_max = float(ex_record['weight'].max()) if not ex_record.empty else 0.0
    
    if prev_max > 0:
        st.info(f"💡 {save_exercise} 기존 최고: **{prev_max} lbs**")
        
        # [수정 포인트] 퍼센트 계산 및 1열 순차 출력
        percents = list(range(50, 101, 5)) # 50, 55, 60 ... 100
        
        with st.expander("📊 퍼센트별 중량 확인 (50% ~ 100%)", expanded=True):
            for p in percents:
                calc_w = round((prev_max * p / 100) / 2.5) * 2.5
                # columns 없이 바로 metric을 호출하면 위에서 아래로 1열 정렬됩니다.
                st.metric(label=f"{p}%", value=f"{calc_w} lb")
    
    st.divider()

    # 입력창 (기존 로직 유지)
    new_weight = st.number_input(
        f"오늘의 {save_exercise} 중량 (lbs)", 
        value=prev_max, 
        step=5.0, 
        key=f"weight_{save_exercise}"
    )
    
    new_memo = st.text_input(
        "오늘의 메모", 
        value="",
        placeholder="예: 컨디션 좋음, 스트랩 사용 등", 
        key=f"memo_{save_exercise}"
    )
    
    if st.button("🏋️ 새로운 기록 저장 (누적)", use_container_width=True):
        if new_weight > 0:
            user_data = df[df['name'] == st.session_state.user_name]
            # 최근 데이터에서 비밀번호와 성별 가져오기
            last_row = user_data.iloc[-1] if not user_data.empty else None
            final_pw = str(last_row['password']) if last_row is not None else st.session_state.get('temp_pw', '0000')
            
            new_record = pd.DataFrame([{
                "name": st.session_state.user_name, 
                "exercise": save_exercise, 
                "weight": new_weight, 
                "date": datetime.now().strftime("%Y-%m-%d"), 
                "password": final_pw, 
                "gender": st.session_state.user_gender,
                "memo": new_memo 
            }])
            
            updated_df = pd.concat([df, new_record], ignore_index=True)
            conn.update(worksheet="sheet1", data=updated_df)
            st.balloons()
            time.sleep(1)
            st.rerun()

    st.markdown("<br><a href='#link_to_top' style='text-decoration:none;'><button style='width:100%; border-radius:10px; border:1px solid #ddd; background-color:#f9f9f9; padding:10px; cursor:pointer;'>🔝 맨 위로 가기</button></a>", unsafe_allow_html=True)

# --- 8. 관리자 모드 ---
with st.expander("🛠️ Admin"):
    admin_pw = st.text_input("Key", type="password")
    if admin_pw == "5207":
        st.dataframe(df)






import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import time

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="centered")

# --- 서수(Ordinal) 변환 함수 ---
def get_ordinal(n):
    if 11 <= n % 100 <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

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
        
        # 필수 컬럼 누락 시 기본값 채우기
        for col, default in {'password': '0000', 'gender': '남성', 'memo': ''}.items():
            if col not in raw_df.columns:
                raw_df[col] = default
        return raw_df
    except Exception:
        return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo'])

def get_comments():
    try:
        c_df = conn.read(worksheet="comments", ttl=0)
        return c_df if c_df is not None else pd.DataFrame(columns=['name', 'comment', 'date'])
    except:
        return pd.DataFrame(columns=['name', 'comment', 'date'])

df = get_full_data()
comments_df = get_comments()

if 'is_auth' not in st.session_state:
    st.session_state.is_auth = False
    st.session_state.user_name = ""
    st.session_state.user_gender = "남성"

st.markdown("<div id='link_to_top'></div>", unsafe_allow_html=True)
st.title("🏋️ 1RM을 기억해")

# --- 3. 환영 메시지 ---
if st.session_state.is_auth:
    col_welcome, col_logout = st.columns([3, 1])
    with col_welcome:
        st.subheader(f"👋 {st.session_state.user_name}님")
    with col_logout:
        if st.button("로그아웃", use_container_width=True):
            for key in ['is_auth', 'user_name', 'user_gender']:
                st.session_state[key] = False if key == 'is_auth' else ""
            st.rerun()
    st.divider()

# --- 4. 실시간 전체 랭킹 ---
st.subheader("🏆 박스 실시간 랭킹 (전체)")
selected_rank_exercise = st.selectbox("랭킹 종목 선택", exercise_list, index=0)

rank_df = df[df['exercise'] == selected_rank_exercise].copy()
rank_df['weight'] = pd.to_numeric(rank_df['weight'], errors='coerce')
best_rank_df = rank_df.sort_values('weight', ascending=False).drop_duplicates('name')

with st.expander(f"🔥 {selected_rank_exercise} 전체 순위", expanded=True):
    if not best_rank_df.empty:
        col_m, col_f = st.columns(2)
        
        def display_rank_column(data, title):
            st.markdown(f"#### {title}")
            sorted_data = data.sort_values(by='weight', ascending=False)
            if sorted_data.empty:
                st.write("기록 없음")
            else:
                for i, row in enumerate(sorted_data.itertuples(), 1):
                    # 순위 아이콘 설정
                    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"**{get_ordinal(i)}**")
                    # 본인 강조
                    name_style = f"**<span style='color:#29b5e8;'>{row.name}</span>**" if st.session_state.user_name == row.name else f"{row.name}"
                    st.markdown(f"{medal} {name_style} : `{row.weight} lb`", unsafe_allow_html=True)

        with col_m:
            display_rank_column(best_rank_df[best_rank_df['gender'] == "남성"], "♂️ Male")
        with col_f:
            display_rank_column(best_rank_df[best_rank_df['gender'] == "여성"], "♀️ Female")
    else:
        st.write("첫 주인공이 되어보세요!")

st.divider()

# --- 5. 실시간 응원 한마디 (예시 문구 업데이트) ---
st.subheader("💬 실시간 응원 한마디")

if st.session_state.is_auth:
    with st.form(key="comment_form", clear_on_submit=True):
        col_c1, col_c2 = st.columns([4, 1])
        with col_c1:
            # 재효님 성함이 들어간 찰진 예시 문구!
            new_comment = st.text_input(
                f"{st.session_state.user_name}님, 한마디!", 
                placeholder="예: 재효님 클린 미쳤네요ㄷㄷ" 
            )
        with col_c2:
            submit_comment = st.form_submit_button("등록")
        
        if submit_comment and new_comment.strip():
            kst_now = datetime.now() + timedelta(hours=9)
            new_c_row = pd.DataFrame([{
                "name": st.session_state.user_name,
                "comment": new_comment,
                "date": kst_now.strftime("%m/%d %H:%M")
            }])
            # 시트 업데이트
            all_comments = pd.concat([comments_df, new_c_row], ignore_index=True)
            conn.update(worksheet="comments", data=all_comments)
            
            st.success("🔥 응원 등록 완료! 파이팅입니다!")
            time.sleep(0.8)
            st.rerun()
            
st.divider()

# --- 6. 사용자 인증 ---
if not st.session_state.is_auth:
    st.subheader("👤 사용자 인증")
    mode = st.radio("로그인 방식", ["기존 사용자", "신규 등록"], horizontal=True)
    if mode == "기존 사용자":
        u_list = sorted(df['name'].dropna().unique().tolist()) if not df.empty else []
        sel_name = st.selectbox("이름 선택", ["선택하세요"] + u_list)
        pw_in = st.text_input("비밀번호", type="password")
        if st.button("로그인", use_container_width=True) and sel_name != "선택하세요":
            stored_pw = str(df[df['name'] == sel_name].iloc[-1]['password']).strip().replace("'", "")
            if pw_in.strip() == stored_pw:
                st.session_state.is_auth, st.session_state.user_name = True, sel_name
                st.session_state.user_gender = df[df['name'] == sel_name].iloc[-1]['gender']
                st.rerun()
            else: st.error("비밀번호 불일치")
    else:
        r1, r2 = st.columns(2)
        n_name = r1.text_input("새 이름")
        n_gender = r2.radio("성별", ["남성", "여성"], horizontal=True)
        n_pw = st.text_input("비밀번호 설정", type="password")
        if st.button("등록 및 로그인", use_container_width=True) and n_name and n_pw:
            st.session_state.is_auth, st.session_state.user_name, st.session_state.user_gender = True, n_name, n_gender
            st.session_state.temp_pw = f"'{n_pw}"
            st.rerun()

# --- 7. 개인 차트 및 상세 기록 ---
if st.session_state.is_auth:
    my_data = df[df['name'] == st.session_state.user_name].copy()
    my_data['weight'] = pd.to_numeric(my_data['weight'], errors='coerce')
    
    if not my_data.empty:
        chart_df = my_data.sort_values('weight', ascending=False).drop_duplicates('exercise').copy()
        chart_df['exercise_short'] = chart_df['exercise'].map(rename_map).fillna(chart_df['exercise'])
        st.write(f"📊 {st.session_state.user_name}님의 최고 기록")
        chart = alt.Chart(chart_df).encode(
            y=alt.Y('exercise_short:N', sort='-x', title=None),
            x=alt.X('weight:Q', title="중량 (lbs)")
        ).mark_bar(color="#29b5e8", cornerRadiusEnd=5)
        st.altair_chart(chart, use_container_width=True)

    # --- 8. 기록 업데이트 ---
    st.subheader("💪 오늘의 기록")
    save_ex = st.selectbox("종목 선택", exercise_list)
    ex_rec = my_data[my_data['exercise'] == save_ex]
    p_max = float(ex_rec['weight'].max()) if not ex_rec.empty else 0.0
    
    if p_max > 0:
        st.info(f"💡 {save_ex} 최고: **{p_max} lbs**")
        with st.expander("📊 퍼센트별 중량"):
            cols = st.columns(3)
            for i, p in enumerate(range(70, 101, 5)):
                cols[i%3].metric(f"{p}%", f"{round((p_max * p / 100) / 2.5) * 2.5} lb")
    
    new_w = st.number_input("중량 (lbs)", value=p_max, step=5.0)
    new_m = st.text_input("메모", placeholder="컨디션 등")
    
    if st.button("🏋️ 기록 저장", use_container_width=True) and new_w > 0:
        kst_now = datetime.now() + timedelta(hours=9)
        u_data = df[df['name'] == st.session_state.user_name]
        f_pw = str(u_data.iloc[-1]['password']) if not u_data.empty else st.session_state.get('temp_pw', '0000')
        if not str(f_pw).startswith("'"): f_pw = f"'{f_pw}"
        
        new_rec = pd.DataFrame([{"name": st.session_state.user_name, "exercise": save_ex, "weight": new_w, 
                                 "date": kst_now.strftime("%Y-%m-%d"), "password": f_pw, 
                                 "gender": st.session_state.user_gender, "memo": new_m}])
        conn.update(worksheet="sheet1", data=pd.concat([df, new_rec], ignore_index=True))
        st.balloons()
        time.sleep(1)
        st.rerun()

    st.markdown("<br><a href='#link_to_top' style='text-decoration:none;'><button style='width:100%; border-radius:10px; border:1px solid #ddd; background-color:#f9f9f9; padding:10px; cursor:pointer;'>🔝 맨 위로 가기</button></a>", unsafe_allow_html=True)

# --- 9. 관리자 ---
with st.expander("🛠️ Admin"):
    if st.text_input("Key", type="password") == "5207":
        st.dataframe(df)


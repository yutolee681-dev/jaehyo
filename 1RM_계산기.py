import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import time

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="wide") # wide 모드로 변경해서 랭킹 가독성 확보

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
        for col, default in {'password': '0000', 'gender': '남성', 'memo': ''}.items():
            if col not in raw_df.columns: raw_df[col] = default
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
    st.session_state.is_auth, st.session_state.user_name, st.session_state.user_gender = False, "", "남성"

st.markdown("<div id='link_to_top'></div>", unsafe_allow_html=True)
st.title("🏋️ 1RM을 기억해")

# --- 3. 환영 메시지 및 로그아웃 ---
if st.session_state.is_auth:
    col_w, col_l = st.columns([5, 1])
    col_w.subheader(f"👋 {st.session_state.user_name}님 환영합니다!")
    if col_l.button("로그아웃", use_container_width=True):
        st.session_state.is_auth = False
        st.rerun()
    st.divider()

# --- 4. 실시간 전체 랭킹 (한 그리드에 남/여 병렬 배치) ---
st.subheader("🏆 박스 실시간 랭킹")
selected_rank_exercise = st.selectbox("랭킹 종목 선택", exercise_list, index=0)
rank_df = df[df['exercise'] == selected_rank_exercise].copy()
rank_df['weight'] = pd.to_numeric(rank_df['weight'], errors='coerce')
best_rank_df = rank_df.sort_values('weight', ascending=False).drop_duplicates('name')

# ✅ 요청하신 한 그리드(남성 왼쪽, 여성 오른쪽) 배치
rank_col1, rank_col2 = st.columns(2)

def display_rank_box(data, title, icon):
    st.markdown(f"#### {icon} {title}")
    sd = data.sort_values(by='weight', ascending=False)
    if sd.empty:
        st.info("등록된 기록이 없습니다.")
    else:
        for i, row in enumerate(sd.itertuples(), 1):
            medal = {1:"🥇", 2:"🥈", 3:"🥉"}.get(i, f"**{get_ordinal(i)}**")
            name_style = f"color:#29b5e8; font-weight:bold;" if st.session_state.user_name == row.name else ""
            st.markdown(f"{medal} <span style='{name_style}'>{row.name}</span> : `{row.weight} lb`", unsafe_allow_html=True)

with rank_col1:
    display_rank_box(best_rank_df[best_rank_df['gender'] == "남성"], "Male", "♂️")

with rank_col2:
    display_rank_box(best_rank_df[best_rank_df['gender'] == "여성"], "Female", "♀️")

st.divider()

# --- 5. 실시간 응원 댓글 ---
st.subheader("💬 실시간 응원 한마디")
if st.session_state.is_auth:
    with st.form(key="comment_form", clear_on_submit=True):
        c1, c2 = st.columns([4, 1])
        new_comment = c1.text_input(f"{st.session_state.user_name}님, 응원 한마디 남겨주세요!", placeholder="예: 재효님 클린 미쳤네요ㄷㄷ")
        if c2.form_submit_button("등록") and new_comment:
            kst_now = datetime.now() + timedelta(hours=9)
            new_row = pd.DataFrame([{"name": st.session_state.user_name, "comment": new_comment, "date": kst_now.strftime("%m/%d %H:%M")}])
            conn.update(worksheet="comments", data=pd.concat([comments_df, new_row], ignore_index=True))
            st.success("🔥 응원 등록 완료!"); time.sleep(0.5); st.rerun()
else:
    st.warning("🔒 로그인하셔야 댓글을 쓰실 수 있습니다.")

if not comments_df.empty:
    with st.expander("최근 댓글 보기", expanded=True):
        for idx, row in comments_df.sort_index(ascending=False).head(10).iterrows():
            cc1, cc2 = st.columns([5, 1])
            cc1.markdown(f"**{row['name']}** <small style='color:gray;'>{row['date']}</small>", unsafe_allow_html=True)
            cc1.info(row['comment'])
            if st.session_state.is_auth and st.session_state.user_name == row['name']:
                if cc2.button("🗑️", key=f"del_{idx}"):
                    conn.update(worksheet="comments", data=comments_df.drop(idx)); st.rerun()

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
        n_name, n_pw = r1.text_input("새 이름"), st.text_input("비밀번호 설정", type="password")
        n_gender = r2.radio("성별", ["남성", "여성"], horizontal=True)
        if st.button("등록 및 로그인", use_container_width=True) and n_name and n_pw:
            st.session_state.is_auth, st.session_state.user_name, st.session_state.user_gender = True, n_name, n_gender
            st.session_state.temp_pw = f"'{n_pw}"; st.rerun()

# --- 7. 개인 차트 (숫자 라벨 포함) ---
if st.session_state.is_auth:
    my_data = df[df['name'] == st.session_state.user_name].copy()
    my_data['weight'] = pd.to_numeric(my_data['weight'], errors='coerce')
    if not my_data.empty:
        chart_df = my_data.sort_values('weight', ascending=False).drop_duplicates('exercise').copy()
        chart_df['exercise_short'] = chart_df['exercise'].map(rename_map).fillna(chart_df['exercise'])
        st.write(f"📊 {st.session_state.user_name}님의 최고 기록 현황")
        
        base = alt.Chart(chart_df).encode(
            y=alt.Y('exercise_short:N', sort='-x', title=None),
            x=alt.X('weight:Q', title="lbs")
        )
        bars = base.mark_bar(color="#29b5e8", cornerRadiusEnd=5)
        text = base.mark_text(align='right', dx=-5, color='white', fontWeight='bold').encode(text=alt.Text('weight:Q', format='.0f'))
        st.altair_chart(bars + text, use_container_width=True)
        
        with st.expander("📋 나의 상세 기록 전체 보기"):
            my_exs = sorted(my_data['exercise'].unique().tolist())
            sel_ex = st.selectbox("종목 필터", ["전체 보기"] + my_exs)
            disp_df = my_data if sel_ex == "전체 보기" else my_data[my_data['exercise'] == sel_ex]
            st.dataframe(disp_df[['date', 'exercise', 'weight', 'memo']].sort_values('date', ascending=False), hide_index=True, use_container_width=True)

    st.divider()

    # --- 8. 기록 업데이트 & 퍼센트 계산기 (UI 개선) ---
    st.subheader("💪 오늘의 기록 업데이트")
    save_ex = st.selectbox("업데이트할 종목 선택", exercise_list)
    p_max = float(my_data[my_data['exercise'] == save_ex]['weight'].max()) if not my_data[my_data['exercise'] == save_ex].empty else 0.0
    
    if p_max > 0:
        st.info(f"💡 {save_ex} 나의 최고 기록: **{p_max} lbs**")
        with st.expander("📊 퍼센트별 중량 가이드 (5% 단위)", expanded=True):
            # ✅ 요청하신 디테일: 퍼센트는 작게, 중량(lb)은 크고 굵게!
            percents = [50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
            m_col1, m_col2 = st.columns(2)
            for i, p in enumerate(percents):
                calc_w = round((p_max * p / 100) / 2.5) * 2.5
                target_col = m_col1 if i % 2 == 0 else m_col2
                # HTML 커스텀 스타일 적용
                target_col.markdown(f"<small style='color:gray;'>{p}%</small> <b style='font-size:1.2rem;'>{calc_w}</b> <small>lb</small>", unsafe_allow_html=True)
    
    new_w = st.number_input("기록 입력 (lbs)", value=p_max, step=5.0)
    new_m = st.text_input("메모 (선택사항)", placeholder="예: 컨디션 좋음, 노랩 주의")
    if st.button("🏋️ 새로운 기록 저장하기", use_container_width=True) and new_w > 0:
        kst_now = datetime.now() + timedelta(hours=9)
        u_data = df[df['name'] == st.session_state.user_name]
        f_pw = str(u_data.iloc[-1]['password']) if not u_data.empty else st.session_state.get('temp_pw', '0000')
        if not str(f_pw).startswith("'"): f_pw = f"'{f_pw}"
        new_rec = pd.DataFrame([{"name": st.session_state.user_name, "exercise": save_ex, "weight": new_w, "date": kst_now.strftime("%Y-%m-%d"), "password": f_pw, "gender": st.session_state.user_gender, "memo": new_m}])
        conn.update(worksheet="sheet1", data=pd.concat([df, new_rec], ignore_index=True))
        st.balloons(); time.sleep(1); st.rerun()

# --- 9. Admin ---
st.divider()
with st.expander("🛠️ 시스템 관리자"):
    if st.text_input("관리자 인증 키", type="password") == "5207":
        st.write("### 📂 전체 운동 기록 데이터")
        st.dataframe(df)
        st.write("### 💬 전체 응원 댓글 데이터")
        st.dataframe(comments_df)

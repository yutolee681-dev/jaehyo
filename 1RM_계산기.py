import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import time

with st.sidebar:
    st.title("⚙️ 설정")
    if st.button("🔄 데이터 새로고침", use_container_width=True):
        st.rerun()
    st.info("데이터가 실시간으로 보이지 않으면 위 버튼을 눌러주세요.")


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
        
        required_cols = {'password': '0000', 'gender': '남성', 'memo': ''}
        for col, default in required_cols.items():
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

# --- 3. 최상단 환영 메시지 및 로그아웃 수정 ---
if st.session_state.is_auth:
    col_welcome, col_refresh, col_logout = st.columns([2, 1, 1]) # 컬럼 추가
    with col_welcome:
        st.subheader(f"👋 {st.session_state.user_name}님")
    with col_refresh:
        # 새로고침 버튼
        if st.button("🔄 새로고침", use_container_width=True):
            st.cache_data.clear() # 캐시된 데이터가 있다면 삭제
            st.rerun()
    with col_logout:
        if st.button("로그아웃", use_container_width=True):
            st.session_state.is_auth = False
            st.session_state.user_name = ""
            st.rerun()
    st.divider()

# --- 4. 실시간 전체 랭킹 (표 방식 레이아웃) ---
st.subheader("🏆 박스 실시간 랭킹 (전체)")
selected_rank_exercise = st.selectbox("랭킹 종목 선택", exercise_list, index=0)

rank_df = df[df['exercise'] == selected_rank_exercise].copy()
rank_df['weight'] = pd.to_numeric(rank_df['weight'], errors='coerce')
best_rank_df = rank_df.sort_values('weight', ascending=False).drop_duplicates('name')

with st.expander(f"🔥 {selected_rank_exercise} 전체 순위 보기", expanded=True):
    if not best_rank_df.empty:
        # 남/여 데이터 분리
        m_data = best_rank_df[best_rank_df['gender'] == "남성"].sort_values('weight', ascending=False)
        f_data = best_rank_df[best_rank_df['gender'] == "여성"].sort_values('weight', ascending=False)
        
        # 최대 행 수 결정
        max_rows = max(len(m_data), len(f_data))
        
        # HTML 테이블 생성
        html_code = f"""
        <table style="width:100%; border-collapse: collapse; font-size: 0.8rem; table-layout: fixed;">
            <thead>
                <tr style="border-bottom: 1px solid #444;">
                    <th style="text-align: left; padding: 5px;">♂️ Male</th>
                    <th style="text-align: left; padding: 5px;">♀️ Female</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for i in range(max_rows):
            # 남성 열
            if i < len(m_data):
                row_m = m_data.iloc[i]
                medal_m = "🥇" if i==0 else "🥈" if i==1 else "🥉" if i==2 else f"{get_ordinal(i+1)}"
                name_m_style = "color:#29b5e8; font-weight:bold;" if st.session_state.user_name == row_m['name'] else ""
                m_col = f"<td>{medal_m} <span style='{name_m_style}'>{row_m['name']}</span> <b style='font-size:0.7rem;'>{row_m['weight']}</b></td>"
            else:
                m_col = "<td>-</td>"
                
            # 여성 열
            if i < len(f_data):
                row_f = f_data.iloc[i]
                medal_f = "🥇" if i==0 else "🥈" if i==1 else "🥉" if i==2 else f"{get_ordinal(i+1)}"
                name_f_style = "color:#29b5e8; font-weight:bold;" if st.session_state.user_name == row_f['name'] else ""
                f_col = f"<td>{medal_f} <span style='{name_f_style}'>{row_f['name']}</span> <b style='font-size:0.7rem;'>{row_f['weight']}</b></td>"
            else:
                f_col = "<td>-</td>"
            
            html_code += f"<tr>{m_col}{f_col}</tr>"
            
        html_code += "</tbody></table>"
        st.markdown(html_code, unsafe_allow_html=True)
    else:
        st.write("첫 주인공이 되어보세요!")
        
st.divider()

# --- 5. 실시간 응원 댓글 ---
st.subheader("💬 실시간 응원 한마디")

if st.session_state.is_auth:
    with st.form(key="comment_form", clear_on_submit=True):
        col_c1, col_c2 = st.columns([4, 1])
        with col_c1:
            new_comment = st.text_input(f"{st.session_state.user_name}님, 한마디!", placeholder="예: 재효님 클린 미쳤네요ㄷㄷ")
        with col_c2:
            submit_comment = st.form_submit_button("등록")
        
        if submit_comment and new_comment:
            kst_now = datetime.now() + timedelta(hours=9)
            new_c_row = pd.DataFrame([{
                "name": st.session_state.user_name,
                "comment": new_comment,
                "date": kst_now.strftime("%m/%d %H:%M")
            }])
            all_comments = pd.concat([comments_df, new_c_row], ignore_index=True)
            conn.update(worksheet="comments", data=all_comments)
            st.success("댓글 등록 완료!")
            time.sleep(1)
            st.rerun()
else:
    st.info("로그인하면 댓글을 남길 수 있습니다.")

if not comments_df.empty:
    with st.expander("최근 댓글 보기", expanded=True):
        display_comments = comments_df.sort_index(ascending=False).head(10)
        for idx, row in display_comments.iterrows():
            c_col1, c_col2 = st.columns([5, 1])
            with c_col1:
                st.markdown(f"**{row['name']}** <small style='color:gray;'>{row['date']}</small>", unsafe_allow_html=True)
                st.info(row['comment'])
            with c_col2:
                if st.session_state.is_auth and st.session_state.user_name == row['name']:
                    if st.button("🗑️", key=f"del_{idx}"):
                        updated_comments = comments_df.drop(idx)
                        conn.update(worksheet="comments", data=updated_comments)
                        st.warning("삭제됨")
                        time.sleep(1)
                        st.rerun()

st.divider()

# --- 6. 사용자 인증 ---
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
                    stored_pw = str(user_rows.iloc[-1]['password']).strip().replace("'", "") # 따옴표 제거 후 비교
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
                    st.session_state.temp_pw = f"'{new_pw}" # '0' 보존을 위한 접두어
                    st.rerun()

# --- 7. 개인 차트 및 상세 기록 (그래프 & 삭제 기능 추가) ---
if st.session_state.is_auth:
    my_data = df[df['name'] == st.session_state.user_name].copy()
    my_data['weight'] = pd.to_numeric(my_data['weight'], errors='coerce')
    my_data['date'] = pd.to_datetime(my_data['date']).dt.date # 날짜 형식 통일
    
    if not my_data.empty:
        # (1) 최고 기록 바 차트 (기존 유지)
        chart_df = my_data.sort_values('weight', ascending=False).drop_duplicates('exercise').copy()
        chart_df['exercise_short'] = chart_df['exercise'].map(rename_map).fillna(chart_df['exercise'])
        st.write(f"📊 {st.session_state.user_name}님의 종목별 최고 기록")
        
        base = alt.Chart(chart_df).encode(
            y=alt.Y('exercise_short:N', sort='-x', title=None),
            x=alt.X('weight:Q', title="중량 (lbs)")
        )
        bars = base.mark_bar(color="#29b5e8", cornerRadiusEnd=5)
        text = base.mark_text(align='right', dx=-5, color='white', fontWeight='bold').encode(text=alt.Text('weight:Q', format='.0f'))
        st.altair_chart(bars + text, use_container_width=True)

        # (2) 성장 그래프 (새로 추가)
        st.write(f"📈 기록 성장 추이")
        graph_exercise = st.selectbox("추이를 볼 종목 선택", exercise_list, key="graph_ex")
        ex_history = my_data[my_data['exercise'] == graph_exercise].sort_values('date')
        
        if not ex_history.empty:
            line_chart = alt.Chart(ex_history).mark_line(point=True, color="#ff4b4b").encode(
                x=alt.X('date:T', title="날짜"),
                y=alt.Y('weight:Q', title="중량 (lbs)", scale=alt.Scale(zero=False)),
                tooltip=['date', 'weight', 'memo']
            ).properties(height=300)
            st.altair_chart(line_chart, use_container_width=True)
        else:
            st.info(f"{graph_exercise} 기록이 아직 없습니다.")

        # (3) 상세 기록 조회 및 삭제 (수정)
        with st.expander("📋 상세 기록 조회 및 삭제"):
            my_exercises = sorted(my_data['exercise'].unique().tolist())
            selected_history_ex = st.selectbox("조회할 종목", ["전체 보기"] + my_exercises, key="history_filter")
            
            history_display_df = my_data if selected_history_ex == "전체 보기" else my_data[my_data['exercise'] == selected_history_ex]
            history_display_df = history_display_df.sort_values(by=['date', 'exercise'], ascending=[False, True])
            
            # 삭제를 위한 인터페이스
            for idx, row in history_display_df.iterrows():
                col1, col2, col3 = st.columns([2, 1, 0.5])
                with col1:
                    st.markdown(f"**{row['date']}** | {row['exercise']}")
                    if row['memo']: st.caption(f"📝 {row['memo']}")
                with col2:
                    st.markdown(f"`{row['weight']} lb`")
                with col3:
                    # 각 행 옆에 삭제 버튼 배치
                    if st.button("🗑️", key=f"record_del_{idx}"):
                        # 원본 df에서 해당 인덱스 삭제 (df는 전체 데이터프레임)
                        updated_df = df.drop(idx)
                        conn.update(worksheet="sheet1", data=updated_df)
                        st.warning("기록이 삭제되었습니다.")
                        time.sleep(1)
                        st.rerun()
                st.divider()

    st.divider()

    st.markdown("<br><a href='#link_to_top' style='text-decoration:none;'><button style='width:100%; border-radius:10px; border:1px solid #ddd; background-color:#f9f9f9; padding:10px; cursor:pointer;'>🔝 맨 위로 가기</button></a>", unsafe_allow_html=True)

# --- 9. 관리자 모드 ---
with st.expander("🛠️ Admin"):
    admin_pw = st.text_input("Key", type="password")
    if admin_pw == "5207":
        st.dataframe(df)








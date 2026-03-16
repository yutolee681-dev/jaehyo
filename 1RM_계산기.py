import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import time
import urllib.parse

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

# --- 2. [핵심 변경] CSV 직접 호출 및 데이터 로드 함수 ---
# GSheetsConnection 대신 직접 URL을 통해 데이터를 가져옵니다.
SHEET_ID = "1ekqS81gko96DVkrFsBkg2-bQiF3oAcHkXd02oHJQ1R4"

def get_data_via_csv(worksheet_name="Sheet1"):
    try:
        # 캐시 방지를 위해 현재 시간을 URL 뒤에 붙임
        cb = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={worksheet_name}&cb={cb}"
        
        # 모든 데이터를 일단 문자열로 읽고 빈 값을 처리
        data = pd.read_csv(url).fillna("")
        
        # 컬럼명 소문자 정리
        data.columns = [c.lower().strip() for c in data.columns]
        
        # 비밀번호 숫자(.0) 제거 로직
        if 'password' in data.columns:
            def clean_pw(val):
                s = str(val).replace("'", "").strip()
                if s.endswith('.0'): s = s[:-2]
                return s
            data['password'] = data['password'].apply(clean_pw)
            
        return data
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

# 쓰기 작업을 위해 기존 커넥션은 유지하되 읽기는 위 함수를 사용합니다.
from streamlit_gsheets import GSheetsConnection
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"

# 데이터 로드
df = get_data_via_csv("Sheet1")
comments_df = get_data_via_csv("comments")

# 세션 상태 초기화
if 'is_auth' not in st.session_state:
    st.session_state.is_auth = False
    st.session_state.user_name = ""
    st.session_state.user_gender = "남성"

st.markdown("<div id='link_to_top'></div>", unsafe_allow_html=True)
st.title("🏋️ 1RM을 기억해")

# --- 3. 최상단 환영 메시지 및 로그아웃 ---
if st.session_state.is_auth:
    col_welcome, col_refresh, col_logout = st.columns([2, 1, 1])
    with col_welcome:
        st.markdown(f"👋 **{st.session_state.user_name}**님")
    with col_refresh:
        if st.button("🔄 갱신", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col_logout:
        if st.button("로그아웃", use_container_width=True):
            st.session_state.is_auth = False
            st.session_state.user_name = ""
            st.rerun()
    st.divider()

# --- 4. 실시간 전체 랭킹 ---
st.subheader("🏆 박스 실시간 랭킹 (전체)")
selected_rank_exercise = st.selectbox("랭킹 종목 선택", exercise_list, index=0)

if not df.empty and 'exercise' in df.columns:
    rank_df = df[df['exercise'] == selected_rank_exercise].copy()
    rank_df['weight'] = pd.to_numeric(rank_df['weight'], errors='coerce')
    best_rank_df = rank_df.sort_values('weight', ascending=False).drop_duplicates('name')

    with st.expander(f"🔥 {selected_rank_exercise} 전체 순위 보기", expanded=True):
        if not best_rank_df.empty:
            m_data = best_rank_df[best_rank_df['gender'] == "남성"].sort_values('weight', ascending=False)
            f_data = best_rank_df[best_rank_df['gender'] == "여성"].sort_values('weight', ascending=False)
            max_rows = max(len(m_data), len(f_data))
            
            html_code = """<table style="width:100%; border-collapse: collapse; font-size: 0.8rem; table-layout: fixed;">
                           <thead><tr style="border-bottom: 1px solid #444;"><th style="text-align: left; padding: 5px;">♂️ Male</th>
                           <th style="text-align: left; padding: 5px;">♀️ Female</th></tr></thead><tbody>"""
            for i in range(max_rows):
                m_col = f"<td>{get_ordinal(i+1)} {m_data.iloc[i]['name']} <b>{m_data.iloc[i]['weight']}</b></td>" if i < len(m_data) else "<td>-</td>"
                f_col = f"<td>{get_ordinal(i+1)} {f_data.iloc[i]['name']} <b>{f_data.iloc[i]['weight']}</b></td>" if i < len(f_data) else "<td>-</td>"
                html_code += f"<tr>{m_col}{f_col}</tr>"
            html_code += "</tbody></table>"
            st.markdown(html_code, unsafe_allow_html=True)
        else:
            st.write("기록이 없습니다.")
st.divider()

# --- 5. 실시간 응원 한마디 ---
st.subheader("💬 실시간 응원 한마디")
if st.session_state.is_auth:
    with st.form(key="comment_form", clear_on_submit=True):
        col_c1, col_c2 = st.columns([4, 1])
        with col_c1:
            new_comment = st.text_input(f"{st.session_state.user_name}님, 한마디!", placeholder="오늘 컨디션 최고! 🔥")
        with col_c2:
            submit_comment = st.form_submit_button("등록")
        if submit_comment and new_comment:
            kst_now = datetime.now() + timedelta(hours=9)
            new_c_row = pd.DataFrame([{"name": st.session_state.user_name, "comment": new_comment, "date": kst_now.strftime("%m/%d %H:%M")}])
            all_comments = pd.concat([comments_df, new_c_row], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="comments", data=all_comments)
            st.rerun()

if not comments_df.empty:
    with st.expander("📂 최근 응원 메시지", expanded=True):
        display_comments = comments_df.sort_index(ascending=False).head(10)
        for idx, row in display_comments.iterrows():
            st.markdown(f"**{row['name']}** ({row['date']}): {row['comment']}")
st.divider()

# --- 6. [중요] 사용자 인증 (재효님 마스터키 포함) ---
if not st.session_state.is_auth:
    st.subheader("👤 사용자 인증")
    input_mode = st.radio("로그인 방식", ["기존 사용자", "신규 등록"], horizontal=True)
    
    if input_mode == "기존 사용자":
        user_list = sorted(df['name'].dropna().astype(str).str.strip().unique().tolist()) if not df.empty else []
        selected_name = st.selectbox("이름 선택", ["선택하세요"] + user_list)
        
        if selected_name != "선택하세요":
            pw_input = st.text_input("비밀번호", type="password")
            if st.button("로그인", use_container_width=True):
                # 재효님 마스터키
                if selected_name == "재효" and pw_input.strip() == "5207":
                    st.session_state.update({"is_auth": True, "user_name": "재효", "user_gender": "남성"})
                    st.success("재효님 환영합니다! 🔥")
                    time.sleep(0.5); st.rerun()
                
                # 일반 로그인
                user_rows = df[df['name'].astype(str).str.strip() == selected_name]
                if not user_rows.empty:
                    clean_sheet_pw = str(user_rows.iloc[-1]['password']).strip()
                    if pw_input.strip() == clean_sheet_pw:
                        st.session_state.update({"is_auth": True, "user_name": selected_name, "user_gender": user_rows.iloc[-1]['gender']})
                        st.success("로그인 성공!")
                        time.sleep(0.5); st.rerun()
                    else:
                        st.error(f"비밀번호 불일치 (인식된 값: {clean_sheet_pw})")
    else:
        # 신규 등록
        reg_col1, reg_col2 = st.columns(2)
        new_name = reg_col1.text_input("새 이름")
        new_gender = reg_col2.radio("성별", ["남성", "여성"], horizontal=True)
        new_pw = st.text_input("비밀번호 설정", type="password")
        if st.button("등록 및 로그인", use_container_width=True) and new_name and new_pw:
            st.session_state.update({"is_auth": True, "user_name": new_name.strip(), "user_gender": new_gender, "temp_pw": f"'{new_pw}"})
            st.rerun()

# --- 7. 개인 데이터 분석 통합 ---
if st.session_state.is_auth:
    my_data = df[df['name'] == st.session_state.user_name].copy()
    my_data['weight'] = pd.to_numeric(my_data['weight'], errors='coerce')
    
    if not my_data.empty:
        st.subheader("📊 나의 퍼포먼스 리포트")
        tab1, tab2, tab3 = st.tabs(["🏆 최고 기록", "📈 성장률 분석", "📋 전체 히스토리"])

        with tab1:
            chart_df = my_data.sort_values('weight', ascending=False).drop_duplicates('exercise').copy()
            chart_df['exercise_short'] = chart_df['exercise'].map(rename_map).fillna(chart_df['exercise'])
            base = alt.Chart(chart_df).encode(
                y=alt.Y('exercise_short:N', sort='-x', title=None),
                x=alt.X('weight:Q', title="중량 (lbs)")
            )
            st.altair_chart(base.mark_bar(color="#29b5e8") + base.mark_text(align='right', dx=-5, color='white'), use_container_width=True)

        with tab2:
            unique_ex = sorted(my_data['exercise'].unique())
            cols = st.columns(2)
            for i, ex in enumerate(unique_ex):
                ex_data = my_data[my_data['exercise'] == ex].sort_values('date')
                diff = ex_data.iloc[-1]['weight'] - ex_data.iloc[0]['weight']
                cols[i % 2].metric(label=ex, value=f"{ex_data.iloc[-1]['weight']} lbs", delta=f"{diff} lbs")

        with tab3:
            # --- 목록형 히스토리 (메모 출력 보강) ---
            st.write("📝 기록을 클릭하면 수정/삭제할 수 있습니다.")
            
            # 1. 종목 필터
            all_my_ex = sorted(my_data['exercise'].unique().tolist())
            filter_ex = st.selectbox("종목 선택", ["전체 보기"] + all_my_ex, key="history_filter")
            
            # 2. 데이터 필터링 및 최신순 정렬
            display_df = my_data.copy()
            if filter_ex != "전체 보기":
                display_df = display_df[display_df['exercise'] == filter_ex]
            
            display_df = display_df.sort_values(by='date', ascending=False)

            # 3. 리스트 렌더링
            if not display_df.empty:
                for idx, row in display_df.iterrows():
                    # 메모가 있으면 표시, 없으면 '없음' 표시
                    memo_text = row['memo'] if str(row['memo']).strip() != "" else "내용 없음"
                    
                    # 목록 제목에 메모 요약 추가
                    with st.expander(f"📅 {row['date']} | {row['exercise']} | {row['weight']} lbs"):
                        st.markdown(f"**💬 기록된 메모:** {memo_text}")
                        st.divider()
                        
                        st.markdown("#### ✏️ 기록 수정")
                        e_col1, e_col2 = st.columns(2)
                        with e_col1:
                            new_w = st.number_input("중량(lbs)", value=float(row['weight']), step=5.0, key=f"nw_{idx}")
                        with e_col2:
                            # 메모 수정 칸
                            new_m = st.text_input("메모 수정", value=str(row['memo']), key=f"nm_{idx}")
                        
                        b_col1, b_col2 = st.columns(2)
                        with b_col1:
                            if st.button("💾 수정 저장", key=f"sv_{idx}", use_container_width=True):
                                # 수정된 데이터 반영
                                df.at[idx, 'weight'] = new_w
                                df.at[idx, 'memo'] = new_m
                                
                                # [수정] 데이터 저장 로직 강화
                                # gsheets 라이브러리가 헷갈리지 않게 ID와 시트 이름을 정확히 명시
                                conn.update(
                                    spreadsheet=SHEET_ID,  # URL 대신 ID 사용
                                    worksheet="Sheet1", 
                                    data=df
                                )
                                st.success("수정 완료! 🔄")
                                time.sleep(0.5)
                                st.rerun()
                        
                        with b_col2:
                            if st.button("🗑️ 기록 삭제", key=f"dc_{idx}", use_container_width=True):
                                # 해당 행 삭제 후 인덱스 초기화 없이 원본 df 업데이트
                                final_df = df.drop(idx)
                                
                                conn.update(
                                    spreadsheet=SHEET_ID, 
                                    worksheet="Sheet1", 
                                    data=final_df
                                )
                                st.warning("기록이 삭제되었습니다.")
                                time.sleep(0.5)
                                st.rerun()
            else:
                st.info("해당 종목의 기록이 없습니다.")
    st.divider()

# --- 8. 오늘의 기록 업데이트 ---
if st.session_state.is_auth:
    st.subheader("💪 오늘의 기록 업데이트")
    save_exercise = st.selectbox("종목 선택", exercise_list, key="update_ex")
    ex_record = my_data[my_data['exercise'] == save_exercise]
    prev_max = float(ex_record['weight'].max()) if not ex_record.empty else 0.0

    with st.form(key="record_form"):
        new_weight = st.number_input("성공 중량 (lbs)", value=prev_max)
        new_memo = st.text_input("메모")
        if st.form_submit_button("🔥 기록 저장"):
            kst_now = datetime.now() + timedelta(hours=9)
            new_record = pd.DataFrame([{"name": st.session_state.user_name, "exercise": save_exercise, "weight": new_weight, "date": kst_now.strftime("%Y-%m-%d"), "password": f"'{pw_input}" if 'pw_input' in locals() else "'0000", "gender": st.session_state.user_gender, "memo": new_memo}])
            updated_df = pd.concat([df, new_record], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated_df)
            st.success("저장 완료!")
            time.sleep(0.5); st.rerun()

# --- 9. 관리자 모드 ---
with st.expander("🛠️ Admin"):
    if st.text_input("Key", type="password") == "5207":
        st.dataframe(df)

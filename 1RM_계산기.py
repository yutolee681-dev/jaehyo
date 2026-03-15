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
# 변경 후
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ekqS81gko96DVkrFsBkg2-bQiF3oAcHkXd02oHJQ1R4"

SHEET_ID = "1ekqS81gko96DVkrFsBkg2-bQiF3oAcHkXd02oHJQ1R4"

def get_full_data():
    try:
        raw_df = conn.read(
            worksheet="Sheet1",
            ttl=0
        )

        if raw_df is None or raw_df.empty:
            return pd.DataFrame(columns=['name','exercise','weight','date','password','gender','memo'])

        required_cols = {'password': '0000', 'gender': '남성', 'memo': ''}

        for col, default in required_cols.items():
            if col not in raw_df.columns:
                raw_df[col] = default

        return raw_df

    except Exception as e:
        st.error(f"GSheets read error: {e}")
        return pd.DataFrame(columns=['name','exercise','weight','date','password','gender','memo'])

def get_comments():
    try:
        c_df = conn.read(
            worksheet="comments",
            ttl=0
        )

        if c_df is None:
            return pd.DataFrame(columns=['name','comment','date'])

        return c_df

    except Exception as e:
        st.error(f"GSheets comment error: {e}")
        return pd.DataFrame(columns=['name','comment','date'])


df = get_full_data()
comments_df = get_comments()

if 'is_auth' not in st.session_state:
    st.session_state.is_auth = False
    st.session_state.user_name = ""
    st.session_state.user_gender = "남성"

st.markdown("<div id='link_to_top'></div>", unsafe_allow_html=True)
st.title("🏋️ 1RM을 기억해")

# --- 3. 최상단 환영 메시지 및 로그아웃 ---
if st.session_state.is_auth:
    # 3개 컬럼으로 나누어 환영인사 / 새로고침 / 로그아웃 배치
    col_welcome, col_refresh, col_logout = st.columns([2, 1, 1])
    
    with col_welcome:
        st.markdown(f"👋 **{st.session_state.user_name}**님")
    
    with col_refresh:
        # 모바일에서 누르기 편하게 '새로고침' 버튼 추가
        if st.button("🔄 갱신", use_container_width=True):
            st.cache_data.clear() # 캐시된 시트 데이터 삭제
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

# --- 5. 실시간 응원 한마디 ---
st.subheader("💬 실시간 응원 한마디")

# 1. 댓글 입력창 (로그인 시에만 노출)
if st.session_state.is_auth:
    with st.form(key="comment_form_v5", clear_on_submit=True):
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
else:
    st.info("로그인하면 응원 댓글을 남길 수 있습니다.")

# 2. 최근 응원 메시지 박스 (이 부분만 남김)
if not comments_df.empty:
    with st.expander("📂 최근 응원 메시지", expanded=True):
        display_comments = comments_df.sort_index(ascending=False).head(10)
        for idx, row in display_comments.iterrows():
            c_main, c_del = st.columns([10, 1])
            with c_main:
                # 다크모드 대응을 위해 배경은 반투명 회색, 글자색은 자동(inherit)
                st.markdown(f"""
                    <div style="margin-bottom: 5px; padding: 8px; border-bottom: 1px solid rgba(128,128,128,0.2);">
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <span style="font-weight: bold; font-size: 0.85rem; color: #29b5e8;">{row['name']}</span>
                            <span style="color: #888; font-size: 0.7rem;">{row['date']}</span>
                        </div>
                        <div style="font-size: 0.9rem; margin-top: 3px; color: inherit;">{row['comment']}</div>
                    </div>
                """, unsafe_allow_html=True)
            with c_del:
                if st.session_state.is_auth and st.session_state.user_name == row['name']:
                    if st.button("x", key=f"dc_{idx}"):
                        conn.update(spreadsheet=SHEET_URL, worksheet="comments", data=comments_df.drop(idx))
                        st.rerun()

st.divider()

# --- 6. 사용자 인증 ---
if not st.session_state.is_auth:
    with st.container():
        st.subheader("👤 사용자 인증")
        input_mode = st.radio("로그인 방식", ["기존 사용자", "신규 등록"], horizontal=True)
        
        if input_mode == "기존 사용자":
            user_list = sorted(df['name'].dropna().unique().tolist()) if not df.empty else []
            
            # 검색 기능을 끄고 클릭만 유도하는 Selectbox
            selected_name = st.selectbox(
                "본인 이름을 선택하세요", 
                options=user_list,
                index=None,
                placeholder="이름을 선택해주세요",
                key="auth_name_final_select"
            )
            
            # 이름이 선택된 경우에만 비밀번호 창 등장
            if selected_name:
                st.write(f"✅ **{selected_name}** 님이 선택되었습니다.")
                pw_input = st.text_input("비밀번호", type="password", key="login_pw_input")
                
                if st.button("로그인", use_container_width=True):
                    user_rows = df[df['name'] == selected_name]
                    # 따옴표 제거 후 비교
                    stored_pw = str(user_rows.iloc[-1]['password']).strip().replace("'", "")
                    
                    if pw_input.strip() == stored_pw:
                        st.session_state.is_auth = True
                        st.session_state.user_name = selected_name
                        st.session_state.user_gender = user_rows.iloc[-1]['gender']
                        st.success(f"환영합니다, {selected_name}님!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("비밀번호가 틀렸습니다.")
                        
        else:
            # 신규 등록 로직
            reg_col1, reg_col2 = st.columns(2)
            new_name = reg_col1.text_input("새 이름", placeholder="예: 이재효")
            new_gender = reg_col2.radio("성별", ["남성", "여성"], horizontal=True)
            new_pw = st.text_input("비밀번호 설정", type="password")
            
            if st.button("등록 및 로그인", use_container_width=True):
                if new_name and new_pw:
                    st.session_state.is_auth = True
                    st.session_state.user_name = new_name
                    st.session_state.user_gender = new_gender
                    st.session_state.temp_pw = f"'{new_pw}" 
                    st.rerun()

# --- 7. 개인 데이터 분석 통합 (탭 방식) ---
if st.session_state.is_auth:
    # 필터와 수정을 위해 최신 데이터 복사
    my_data = df[df['name'] == st.session_state.user_name].copy()
    my_data['weight'] = pd.to_numeric(my_data['weight'], errors='coerce')
    
    if not my_data.empty:
        st.subheader("📊 나의 퍼포먼스 리포트")
        tab1, tab2, tab3 = st.tabs(["🏆 최고 기록", "📈 성장률 분석", "📋 전체 히스토리"])

        with tab1:
            # 최고 기록 차트 (기존 유지)
            chart_df = my_data.sort_values('weight', ascending=False).drop_duplicates('exercise').copy()
            chart_df['exercise_short'] = chart_df['exercise'].map(rename_map).fillna(chart_df['exercise'])
            base = alt.Chart(chart_df).encode(
                y=alt.Y('exercise_short:N', sort='-x', title=None),
                x=alt.X('weight:Q', title="중량 (lbs)")
            )
            bars = base.mark_bar(color="#29b5e8", cornerRadiusEnd=5)
            text = base.mark_text(align='right', dx=-5, color='white', fontWeight='bold').encode(text=alt.Text('weight:Q', format='.0f'))
            st.altair_chart(bars + text, use_container_width=True)

        with tab2:
            # 성장률 분석 (기존 유지)
            unique_ex = sorted(my_data['exercise'].unique())
            cols = st.columns(2)
            for i, ex in enumerate(unique_ex):
                ex_data = my_data[my_data['exercise'] == ex].sort_values('date')
                if not ex_data.empty:
                    first_w = ex_data.iloc[0]['weight']
                    last_w = ex_data.iloc[-1]['weight']
                    diff = last_w - first_w
                    with cols[i % 2]:
                        st.metric(label=f"{ex}", value=f"{last_w} lbs", delta=f"{diff} lbs")

        with tab3:
            # --- 목록형 히스토리 (클릭 시 세부 수정) ---
            st.write("📝 기록을 클릭하면 수정/삭제할 수 있습니다.")
            
            # 1. 종목 필터 확실하게 적용
            all_my_ex = sorted(my_data['exercise'].unique().tolist())
            filter_ex = st.selectbox("종목 선택", ["전체 보기"] + all_my_ex, key="final_filter")
            
            # 2. 데이터 필터링 및 최신순 정렬
            display_df = my_data.copy()
            if filter_ex != "전체 보기":
                display_df = display_df[display_df['exercise'] == filter_ex]
            
            display_df = display_df.sort_values(by='date', ascending=False)

            # 3. 리스트 렌더링
            if not display_df.empty:
                for idx, row in display_df.iterrows():
                    # 목록 한 줄 디자인 (클릭하면 열림)
                    with st.expander(f"📅 {row['date']} | {row['exercise']} | {row['weight']} lbs"):
                        st.markdown("#### ✏️ 기록 수정")
                        
                        # 수정 입력창
                        e_col1, e_col2 = st.columns(2)
                        with e_col1:
                            new_w = st.number_input("중량(lbs)", value=float(row['weight']), step=5.0, key=f"nw_{idx}")
                        with e_col2:
                            new_m = st.text_input("메모", value=str(row['memo']), key=f"nm_{idx}")
                        
                        # 수정/삭제 버튼
                        b_col1, b_col2 = st.columns(2)
                        with b_col1:
                            if st.button("💾 수정 저장", key=f"sv_{idx}", use_container_width=True):
                                # 원본 df의 인덱스를 찾아 업데이트
                                df.at[idx, 'weight'] = new_w
                                df.at[idx, 'memo'] = new_m
                                conn.update(spreadsheet=SHEET_URL, worksheet="sheet1", data=df)
                                st.success("수정 완료!")
                                time.sleep(0.5)
                                st.rerun()
                        
                        with b_col2:
                            if st.button("🗑️ 기록 삭제", key=f"dc_{idx}", use_container_width=True):
                                # 해당 행 삭제
                                final_df = df.drop(idx)
                                conn.update(spreadsheet=SHEET_URL, worksheet="sheet1", data=final_df)
                                st.warning("기록 삭제됨")
                                time.sleep(0.5)
                                st.rerun()
            else:
                st.info("해당 종목의 기록이 없습니다.")
    st.divider()

# --- 8. 오늘의 기록 업데이트 ---
st.subheader("💪 오늘의 기록 업데이트")

if st.session_state.is_auth:
    # 랭킹에서 선택한 종목을 기본값으로 가져오기
    try:
        ex_index = exercise_list.index(selected_rank_exercise)
    except:
        ex_index = 0

    # 1. 종목 선택
    save_exercise = st.selectbox("종목 선택", exercise_list, index=ex_index, key="update_ex_select")
    
    # 해당 종목의 내 기존 데이터 찾기
    ex_record = my_data[my_data['exercise'] == save_exercise]
    prev_max = float(ex_record['weight'].max()) if not ex_record.empty else 0.0
    
    # 2. 훈련 무게 계산기 (안 깨지는 최종 로직)
    if prev_max > 0:
        st.markdown(f"💡 {save_exercise} 기존 최고: **{prev_max} lbs**")
        with st.expander("📊 훈련 무게 계산 (50% ~ 100%)", expanded=False):
            percents = list(range(50, 101, 5))
            
            # HTML을 리스트에 담아 한 줄로 합쳐서 출력 (코드 노출 방지)
            html_list = []
            html_list.append("<div style='background-color:#f9f9f9;padding:15px;border-radius:10px;border:1px solid #eee;'>")
            for p in percents:
                calc_w = round((prev_max * p / 100) / 2.5) * 2.5
                row = f"<div style='display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #ddd;'><span style='font-weight:bold;font-size:1.1rem;color:#555;'>{p}%</span><span style='font-weight:bold;font-size:1.1rem;color:#29b5e8;'>{calc_w} <small>lbs</small></span></div>"
                html_list.append(row)
            html_list.append("</div>")
            
            st.markdown("".join(html_list), unsafe_allow_html=True)
    else:
        st.caption("아직 기록이 없네요. 오늘 첫 기록을 남겨보세요!")

    st.divider()

    # 3. 입력 폼 (모바일 대응 세로 배치)
    with st.form(key="record_update_form_v3", clear_on_submit=False):
        st.markdown("#### 🏋️ 새로운 기록 입력")
        new_weight = st.number_input("성공한 중량 (lbs)", value=prev_max if prev_max > 0 else 0.0, step=5.0)
        new_memo = st.text_input("오늘의 메모 (컨디션 등)", placeholder="예: 가벼웠는데? 다음번엔 5lbs 높여서 도전..")
        submit_record = st.form_submit_button("🔥 새로운 기록 저장하기", use_container_width=True)

    # 4. 데이터 저장 로직
    if submit_record:
        if new_weight > 0:
            kst_now = datetime.now() + timedelta(hours=9)
            user_data = df[df['name'] == st.session_state.user_name]
            last_row = user_data.iloc[-1] if not user_data.empty else None
            final_pw = str(last_row['password']) if last_row is not None else st.session_state.get('temp_pw', '0000')
            if not str(final_pw).startswith("'"): final_pw = f"'{final_pw}"
            
            new_record = pd.DataFrame([{
                "name": st.session_state.user_name, "exercise": save_exercise, 
                "weight": new_weight, "date": kst_now.strftime("%Y-%m-%d"), 
                "password": final_pw, "gender": st.session_state.user_gender, "memo": new_memo 
            }])
            
            updated_df = pd.concat([df, new_record], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated_df)
            st.balloons()
            st.success(f"성공! {save_exercise} {new_weight} lbs 저장 완료!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("중량을 입력해주세요!")
else:
    st.warning("로그인 후 이용 가능합니다.")

    st.markdown("<br><a href='#link_to_top' style='text-decoration:none;'><button style='width:100%; border-radius:10px; border:1px solid #ddd; background-color:#f9f9f9; padding:10px; cursor:pointer;'>🔝 맨 위로 가기</button></a>", unsafe_allow_html=True)

# --- 9. 관리자 모드 ---
with st.expander("🛠️ Admin"):
    admin_pw = st.text_input("Key", type="password")
    if admin_pw == "5207":
        st.dataframe(df)































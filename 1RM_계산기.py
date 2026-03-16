import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import time
import urllib.parse
# [추가] 직접 저장을 위한 라이브러리
import gspread
from google.oauth2.service_account import Credentials

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

# --- 2. 데이터 로드 및 저장 함수 (KeyError 및 저장 에러 방지) ---
SHEET_ID = "1ekqS81gko96DVkrFsBkg2-bQiF3oAcHkXd02oHJQ1R4"

def get_data_via_csv(worksheet_name="Sheet1"):
    try:
        cb = int(time.time())
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={worksheet_name}&cb={cb}"
        data = pd.read_csv(url).fillna("")
        
        # 1. 컬럼명을 무조건 소문자/공백제거로 표준화
        data.columns = [str(c).lower().strip() for c in data.columns]
        
        # 2. 필수 컬럼이 없거나 데이터가 비어있으면 빈 틀을 반환 (KeyError 방지)
        required_cols = ['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo']
        if 'name' not in data.columns or data.empty:
            return pd.DataFrame(columns=required_cols)

        # 3. 비밀번호 포맷 정리 (따옴표 제거 및 소수점 제거)
        if 'password' in data.columns:
            def clean_pw(val):
                s = str(val).replace("'", "").strip()
                if s.endswith('.0'): s = s[:-2]
                return s
            data['password'] = data['password'].apply(clean_pw)
            
        return data
    except Exception as e:
        # 로드 실패 시에도 앱이 안 죽게 빈 틀 반환
        return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo'])

def save_to_gsheet(dataframe, worksheet_name="Sheet1"):
    try:
        # Secrets에서 [gsheets] 정보를 바로 가져옵니다.
        creds_info = st.secrets["gsheets"]

        credentials_dict = {
            "type": creds_info["type"],
            "project_id": creds_info["project_id"],
            "private_key_id": creds_info["private_key_id"],
            "private_key": creds_info["private_key"].replace("\\n", "\n"),
            "client_email": creds_info["client_email"],
            "client_id": creds_info["client_id"],
            "auth_uri": creds_info["auth_uri"],
            "token_uri": creds_info["token_uri"],
            "auth_provider_x509_cert_url": creds_info["auth_provider_x509_cert_url"],
            "client_x509_cert_url": creds_info["client_x509_cert_url"],
        }

        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        
        sh = client.open_by_key(SHEET_ID)
        
        # 워크시트 없으면 에러 안나게 체크
        try:
            worksheet = sh.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")
        
        dataframe = dataframe.fillna("")
        # 헤더를 포함하여 전체 데이터를 리스트로 변환
        data_to_save = [dataframe.columns.values.tolist()] + dataframe.astype(str).values.tolist()
        
        worksheet.clear()
        # 전체 범위(A1부터)에 업데이트
        worksheet.update(values=data_to_save, range_name='A1')
        return True
    except Exception as e:
        st.error(f"저장 실패! 다시 확인해 주세요: {e}")
        return False

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

# --- 3. 최상단 환영 메시지 ---
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
st.subheader("🏆 박스 실시간 랭킹")
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
                # 남성 데이터 처리
                if i < len(m_data):
                    m_row = m_data.iloc[i]
                    # [수정] 본인인 경우 배경색과 굵게 처리
                    is_me_m = st.session_state.is_auth and m_row['name'] == st.session_state.user_name
                    style_m = 'background-color: rgba(41, 181, 232, 0.3); font-weight: bold;' if is_me_m else ''
                    m_col = f"<td style='{style_m} padding: 5px;'>{get_ordinal(i+1)} {m_row['name']} <b>{m_row['weight']}</b></td>"
                else:
                    m_col = "<td>-</td>"

                # 여성 데이터 처리
                if i < len(f_data):
                    f_row = f_data.iloc[i]
                    # [수정] 본인인 경우 배경색과 굵게 처리
                    is_me_f = st.session_state.is_auth and f_row['name'] == st.session_state.user_name
                    style_f = 'background-color: rgba(255, 75, 75, 0.2); font-weight: bold;' if is_me_f else ''
                    f_col = f"<td style='{style_f} padding: 5px;'>{get_ordinal(i+1)} {f_row['name']} <b>{f_row['weight']}</b></td>"
                else:
                    f_col = "<td>-</td>"
                
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
            if save_to_gsheet(all_comments, "comments"):
                st.rerun()

if not comments_df.empty:
    with st.expander("📂 최근 응원 메시지", expanded=True):
        display_comments = comments_df.sort_index(ascending=False).head(10)
        
        for idx, row in display_comments.iterrows():
            # [수정] 비율을 8:1로 조절하여 텍스트 공간을 넓히고 삭제 버튼 공간을 줄임
            c_col, d_col = st.columns([8, 1])
            
            with c_col:
                # [수정] div 여백(margin)을 최소화하여 한 칸당 높이를 줄임
                st.markdown(f"""
                    <div style="line-height: 1.2;">
                        <span style="font-weight: bold; color: #29b5e8; font-size: 0.85rem;">{row['name']}</span> 
                        <span style="color: gray; font-size: 0.7rem; margin-left: 3px;">{row['date']}</span>
                    </div>
                    <div style="font-size: 0.95rem; margin-top: 2px; color: #eee;">
                        {row['comment']}
                    </div>
                """, unsafe_allow_html=True)
            
            if st.session_state.is_auth and row['name'] == st.session_state.user_name:
                with d_col:
                    # [팁] 버튼 간격을 줄이기 위해 작은 스타일 적용
                    if st.button("🗑️", key=f"del_msg_{idx}"):
                        new_comments_df = comments_df.drop(idx)
                        if save_to_gsheet(new_comments_df, "comments"):
                            st.warning("삭제됨")
                            time.sleep(0.5)
                            st.rerun()
            
            # [수정] 구분선 간격도 최소화
            st.markdown("<hr style='margin: 8px 0; border: 0.1px solid #333;'>", unsafe_allow_html=True)
            
# --- 6. 사용자 인증 ---
if not st.session_state.is_auth:
    st.subheader("👤 사용자 인증")
    input_mode = st.radio("로그인 방식", ["기존 사용자", "신규 등록"], horizontal=True)
    
    if input_mode == "기존 사용자":
        user_list = sorted(df['name'].dropna().astype(str).str.strip().unique().tolist()) if not df.empty else []
        selected_name = st.selectbox("이름 선택", ["선택하세요"] + user_list)
        
        if selected_name != "선택하세요":
            pw_input = st.text_input("비밀번호", type="password")
            if st.button("로그인", use_container_width=True):
                # 1. 재효님 전용 관리자 로그인
                if selected_name == "재효" and pw_input.strip() == "5207":
                    st.session_state.update({
                        "is_auth": True, 
                        "user_name": "재효", 
                        "user_gender": "남성",
                        "password": "5207"
                    })
                    st.rerun()
                
                # 2. 일반 사용자 로그인 체크 (시트의 마지막 기록 비번 기준)
                user_rows = df[df['name'].astype(str).str.strip() == selected_name]
                if not user_rows.empty:
                    clean_sheet_pw = str(user_rows.iloc[-1]['password']).strip()
                    if pw_input.strip() == clean_sheet_pw:
                        st.session_state.update({
                            "is_auth": True, 
                            "user_name": selected_name, 
                            "user_gender": user_rows.iloc[-1]['gender'],
                            "password": pw_input.strip()
                        })
                        st.rerun()
                    else:
                        st.error("비밀번호가 일치하지 않습니다.")
    else:
        # 3. 신규 사용자 등록 (DB 저장 로직 포함)
        reg_col1, reg_col2 = st.columns(2)
        new_name = reg_col1.text_input("새 이름", placeholder="성함 입력")
        new_gender = reg_col2.radio("성별", ["남성", "여성"], horizontal=True)
        new_pw = st.text_input("비밀번호 설정", type="password", placeholder="숫자 4자리 등")
        
        if st.button("등록 및 로그인", use_container_width=True):
            if new_name and new_pw:
                # 시트에 중복 이름이 있는지 확인
                if not df.empty and new_name.strip() in df['name'].values:
                    st.warning("이미 존재하는 이름입니다. 기존 사용자로 로그인해주세요.")
                else:
                    # 가입 정보를 시트에 기록 (최초 데이터 생성)
                    new_user_data = pd.DataFrame([{
                        "name": new_name.strip(),
                        "exercise": "Registration",  # 가입용 더미 데이터
                        "weight": 0,
                        "date": (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d"),
                        "password": f"'{new_pw.strip()}", # 시트 숫지 변환 방지
                        "gender": new_gender,
                        "memo": "신규 가입 환영합니다! 🔥"
                    }])
                    
                    # 기존 데이터에 합치기
                    updated_df = pd.concat([df, new_user_data], ignore_index=True)
                    
                    # 구글 시트에 즉시 전송
                    if save_to_gsheet(updated_df, "Sheet1"):
                        st.session_state.update({
                            "is_auth": True, 
                            "user_name": new_name.strip(), 
                            "user_gender": new_gender,
                            "password": new_pw.strip()
                        })
                        st.success(f"🎉 {new_name}님, 가입을 축하합니다! 이제 기록을 시작하세요.")
                        time.sleep(1)
                        st.rerun()
            else:
                st.error("이름과 비밀번호를 모두 입력해주셔야 등록이 가능합니다.")

# --- 7. 개인 데이터 분석 통합 ---
if st.session_state.is_auth:
    my_data = df[df['name'] == st.session_state.user_name].copy()
    my_data['weight'] = pd.to_numeric(my_data['weight'], errors='coerce')
    
    if not my_data.empty:
        st.subheader("📊 나의 퍼포먼스 리포트")
        tab1, tab2, tab3 = st.tabs(["🏆 최고 기록", "📈 성장률 분석", "📋 전체 히스토리"])

        with tab1:
            # 1. 차트용 데이터 준비 (중량 형변환 및 종목명 단축)
            chart_df = my_data.sort_values('weight', ascending=False).drop_duplicates('exercise').copy()
            chart_df['weight'] = pd.to_numeric(chart_df['weight'], errors='coerce')
            chart_df['exercise_short'] = chart_df['exercise'].map(rename_map).fillna(chart_df['exercise'])
            
            # 2. 최고 기록 막대 차트 설정
            base = alt.Chart(chart_df).encode(
                y=alt.Y('exercise_short:N', sort='-x', title=None),
                x=alt.X('weight:Q', title="중량 (lbs)")
            )

            # 3. 막대(Bar)와 숫자 라벨(Text) 결합
            bars = base.mark_bar(color="#29b5e8")
            text = base.mark_text(
                align='right',
                dx=-5,
                color='white'
            ).encode(
                text=alt.Text('weight:Q', format='.0f')
            )

            st.altair_chart(bars + text, use_container_width=True)

            # 4. 1RM 비율별 중량 표 (모바일 최적화: 50%부터 순차적으로)
            st.divider()
            st.subheader("📊 1RM 비율별 중량 표")
            
            # 내 기록이 있는 종목만 선택지로 제공
            calc_ex = st.selectbox("종목 선택", chart_df['exercise'].unique(), key="calc_ex_select")
            
            if calc_ex:
                # 선택한 종목의 1RM(최고 중량) 가져오기
                max_w = chart_df[chart_df['exercise'] == calc_ex]['weight'].iloc[0]
                
                # 50%부터 100%까지 5% 단위로 리스트 생성
                per_list = range(50, 105, 5) 
                calc_data = []
                for p in per_list:
                    calc_data.append({
                        "비율 (%)": f"{p}%",
                        "중량 (lbs)": f"{round(max_w * (p/100), 1)} lbs"
                    })
                
                # 데이터프레임 변환 및 출력 (모바일은 한 줄로 길게 보는 게 편함)
                calc_table = pd.DataFrame(calc_data).set_index("비율 (%)")
                st.table(calc_table)
                             
        with tab2:
            unique_ex = sorted(my_data['exercise'].unique())
            cols = st.columns(2)
            for i, ex in enumerate(unique_ex):
                ex_data = my_data[my_data['exercise'] == ex].sort_values('date')
                diff = ex_data.iloc[-1]['weight'] - ex_data.iloc[0]['weight']
                cols[i % 2].metric(label=ex, value=f"{ex_data.iloc[-1]['weight']} lbs", delta=f"{diff} lbs")

        with tab3:
            st.write("📝 기록을 클릭하면 수정/삭제할 수 있습니다.")
            all_my_ex = sorted(my_data['exercise'].unique().tolist())
            filter_ex = st.selectbox("종목 선택", ["전체 보기"] + all_my_ex, key="history_filter")
            
            display_df = my_data.copy()
            if filter_ex != "전체 보기":
                display_df = display_df[display_df['exercise'] == filter_ex]
            display_df = display_df.sort_values(by='date', ascending=False)

            if not display_df.empty:
                for idx, row in display_df.iterrows():
                    memo_text = row['memo'] if str(row['memo']).strip() != "" else "내용 없음"
                    with st.expander(f"📅 {row['date']} | {row['exercise']} | {row['weight']} lbs"):
                        st.markdown(f"**💬 기록된 메모:** {memo_text}")
                        st.divider()
                        new_w = st.number_input("중량(lbs)", value=float(row['weight']), step=5.0, key=f"nw_{idx}")
                        new_m = st.text_input("메모 수정", value=str(row['memo']), key=f"nm_{idx}")
                        
                        b_col1, b_col2 = st.columns(2)
                        with b_col1:
                            if st.button("💾 수정 저장", key=f"sv_{idx}", use_container_width=True):
                                df.at[idx, 'weight'] = new_w
                                df.at[idx, 'memo'] = new_m
                                if save_to_gsheet(df, "Sheet1"):
                                    st.success("수정 완료! 🔥")
                                    time.sleep(0.5); st.rerun()
                        with b_col2:
                            if st.button("🗑️ 기록 삭제", key=f"dc_{idx}", use_container_width=True):
                                if save_to_gsheet(df.drop(idx), "Sheet1"):
                                    st.warning("삭제됨")
                                    time.sleep(0.5); st.rerun()

# --- 8. 오늘의 기록 업데이트 ---
if st.session_state.is_auth:
    st.divider()
    st.subheader("💪 오늘의 기록 업데이트")

    # 1. 종목 선택
    save_exercise = st.selectbox(
        "종목 선택", 
        exercise_list, 
        key="update_ex_select"
    )
    
    # 해당 종목의 이전 최고 기록 가져오기
    ex_record = my_data[my_data['exercise'] == save_exercise]
    prev_max = float(ex_record['weight'].max()) if not ex_record.empty else 0.0

    # 2. 입력 폼
    with st.form(key="record_form", clear_on_submit=True):
        new_weight = st.number_input("성공 중량 (lbs)", value=prev_max, step=5.0)
        new_memo = st.text_input("메모", placeholder="컨디션이나 와드 기록 등", key="memo_input_widget")
        submit_btn = st.form_submit_button("🔥 기록 저장")
        
        if submit_btn:
            kst_now = datetime.now() + timedelta(hours=9)
            
            # [보안 및 에러 방지 핵심 로직]
            # 1순위: 세션에 저장된 'password' (로그인 시 입력값)
            # 2순위: 재효님일 경우 '5207' 강제 할당
            # 3순위: 그래도 없으면 로그인 창에 입력된 값을 직접 참조 (최후의 수단)
            user_pw = st.session_state.get("password")
            
            if not user_pw:
                if st.session_state.user_name == "재효":
                    user_pw = "5207"
                else:
                    # 세션에 비번이 없으면 아예 저장을 막아버립니다 (UNKNOWN 방지)
                    st.error("인증 정보가 만료되었습니다. 로그아웃 후 다시 로그인해주세요.")
                    st.stop()
            
            # 새로운 데이터 프레임 생성
            new_record = pd.DataFrame([{
                "name": st.session_state.user_name, 
                "exercise": save_exercise, 
                "weight": new_weight, 
                "date": kst_now.strftime("%Y-%m-%d"), 
                "password": f"'{user_pw}",  # 앞에 '를 붙여야 시트에서 숫자로 안 변함
                "gender": st.session_state.user_gender, 
                "memo": new_memo
            }])
            
            # 전체 데이터와 합치기
            updated_df = pd.concat([df, new_record], ignore_index=True)
            
            # 구글 시트 저장
            if save_to_gsheet(updated_df, "Sheet1"):
                st.success(f"[{save_exercise}] {new_weight}lbs 저장 완료! 🔥")
                time.sleep(1)
                st.rerun()

# --- 9. 관리자 모드 ---
with st.expander("🛠️ Admin"):
    if st.text_input("Key", type="password") == "5207":
        st.dataframe(df)

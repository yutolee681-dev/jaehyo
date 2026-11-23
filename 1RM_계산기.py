import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import time
import gspread
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="centered")

# --- 🎨 커스텀 CSS (세련된 카드 UI & 여백 최적화) ---
st.markdown("""
<style>
    /* 전체 상단 여백 축소 */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 760px;
    }
    /* 카드형 컨테이너 스타일 */
    .wod-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-left: 5px solid #38bdf8;
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .wod-title {
        color: #38bdf8;
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 0.3rem;
    }
    .wod-workout {
        color: #f8fafc;
        font-size: 1.35rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    .wod-desc {
        color: #cbd5e1;
        font-size: 0.95rem;
        white-space: pre-line;
        line-height: 1.5;
    }
    /* 랭킹 테이블 스타일 */
    .rank-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0 6px;
        font-size: 0.9rem;
    }
    .rank-table th {
        color: #94a3b8;
        font-weight: 600;
        padding: 8px 12px;
        text-align: left;
        border-bottom: 1px solid #334155;
    }
    .rank-table td {
        background-color: #1e293b;
        padding: 10px 12px;
        color: #f1f5f9;
    }
    .rank-table td:first-child { border-radius: 8px 0 0 8px; }
    .rank-table td:last-child { border-radius: 0 8px 8px 0; }
    
    /* 탭 디자인 개선 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #0f172a;
        padding: 6px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 14px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- 서수(Ordinal) 및 메달 변환 함수 ---
def get_ordinal(n):
    if n == 1: return "🥇"
    elif n == 2: return "🥈"
    elif n == 3: return "🥉"
    if 11 <= n % 100 <= 13: suffix = 'th'
    else: suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"<span style='color:#94a3b8; font-size:0.8rem;'>{n}{suffix}</span>"

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

# --- 2. 구글 시트 API 연결 및 최적화 함수 ---
SHEET_ID = "1ekqS81gko96DVkrFsBkg2-bQiF3oAcHkXd02oHJQ1R4"

def get_gspread_client():
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
    return gspread.authorize(credentials)

@st.cache_data(ttl=3600)
def load_data_from_api(worksheet_name="Sheet1"):
    col_mapping = {
        "Sheet1": ['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo'],
        "comments": ['name', 'comment', 'date'],
        "today_wod": ['date', 'workout', 'description'],
        "training_logs": ['date', 'name', 'log_content']
    }
    required_cols = col_mapping.get(worksheet_name, [])
    try:
        client = get_gspread_client()
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        if not data: return pd.DataFrame(columns=required_cols)
        df_new = pd.DataFrame(data)
        df_new.columns = [str(c).lower().strip() for c in df_new.columns]
        for col in required_cols:
            if col not in df_new.columns: df_new[col] = ""
        if 'password' in df_new.columns:
            df_new['password'] = df_new['password'].astype(str).str.replace("'", "", regex=False).str.strip().str.replace(".0", "", regex=False)
        return df_new
    except Exception:
        return pd.DataFrame(columns=required_cols)

def save_to_gsheet(dataframe, worksheet_name="Sheet1"):
    try:
        client = get_gspread_client()
        sh = client.open_by_key(SHEET_ID)
        try: worksheet = sh.worksheet(worksheet_name)
        except gspread.WorksheetNotFound: worksheet = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")
        dataframe = dataframe.fillna("")
        data_to_save = [dataframe.columns.values.tolist()] + dataframe.astype(str).values.tolist()
        worksheet.clear()
        worksheet.update(values=data_to_save, range_name='A1', value_input_option='RAW')
        st.cache_data.clear()
        return True
    except Exception: return False

def append_to_gsheet(list_data, worksheet_name="comments"):
    try:
        client = get_gspread_client()
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet(worksheet_name)
        worksheet.append_row(list_data, value_input_option='RAW')
        st.cache_data.clear()
        return True
    except Exception: return False

# --- 데이터 로딩 ---
raw_df = load_data_from_api("Sheet1")
comments_df = load_data_from_api("comments")
wod_df = load_data_from_api("today_wod")
logs_df = load_data_from_api("training_logs")
today_str = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d")
df = raw_df[~raw_df['exercise'].astype(str).str.lower().isin(['registration', 'join'])].copy()

# 세션 초기화
if 'is_auth' not in st.session_state:
    st.session_state.update({"is_auth": False, "user_name": "", "user_gender": "남성"})

# ==========================================
# 상단 헤더 & 사용자 상태 바
# ==========================================
head_col1, head_col2 = st.columns([3, 2])
with head_col1:
    st.markdown("## 🏋️ CrossFit 1RM")
with head_col2:
    if st.session_state.is_auth:
        b1, b2 = st.columns(2)
        if b1.button("🔄 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.toast("최신 데이터를 불러왔습니다!", icon="✨")
            time.sleep(0.4)
            st.rerun()
        if b2.button("🚪 로그아웃", use_container_width=True):
            st.session_state.is_auth = False
            st.rerun()

# 로그인 상태 표시 및 계정 설정 (접이식으로 깔끔하게)
if st.session_state.is_auth:
    with st.expander(f"👋 **{st.session_state.user_name}**님 로그인 중 · 계정 / 관리자 설정"):
        acc_tab1, acc_tab2 = st.tabs(["🔐 비밀번호 변경", "🛠️ 관리자 메뉴"])
        
        with acc_tab1:
            with st.form("pw_change_top", clear_on_submit=True):
                c_p1, c_p2, c_p3 = st.columns([2, 2, 1])
                new_pw = c_p1.text_input("새 비밀번호", type="password", placeholder="숫자 4자리", label_visibility="collapsed")
                confirm_pw = c_p2.text_input("비밀번호 확인", type="password", placeholder="비밀번호 확인", label_visibility="collapsed")
                if c_p3.form_submit_button("변경", use_container_width=True):
                    if new_pw != confirm_pw: st.error("비밀번호 불일치")
                    elif len(new_pw) < 2: st.warning("비밀번호 입력 필요")
                    else:
                        fixed_pw = str(new_pw).strip().zfill(4)
                        raw_df.loc[raw_df['name'] == st.session_state.user_name, 'password'] = fixed_pw
                        if save_to_gsheet(raw_df):
                            st.success("비밀번호가 변경되었습니다!")
                            st.session_state.password = fixed_pw
                            time.sleep(0.8)
                            st.rerun()
        
        with acc_tab2:
            current_user = st.session_state.get("user_name", "")
            admin_pw = st.text_input("Admin Key (권한자 자동인증)", type="password", placeholder="인증키 입력")
            is_super_admin = (current_user == "재효") or (admin_pw == "5207")
            is_training_admin = (current_user == "윤아")

            if is_super_admin or is_training_admin:
                existing_today_wod = wod_df[wod_df['date'] == today_str]
                if 'wod_title' not in st.session_state:
                    st.session_state.wod_title = existing_today_wod.iloc[0]['workout'] if not existing_today_wod.empty else ""
                if 'wod_desc' not in st.session_state:
                    st.session_state.wod_desc = existing_today_wod.iloc[0]['description'] if not existing_today_wod.empty else ""

                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("🆕 새 공지 비우기", use_container_width=True):
                    st.session_state.wod_title, st.session_state.wod_desc = "", ""
                    st.rerun()
                if col_btn2.button("📥 오늘 공지 불러오기", use_container_width=True):
                    if not existing_today_wod.empty:
                        st.session_state.wod_title = existing_today_wod.iloc[0]['workout']
                        st.session_state.wod_desc = existing_today_wod.iloc[0]['description']
                    st.rerun()

                with st.form("wod_form"):
                    input_title = st.text_input("WOD 제목", value=st.session_state.wod_title)
                    input_desc = st.text_area("WOD 내용", value=st.session_state.wod_desc, height=130)
                    if st.form_submit_button("✅ 공지 게시하기", use_container_width=True):
                        new_entry = pd.DataFrame([{"date": today_str, "workout": input_title, "description": input_desc}])
                        updated_wod = pd.concat([wod_df[wod_df['date'] != today_str], new_entry], ignore_index=True)
                        if save_to_gsheet(updated_wod, "today_wod"):
                            st.session_state.wod_title, st.session_state.wod_desc = input_title, input_desc
                            st.toast("공지가 게시되었습니다!", icon="🎊")
                            time.sleep(0.8)
                            st.rerun()

                if is_super_admin:
                    st.divider()
                    st.caption("⚙️ 시스템 관리 (슈퍼관리자 전용)")
                    target = st.selectbox("비밀번호 초기화 대상", sorted(raw_df['name'].unique()))
                    if st.button("선택 유저 '1234'로 초기화"):
                        raw_df.loc[raw_df['name'] == target, 'password'] = "'1234"
                        if save_to_gsheet(raw_df):
                            st.toast(f"{target}님 초기화 완료!", icon="🔑")
                            time.sleep(0.8)
                            st.rerun()
                    with st.expander("전체 Raw 데이터 보기"):
                        st.dataframe(raw_df, use_container_width=True)
            else:
                st.caption("공지 작성 및 시스템 관리 권한이 없습니다.")

else:
    # 비로그인 시 깔끔한 로그인 카드 노출
    with st.container(border=True):
        mode = st.radio("멤버십 인증", ["기존 회원 로그인", "신규 회원 등록"], horizontal=True, label_visibility="collapsed")
        if mode == "기존 회원 로그인":
            u_list = sorted(raw_df['name'].unique().tolist()) if not raw_df.empty else []
            c1, c2, c3 = st.columns([2, 2, 1])
            name = c1.selectbox("이름", ["이름 선택"] + u_list, label_visibility="collapsed")
            pw = c2.text_input("비밀번호", type="password", placeholder="비밀번호", label_visibility="collapsed")
            if c3.button("로그인", use_container_width=True, type="primary"):
                if name != "이름 선택":
                    u_row = raw_df[raw_df['name'] == name].iloc[-1]
                    input_pw_fixed = str(pw).strip().zfill(4)
                    sheet_pw_fixed = str(u_row['password']).strip().zfill(4)
                    if input_pw_fixed == sheet_pw_fixed or pw == "5207":
                        st.session_state.update({
                            "is_auth": True, "user_name": name, 
                            "user_gender": u_row['gender'], "password": input_pw_fixed
                        })
                        st.rerun()
                    else:
                        st.error("비밀번호가 일치하지 않습니다.")
                else:
                    st.warning("이름을 선택해주세요.")
        else:
            c1, c2, c3, c4 = st.columns([2, 2, 2, 1.5])
            n_n = c1.text_input("새 이름", placeholder="이름", label_visibility="collapsed")
            n_g = c2.selectbox("성별", ["남성", "여성"], label_visibility="collapsed")
            n_p = c3.text_input("비번", type="password", placeholder="숫자 4자리", label_visibility="collapsed")
            if c4.button("가입", use_container_width=True, type="primary") and n_n and n_p:
                new_u = pd.DataFrame([{"name": n_n, "exercise": "Registration", "weight": 0, "date": today_str, "password": f"'{n_p}", "gender": n_g, "memo": "반가워요!"}])
                if save_to_gsheet(pd.concat([raw_df, new_u], ignore_index=True)):
                    st.session_state.update({"is_auth": True, "user_name": n_n, "user_gender": n_g, "password": n_p})
                    st.rerun()

# ==========================================
# 메인 네비게이션 탭 (4단 구성)
# ==========================================
main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs([
    "🏠 홈 & 공지", 
    "🏆 박스 랭킹", 
    "📊 내 기록 · 분석", 
    "📝 훈련 일지"
])

# ------------------------------------------
# TAB 1: 홈 & 공지 & 실시간 잡도리
# ------------------------------------------
with main_tab1:
    # 1. 오늘의 WOD 카드
    if not wod_df.empty and not wod_df[wod_df['date'] == today_str].empty:
        w_info = wod_df[wod_df['date'] == today_str].iloc[0]
        st.markdown(f"""
        <div class="wod-card">
            <div class="wod-title">📅 TODAY'S WOD · {today_str}</div>
            <div class="wod-workout">📢 {w_info['workout']}</div>
            <div class="wod-desc">{w_info['description']}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("📢 오늘 예정된 공통 WOD가 없습니다. 개인 스트렝스 훈련을 진행하세요!")

    # 지난 훈련 공지 (깔끔한 셀렉트)
    with st.expander("📅 지난 훈련 공지 다시보기"):
        if not wod_df.empty:
            past_wods = wod_df[wod_df['date'] < today_str].sort_values('date', ascending=False)
            if not past_wods.empty:
                selected_date = st.selectbox("날짜 선택", past_wods['date'].unique(), label_visibility="collapsed")
                wod_detail = past_wods[past_wods['date'] == selected_date].iloc[0]
                st.markdown(f"**📢 {wod_detail['workout']}**")
                st.caption(wod_detail['description'])
            else:
                st.caption("과거 공지 기록이 없습니다.")

    st.markdown("### 💬 실시간 잡도리 & 응원")
    if st.session_state.is_auth:
        with st.form(key="comment_form", clear_on_submit=True):
            c1, c2 = st.columns([4, 1])
            new_c = c1.text_input("메시지", placeholder=f"{st.session_state.user_name}님, 한마디 남겨보세요! 🔥", label_visibility="collapsed")
            if c2.form_submit_button("등록", use_container_width=True, type="primary") and new_c:
                kst = (datetime.now() + timedelta(hours=9)).strftime("%m/%d %H:%M")
                if append_to_gsheet([st.session_state.user_name, new_c, kst], "comments"):
                    st.rerun()
    else:
        st.caption("💡 로그인하시면 응원 메시지를 남길 수 있습니다.")

    if not comments_df.empty:
        with st.container(border=True):
            for idx, row in comments_df.sort_index(ascending=False).head(10).iterrows():
                c_col, d_col = st.columns([9, 1])
                c_col.markdown(f"**{row['name']}** <span style='color:#64748b; font-size:0.8rem;'>· {row['date']}</span><br><span style='font-size:0.95rem;'>{row['comment']}</span>", unsafe_allow_html=True)
                if st.session_state.is_auth and row['name'] == st.session_state.user_name:
                    if d_col.button("✕", key=f"del_{idx}", help="삭제"):
                        if save_to_gsheet(comments_df.drop(idx), "comments"):
                            st.rerun()
                st.markdown("<hr style='margin:6px 0; border-color:#1e293b;'>", unsafe_allow_html=True)

# ------------------------------------------
# TAB 2: 박스 실시간 랭킹
# ------------------------------------------
with main_tab2:
    selected_rank_ex = st.selectbox("종목 선택", exercise_list)
    if not df.empty:
        rank_df = df[df['exercise'] == selected_rank_ex].copy()
        rank_df['weight'] = pd.to_numeric(rank_df['weight'], errors='coerce').fillna(0)
        best_rank = rank_df.sort_values('weight', ascending=False).drop_duplicates('name')
        
        if not best_rank.empty:
            m_data = best_rank[best_rank['gender'] == "남성"].reset_index(drop=True)
            f_data = best_rank[best_rank['gender'] == "여성"].reset_index(drop=True)
            max_r = max(len(m_data), len(f_data))
            
            html = """<table class='rank-table'>
                <thead><tr><th style='width:50%;'>♂️ MALE</th><th style='width:50%;'>♀️ FEMALE</th></tr></thead>
                <tbody>"""
            for i in range(max_r):
                m_cell = f"<td>{get_ordinal(i+1)} &nbsp;<b>{m_data.iloc[i]['name']}</b> <span style='float:right; color:#38bdf8; font-weight:700;'>{int(m_data.iloc[i]['weight'])} lbs</span></td>" if i < len(m_data) else "<td>-</td>"
                f_cell = f"<td>{get_ordinal(i+1)} &nbsp;<b>{f_data.iloc[i]['name']}</b> <span style='float:right; color:#f472b6; font-weight:700;'>{int(f_data.iloc[i]['weight'])} lbs</span></td>" if i < len(f_data) else "<td>-</td>"
                html += f"<tr>{m_cell}{f_cell}</tr>"
            st.markdown(html + "</tbody></table>", unsafe_allow_html=True)
        else:
            st.info(f"아직 {selected_rank_ex} 등록 기록이 없습니다.")

# ------------------------------------------
# TAB 3: 내 기록 & 퍼포먼스 분석
# ------------------------------------------
with main_tab3:
    if not st.session_state.is_auth:
        st.warning("🔒 로그인 후 나의 1RM 기록과 성장 분석을 확인할 수 있습니다.")
    else:
        user_name = st.session_state.user_name
        
        # 1. 빠른 PR 업데이트 카드 (최상단 배치로 접근성 극대화)
        with st.expander("➕ 새 기록 등록 / PR 업데이트", expanded=False):
            up_ex = st.selectbox("종목 선택", exercise_list, key="up_ex_sel_fixed")
            existing_record = raw_df[(raw_df['name'] == user_name) & (raw_df['exercise'] == up_ex)]
            last_weight = float(existing_record.iloc[-1]['weight']) if not existing_record.empty else 0.0
            
            with st.form("update_form_final", clear_on_submit=True):
                col_w, col_m = st.columns([1, 2])
                w = col_w.number_input("무게 (lbs)", step=5.0, value=last_weight)
                m = col_m.text_input("메모", placeholder="컨디션이나 세트 기록 (선택)")
                if st.form_submit_button("💾 기록 저장하기", use_container_width=True, type="primary"):
                    other_records = raw_df[~((raw_df['name'] == user_name) & (raw_df['exercise'] == up_ex))]
                    fixed_pw = str(st.session_state.password).strip().zfill(4)
                    new_entry = pd.DataFrame([{
                        "name": user_name, "exercise": up_ex, "weight": w,
                        "date": today_str, "password": f"'{fixed_pw}",
                        "gender": st.session_state.user_gender, "memo": m
                    }])
                    if save_to_gsheet(pd.concat([other_records, new_entry], ignore_index=True)):
                        st.toast(f"🏆 {up_ex} {w} lbs 저장 완료!", icon="🔥")
                        time.sleep(0.8)
                        st.rerun()

        my_data = df[df['name'] == user_name].copy()
        my_data['weight'] = pd.to_numeric(my_data['weight'], errors='coerce').fillna(0)

        if my_data.empty:
            st.info("아직 등록된 1RM 기록이 없습니다. 위 버튼을 눌러 첫 기록을 등록해 보세요!")
        else:
            sub_t1, sub_t2, sub_t3 = st.tabs(["🏆 PR & 밸런스", "📈 성장 추이", "📋 기록 관리"])
            
            with sub_t1:
                best = my_data.sort_values('weight', ascending=False).drop_duplicates('exercise').copy()
                best['ex_short'] = best['exercise'].map(rename_map).fillna(best['exercise'])
                
                # 레이더 차트
                radar_labels = ["Back Squat", "Deadlift", "Shoulder Press", "Thruster", "Power Clean", "Power Snatch"]
                radar_values = [best[best['exercise'] == ex]['weight'].max() if not best[best['exercise'] == ex].empty else 0 for ex in radar_labels]
                fig = go.Figure(go.Scatterpolar(
                    r=radar_values + [radar_values[0]], theta=radar_labels + [radar_labels[0]],
                    fill='toself', fillcolor='rgba(56, 189, 248, 0.3)', line=dict(color='#38bdf8', width=2.5)
                ))
                fig.update_layout(
                    polar=dict(bgcolor='rgba(0,0,0,0)', radialaxis=dict(visible=True, range=[0, max(radar_values) + 15 if any(radar_values) else 100], gridcolor='#334155', showticklabels=False)),
                    paper_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=50, r=50, t=20, b=20)
                )
                st.plotly_chart(fig, use_container_width=True)

                # 가로 막대 차트
                bars = alt.Chart(best).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6).encode(
                    y=alt.Y('ex_short:N', sort='-x', title=None),
                    x=alt.X('weight:Q', title="Weight (lbs)"),
                    color=alt.Color('weight:Q', scale=alt.Scale(scheme='blues'), legend=None)
                )
                text = alt.Chart(best).mark_text(align='right', baseline='middle', dx=-8, color='white', fontWeight='bold').encode(
                    y=alt.Y('ex_short:N', sort='-x'), x=alt.X('weight:Q'), text=alt.Text('weight:Q', format='.0f')
                )
                st.altair_chart(alt.layer(bars, text).properties(height=340), use_container_width=True)

                # 1RM 퍼센트 계산기 (2단 그리드로 컴팩트하게)
                with st.expander("🧮 훈련 중량(%) 계산기"):
                    calc_ex = st.selectbox("종목 선택", exercise_list, key="calc_ex_selector")
                    ex_best = my_data[my_data['exercise'] == calc_ex]['weight'].max()
                    if ex_best > 0:
                        c_left, c_right = st.columns(2)
                        per_list = list(range(95, 45, -5))
                        for idx_p, p in enumerate(per_list):
                            target_col = c_left if idx_p < 5 else c_right
                            target_col.markdown(f"**{p}%** : `{round(float(ex_best)*(p/100), 1)} lbs`")

            with sub_t2:
                recent_ex_list = my_data.sort_values('date', ascending=False)['exercise'].unique()[:3]
                m_cols = st.columns(len(recent_ex_list))
                for i, ex in enumerate(recent_ex_list):
                    ex_d = my_data[my_data['exercise'] == ex].sort_values('date')
                    first_w, last_w = float(ex_d.iloc[0]['weight']), float(ex_d.iloc[-1]['weight'])
                    diff = last_w - first_w
                    m_cols[i].metric(rename_map.get(ex, ex), f"{int(last_w)} lbs", f"{int(diff)} lbs" if diff != 0 else None)

                st.divider()
                graph_ex = st.selectbox("상세 그래프 종목", sorted(my_data['exercise'].unique()), key="graph_ex_selector_v2")
                g_data = my_data[my_data['exercise'] == graph_ex].sort_values('date').copy()
                chart = alt.Chart(g_data).mark_line(point=True, color='#38bdf8').encode(
                    x=alt.X('date:T', title="날짜"),
                    y=alt.Y('weight:Q', title="중량 (lbs)", scale=alt.Scale(zero=False)),
                    tooltip=['date', 'weight', 'memo']
                ).properties(height=260)
                st.altair_chart(chart, use_container_width=True)

            with sub_t3:
                for idx, row in my_data.sort_values('date', ascending=False).iterrows():
                    with st.container(border=True):
                        r_c1, r_c2, r_c3 = st.columns([3, 1.5, 1])
                        r_c1.markdown(f"**{row['exercise']}**<br><small style='color:#94a3b8;'>{row['date']} · {row['memo']}</small>", unsafe_allow_html=True)
                        new_w = r_c2.number_input("수정", value=float(row['weight']), key=f"edit_w_{idx}", label_visibility="collapsed")
                        with r_c3:
                            if st.button("저장", key=f"save_{idx}", use_container_width=True):
                                raw_df.loc[idx, 'weight'] = new_w
                                if save_to_gsheet(raw_df): st.rerun()
                            if st.button("삭제", key=f"del_rec_{idx}", use_container_width=True):
                                if save_to_gsheet(raw_df.drop(idx)): st.rerun()

# ------------------------------------------
# TAB 4: 나의 훈련 일지
# ------------------------------------------
with main_tab4:
    if not st.session_state.is_auth:
        st.warning("🔒 로그인 후 개인 훈련 일지를 작성하고 관리할 수 있습니다.")
    else:
        user_name = st.session_state.user_name
        my_today_log = logs_df[(logs_df['name'] == user_name) & (logs_df['date'] == today_str)]

        if my_today_log.empty:
            with st.form("personal_log_form"):
                user_log = st.text_area("✍️ 오늘의 훈련 일지", placeholder="오늘 WOD 기록, 컨디션, 피드백을 자유롭게 남겨보세요.")
                if st.form_submit_button("💾 오늘 일지 저장", type="primary", use_container_width=True):
                    if user_log.strip():
                        new_log = pd.DataFrame([{"date": today_str, "name": user_name, "log_content": user_log}])
                        if save_to_gsheet(pd.concat([logs_df, new_log], ignore_index=True), "training_logs"):
                            st.toast("오완완! 일지가 저장되었습니다 🔥", icon="💪")
                            time.sleep(0.8)
                            st.rerun()
        else:
            st.success("✅ 오늘 훈련 일지 작성을 완료했습니다!")

        st.markdown("#### 📅 나의 일지 히스토리")
        my_past_logs = logs_df[logs_df['name'] == user_name].sort_values('date', ascending=False)
        if not my_past_logs.empty:
            for idx, row in my_past_logs.iterrows():
                row_date = str(row['date'])
                with st.expander(f"🗓️ {row_date} 훈련 기록", expanded=(row_date == today_str)):
                    edited_log = st.text_area("내용", value=row['log_content'], key=f"edit_log_{idx}", label_visibility="collapsed")
                    if st.button("💾 수정 내용 저장", key=f"up_log_{idx}"):
                        logs_df.loc[idx, 'log_content'] = edited_log
                        if save_to_gsheet(logs_df, "training_logs"):
                            st.toast("수정 완료!", icon="✨")
                            time.sleep(0.8)
                            st.rerun()
        else:
            st.caption("아직 작성된 일지가 없습니다.")

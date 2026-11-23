import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import time
import gspread
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials

# 1. 페이지 설정
st.set_page_config(page_title="LIKE 1RM Tracker", page_icon="⚡", layout="centered")

# --- 🎨 하이엔드 피트니스 UI 커스텀 CSS ---
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    /* 전체 폰트 및 다크 배경 */
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .stApp {
        background-color: #090D16;
        color: #F8FAFC;
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 4rem;
        max-width: 740px;
    }

    /* 상단 브랜드 헤더 */
    .brand-title {
        font-size: 1.65rem;
        font-weight: 900;
        letter-spacing: -0.03em;
        background: linear-gradient(90deg, #F8FAFC 0%, #38BDF8 60%, #A3E635 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .brand-sub {
        font-size: 0.75rem;
        color: #64748B;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    /* 글래스모피즘 WOD 카드 */
    .wod-card {
        background: radial-gradient(circle at top right, rgba(56, 189, 248, 0.14), rgba(15, 23, 42, 0.85));
        backdrop-filter: blur(12px);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 16px;
        padding: 1.4rem 1.6rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
    }
    .wod-badge {
        display: inline-block;
        background: rgba(163, 230, 53, 0.15);
        color: #A3E635;
        border: 1px solid rgba(163, 230, 53, 0.35);
        font-size: 0.72rem;
        font-weight: 800;
        padding: 3px 10px;
        border-radius: 999px;
        letter-spacing: 0.06em;
        margin-bottom: 0.6rem;
    }
    .wod-workout {
        color: #FFFFFF;
        font-size: 1.4rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 0.6rem;
    }
    .wod-desc {
        color: #CBD5E1;
        font-size: 0.94rem;
        white-space: pre-line;
        line-height: 1.6;
        background: rgba(9, 13, 22, 0.45);
        padding: 0.9rem 1rem;
        border-radius: 10px;
        border-left: 3px solid #38BDF8;
    }

    /* KPI 요약 카드 (내 기록 탭) */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        margin: 0.8rem 0 1.2rem 0;
    }
    .kpi-box {
        background: linear-gradient(180deg, #131B2E 0%, #0F1626 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 0.9rem 1rem;
        text-align: center;
    }
    .kpi-label {
        font-size: 0.75rem;
        color: #94A3B8;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .kpi-val {
        font-size: 1.25rem;
        font-weight: 800;
        color: #F8FAFC;
    }
    .kpi-accent { color: #A3E635; }

    /* 하이엔드 랭킹 보드 */
    .rank-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0 8px;
        font-size: 0.9rem;
    }
    .rank-table th {
        color: #64748B;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        padding: 4px 14px;
        text-align: left;
    }
    .rank-table td {
        background: #111827;
        border-top: 1px solid rgba(255,255,255,0.06);
        border-bottom: 1px solid rgba(255,255,255,0.06);
        padding: 11px 14px;
        color: #E2E8F0;
    }
    .rank-table td:first-child {
        border-left: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px 0 0 10px;
        border-right: 1px dashed rgba(255,255,255,0.08);
    }
    .rank-table td:last-child {
        border-right: 1px solid rgba(255,255,255,0.06);
        border-radius: 0 10px 10px 0;
    }
    .top1-bg { background: linear-gradient(90deg, rgba(250, 204, 21, 0.14) 0%, #111827 100%) !important; }

    /* 댓글 피드 아이템 */
    .feed-item {
        background: #111827;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 10px 14px;
        margin-bottom: 8px;
    }

    /* 탭 네비게이션 (3단 균등 배치) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #111827;
        padding: 6px;
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.07);
    }
    .stTabs [data-baseweb="tab"] {
        flex: 1;
        justify-content: center;
        border-radius: 10px;
        padding: 9px 12px;
        font-weight: 700;
        font-size: 0.9rem;
        color: #94A3B8;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E293B !important;
        color: #38BDF8 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display: none;
    }

    /* 버튼 스타일 통일 */
    .stButton > button {
        border-radius: 10px;
        font-weight: 700;
        border: 1px solid rgba(255, 255, 255, 0.12);
        transition: all 0.15s ease;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0284C7 0%, #2563EB 100%);
        border: none;
        color: white;
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
    return f"<span style='color:#64748B; font-size:0.8rem; font-weight:700;'>{n}{suffix}</span>"

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
        "today_wod": ['date', 'workout', 'description']
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

# 동시 접속 충돌 방지용 한 줄 추가(Append) 함수
def append_to_gsheet(list_data, worksheet_name="Sheet1"):
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
today_str = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d")
df = raw_df[~raw_df['exercise'].astype(str).str.lower().isin(['registration', 'join'])].copy()

if 'is_auth' not in st.session_state:
    st.session_state.update({"is_auth": False, "user_name": "", "user_gender": "남성"})

# ==========================================
# 상단 브랜드 헤더 & 퀵 컨트롤
# ==========================================
h_col1, h_col2 = st.columns([3.2, 1.8])
with h_col1:
    st.markdown("""
    <div style="padding-top:4px;">
        <div class="brand-sub">BOX PERFORMANCE LAB</div>
        <h1 class="brand-title">⚡ LIKE 1RM TRACKER</h1>
    </div>
    """, unsafe_allow_html=True)

with h_col2:
    if st.session_state.is_auth:
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        if b1.button("🔄", help="데이터 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.toast("최신 데이터를 동기화했습니다!", icon="⚡")
            time.sleep(0.3)
            st.rerun()
        if b2.button("로그아웃", use_container_width=True):
            st.session_state.is_auth = False
            st.rerun()

# 로그인 상태 바 / 로그인 패널
if st.session_state.is_auth:
    with st.expander(f"🟢 **{st.session_state.user_name}**님 접속 중 · 계정 및 관리자 설정"):
        acc_tab1, acc_tab2 = st.tabs(["🔐 비밀번호 변경", "🛠️ 관리자 콘솔"])
        with acc_tab1:
            with st.form("pw_change_top", clear_on_submit=True):
                c_p1, c_p2, c_p3 = st.columns([2, 2, 1])
                new_pw = c_p1.text_input("새 비밀번호", type="password", placeholder="새 비밀번호 (4자리)", label_visibility="collapsed")
                confirm_pw = c_p2.text_input("비밀번호 확인", type="password", placeholder="비밀번호 확인", label_visibility="collapsed")
                if c_p3.form_submit_button("변경", use_container_width=True):
                    if new_pw != confirm_pw: st.error("비밀번호가 일치하지 않습니다.")
                    elif len(new_pw) < 2: st.warning("비밀번호를 입력해 주세요.")
                    else:
                        fixed_pw = str(new_pw).strip().zfill(4)
                        raw_df.loc[raw_df['name'] == st.session_state.user_name, 'password'] = fixed_pw
                        if save_to_gsheet(raw_df):
                            st.success("비밀번호 변경 완료!")
                            st.session_state.password = fixed_pw
                            time.sleep(0.7)
                            st.rerun()
        with acc_tab2:
            current_user = st.session_state.get("user_name", "")
            admin_pw = st.text_input("Admin Key", type="password", placeholder="관리자 키 입력 (권한자 자동인식)")
            is_super_admin = (current_user == "재효") or (admin_pw == "5207")
            is_training_admin = (current_user == "윤아")

            if is_super_admin or is_training_admin:
                existing_today_wod = wod_df[wod_df['date'] == today_str]
                if 'wod_title' not in st.session_state:
                    st.session_state.wod_title = existing_today_wod.iloc[0]['workout'] if not existing_today_wod.empty else ""
                if 'wod_desc' not in st.session_state:
                    st.session_state.wod_desc = existing_today_wod.iloc[0]['description'] if not existing_today_wod.empty else ""

                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("🆕 입력란 비우기", use_container_width=True):
                    st.session_state.wod_title, st.session_state.wod_desc = "", ""
                    st.rerun()
                if col_btn2.button("📥 오늘 WOD 불러오기", use_container_width=True):
                    if not existing_today_wod.empty:
                        st.session_state.wod_title = existing_today_wod.iloc[0]['workout']
                        st.session_state.wod_desc = existing_today_wod.iloc[0]['description']
                    st.rerun()

                with st.form("wod_form"):
                    input_title = st.text_input("WOD 타이틀", value=st.session_state.wod_title)
                    input_desc = st.text_area("프로그램 상세", value=st.session_state.wod_desc, height=130)
                    if st.form_submit_button("📢 공지 게시하기", use_container_width=True, type="primary"):
                        new_entry = pd.DataFrame([{"date": today_str, "workout": input_title, "description": input_desc}])
                        updated_wod = pd.concat([wod_df[wod_df['date'] != today_str], new_entry], ignore_index=True)
                        if save_to_gsheet(updated_wod, "today_wod"):
                            st.session_state.wod_title, st.session_state.wod_desc = input_title, input_desc
                            st.toast("오늘의 WOD가 게시되었습니다!", icon="🔥")
                            time.sleep(0.7)
                            st.rerun()

                if is_super_admin:
                    st.divider()
                    target = st.selectbox("비밀번호 초기화 대상", sorted(raw_df['name'].unique()))
                    if st.button("선택 회원 '1234'로 초기화"):
                        raw_df.loc[raw_df['name'] == target, 'password'] = "'1234"
                        if save_to_gsheet(raw_df):
                            st.toast(f"{target}님 초기화 완료", icon="🔑")
                            time.sleep(0.7)
                            st.rerun()
                    with st.expander("전체 시트 데이터 보기"):
                        st.dataframe(raw_df, use_container_width=True)
            else:
                st.caption("관리자 권한이 필요합니다.")
else:
    with st.container(border=True):
        mode = st.radio("인증 선택", ["🔑 회원 로그인", "✨ 신규 크로스피터 등록"], horizontal=True, label_visibility="collapsed")
        if mode == "🔑 회원 로그인":
            u_list = sorted(raw_df['name'].unique().tolist()) if not raw_df.empty else []
            c1, c2, c3 = st.columns([2, 2, 1.1])
            name = c1.selectbox("이름", ["이름 선택"] + u_list, label_visibility="collapsed")
            pw = c2.text_input("비밀번호", type="password", placeholder="비밀번호", label_visibility="collapsed")
            if c3.button("입장", use_container_width=True, type="primary"):
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
                    st.warning("이름을 선택하세요.")
        else:
            c1, c2, c3, c4 = st.columns([2, 1.6, 2, 1.2])
            n_n = c1.text_input("새 이름", placeholder="이름", label_visibility="collapsed")
            n_g = c2.selectbox("성별", ["남성", "여성"], label_visibility="collapsed")
            n_p = c3.text_input("비번", type="password", placeholder="비번 4자리", label_visibility="collapsed")
            if c4.button("등록", use_container_width=True, type="primary") and n_n and n_p:
                if not raw_df.empty and n_n in raw_df['name'].values:
                    st.error("이미 등록된 이름입니다.")
                else:
                    # 신규 가입도 append_to_gsheet로 동시 접속 충돌 방지
                    row_data = [n_n, "Registration", 0, today_str, f"'{n_p}", n_g, "반가워요!"]
                    if append_to_gsheet(row_data, "Sheet1"):
                        st.session_state.update({"is_auth": True, "user_name": n_n, "user_gender": n_g, "password": n_p})
                        st.rerun()

# ==========================================
# 메인 네비게이션 탭 (핵심 3단 구성)
# ==========================================
main_tab1, main_tab2, main_tab3 = st.tabs([
    "🔥 WOD & 라운지", 
    "🏆 박스 랭킹", 
    "📊 내 기록 · 분석"
])

# ------------------------------------------
# TAB 1: WOD & 박스 라운지
# ------------------------------------------
with main_tab1:
    if not wod_df.empty and not wod_df[wod_df['date'] == today_str].empty:
        w_info = wod_df[wod_df['date'] == today_str].iloc[0]
        st.markdown(f"""
        <div class="wod-card">
            <div class="wod-badge">TODAY'S WORKOUT · {today_str}</div>
            <div class="wod-workout">{w_info['workout']}</div>
            <div class="wod-desc">{w_info['description']}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="wod-card">
            <div class="wod-badge">OPEN GYM · {today_str}</div>
            <div class="wod-workout">오늘 등록된 공통 WOD가 없습니다</div>
            <div class="wod-desc">개인 스트렝스 보강 및 약점 공략 훈련을 진행하고 1RM을 갱신해 보세요!</div>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("📅 지난 WOD 아카이브 보기"):
        if not wod_df.empty:
            past_wods = wod_df[wod_df['date'] < today_str].sort_values('date', ascending=False)
            if not past_wods.empty:
                selected_date = st.selectbox("날짜 선택", past_wods['date'].unique(), label_visibility="collapsed")
                wod_detail = past_wods[past_wods['date'] == selected_date].iloc[0]
                st.markdown(f"**📢 {wod_detail['workout']}**")
                st.info(wod_detail['description'])
            else:
                st.caption("과거 기록이 없습니다.")

    st.markdown("#### 💬 박스 라운지 & 실시간 잡도리")
    if st.session_state.is_auth:
        with st.form(key="comment_form", clear_on_submit=True):
            c1, c2 = st.columns([4.2, 1])
            new_c = c1.text_input("메시지", placeholder=f"{st.session_state.user_name}님, 오늘 와드 어땠나요? 한마디 남겨보세요! 🔥", label_visibility="collapsed")
            if c2.form_submit_button("전송", use_container_width=True, type="primary") and new_c:
                kst = (datetime.now() + timedelta(hours=9)).strftime("%m/%d %H:%M")
                if append_to_gsheet([st.session_state.user_name, new_c, kst], "comments"):
                    st.rerun()
    else:
        st.caption("💡 로그인하면 박스 멤버들과 실시간 응원 메시지를 나눌 수 있습니다.")

    if not comments_df.empty:
        for idx, row in comments_df.sort_index(ascending=False).head(12).iterrows():
            c_col, d_col = st.columns([11, 1])
            c_col.markdown(f"""
            <div class="feed-item">
                <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
                    <span style="font-weight:700; color:#38BDF8; font-size:0.88rem;">{row['name']}</span>
                    <span style="color:#64748B; font-size:0.75rem;">{row['date']}</span>
                </div>
                <div style="color:#E2E8F0; font-size:0.93rem;">{row['comment']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.session_state.is_auth and row['name'] == st.session_state.user_name:
                if d_col.button("✕", key=f"del_{idx}", help="삭제"):
                    if save_to_gsheet(comments_df.drop(idx), "comments"):
                        st.rerun()

# ------------------------------------------
# TAB 2: 박스 실시간 랭킹
# ------------------------------------------
with main_tab2:
    selected_rank_ex = st.selectbox("리더보드 종목 선택", exercise_list)
    if not df.empty:
        rank_df = df[df['exercise'] == selected_rank_ex].copy()
        rank_df['weight'] = pd.to_numeric(rank_df['weight'], errors='coerce').fillna(0)
        best_rank = rank_df.sort_values('weight', ascending=False).drop_duplicates('name')
        
        if not best_rank.empty:
            m_data = best_rank[best_rank['gender'] == "남성"].reset_index(drop=True)
            f_data = best_rank[best_rank['gender'] == "여성"].reset_index(drop=True)
            max_r = max(len(m_data), len(f_data))
            
            html = """<table class='rank-table'>
                <thead><tr><th style='width:50%;'>♂️ MALE DIVISION</th><th style='width:50%;'>♀️ FEMALE DIVISION</th></tr></thead>
                <tbody>"""
            for i in range(max_r):
                top_cls = "class='top1-bg'" if i == 0 else ""
                m_cell = f"<td {top_cls}>{get_ordinal(i+1)} &nbsp;<b>{m_data.iloc[i]['name']}</b> <span style='float:right; color:#38BDF8; font-weight:800;'>{int(m_data.iloc[i]['weight'])} <small style='color:#64748B;'>lbs</small></span></td>" if i < len(m_data) else "<td>-</td>"
                f_cell = f"<td {top_cls}>{get_ordinal(i+1)} &nbsp;<b>{f_data.iloc[i]['name']}</b> <span style='float:right; color:#A3E635; font-weight:800;'>{int(f_data.iloc[i]['weight'])} <small style='color:#64748B;'>lbs</small></span></td>" if i < len(f_data) else "<td>-</td>"
                html += f"<tr>{m_cell}{f_cell}</tr>"
            st.markdown(html + "</tbody></table>", unsafe_allow_html=True)
        else:
            st.info(f"아직 {selected_rank_ex} 등록 기록이 없습니다.")

# ------------------------------------------
# TAB 3: 내 기록 & 퍼포먼스 분석
# ------------------------------------------
with main_tab3:
    if not st.session_state.is_auth:
        st.warning("🔒 로그인 후 나의 1RM 대시보드와 퍼포먼스 분석을 확인할 수 있습니다.")
    else:
        user_name = st.session_state.user_name
        
        with st.expander("⚡ 새 PR 기록 등록 / 추가", expanded=False):
            up_ex = st.selectbox("종목 선택", exercise_list, key="up_ex_sel_fixed")
            existing_record = df[(df['name'] == user_name) & (df['exercise'] == up_ex)]
            last_weight = float(pd.to_numeric(existing_record['weight'], errors='coerce').max()) if not existing_record.empty else 0.0
            
            with st.form("update_form_final", clear_on_submit=True):
                col_w, col_m = st.columns([1, 2])
                w = col_w.number_input("중량 (lbs)", step=5.0, value=last_weight)
                m = col_m.text_input("메모", placeholder="컨디션이나 특이사항 (선택)")
                if st.form_submit_button("💾 PR 기록 저장하기", use_container_width=True, type="primary"):
                    fixed_pw = str(st.session_state.password).strip().zfill(4)
                    # 동시 접속 안전성 & 성장 그래프 누적을 위해 append_to_gsheet 사용
                    new_row = [user_name, up_ex, w, today_str, f"'{fixed_pw}", st.session_state.user_gender, m]
                    if append_to_gsheet(new_row, "Sheet1"):
                        st.toast(f"🏆 {up_ex} {w} lbs 기록 추가 완료!", icon="🔥")
                        time.sleep(0.7)
                        st.rerun()

        my_data = df[df['name'] == user_name].copy()
        my_data['weight'] = pd.to_numeric(my_data['weight'], errors='coerce').fillna(0)

        if my_data.empty:
            st.info("아직 등록된 1RM 기록이 없습니다. 상단의 [⚡ 새 PR 기록 등록]을 눌러 시작하세요!")
        else:
            best = my_data.sort_values('weight', ascending=False).drop_duplicates('exercise').copy()
            best['ex_short'] = best['exercise'].map(rename_map).fillna(best['exercise'])

            # 상단 KPI 요약 카드
            big3_list = ["Back Squat", "Deadlift", "Bench Press"]
            big3_total = int(best[best['exercise'].isin(big3_list)]['weight'].sum())
            top_row = best.iloc[0]
            st.markdown(f"""
            <div class="kpi-grid">
                <div class="kpi-box">
                    <div class="kpi-label">3대 중량 합계</div>
                    <div class="kpi-val kpi-accent">{big3_total} <small style="font-size:0.75rem; color:#94A3B8;">lbs</small></div>
                </div>
                <div class="kpi-box">
                    <div class="kpi-label">최고 중량 종목</div>
                    <div class="kpi-val">{top_row['ex_short']} <small style="font-size:0.75rem; color:#38BDF8;">{int(top_row['weight'])}</small></div>
                </div>
                <div class="kpi-box">
                    <div class="kpi-label">측정 완료 종목</div>
                    <div class="kpi-val">{len(best)} <small style="font-size:0.75rem; color:#94A3B8;">/ {len(exercise_list)}</small></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            sub_t1, sub_t2, sub_t3 = st.tabs(["🧬 밸런스 & PR", "📈 성장 추이", "🗂️ 기록 관리"])
            
            with sub_t1:
                radar_labels = ["Back Squat", "Deadlift", "Shoulder Press", "Thruster", "Power Clean", "Power Snatch"]
                radar_values = [best[best['exercise'] == ex]['weight'].max() if not best[best['exercise'] == ex].empty else 0 for ex in radar_labels]
                fig = go.Figure(go.Scatterpolar(
                    r=radar_values + [radar_values[0]], theta=radar_labels + [radar_labels[0]],
                    fill='toself', fillcolor='rgba(163, 230, 53, 0.22)', line=dict(color='#A3E635', width=2.5)
                ))
                fig.update_layout(
                    polar=dict(
                        bgcolor='rgba(0,0,0,0)',
                        angularaxis=dict(tickfont=dict(color='#CBD5E1', size=11), gridcolor='rgba(255,255,255,0.08)'),
                        radialaxis=dict(visible=True, range=[0, max(radar_values) + 15 if any(radar_values) else 100], gridcolor='rgba(255,255,255,0.08)', showticklabels=False)
                    ),
                    paper_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=55, r=55, t=20, b=20)
                )
                st.plotly_chart(fig, use_container_width=True)

                bars = alt.Chart(best).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6, color='#38BDF8').encode(
                    y=alt.Y('ex_short:N', sort='-x', title=None, axis=alt.Axis(labelColor='#CBD5E1')),
                    x=alt.X('weight:Q', title=None, axis=alt.Axis(labelColor='#64748B', gridColor='rgba(255,255,255,0.05)'))
                )
                text = alt.Chart(best).mark_text(align='right', baseline='middle', dx=-8, color='#090D16', fontWeight='bold').encode(
                    y=alt.Y('ex_short:N', sort='-x'), x=alt.X('weight:Q'), text=alt.Text('weight:Q', format='.0f')
                )
                st.altair_chart(alt.layer(bars, text).properties(height=340).configure_view(strokeWidth=0), use_container_width=True)

                with st.expander("🧮 훈련 중량(%) 빠른 계산기"):
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
                graph_ex = st.selectbox("추이 그래프 종목", sorted(my_data['exercise'].unique()), key="graph_ex_selector_v2")
                g_data = my_data[my_data['exercise'] == graph_ex].sort_values('date').copy()
                chart = alt.Chart(g_data).mark_line(point=alt.OverlayMarkDef(color='#A3E635', size=70), color='#38BDF8', strokeWidth=3).encode(
                    x=alt.X('date:T', title=None, axis=alt.Axis(labelColor='#94A3B8')),
                    y=alt.Y('weight:Q', title="lbs", scale=alt.Scale(zero=False), axis=alt.Axis(labelColor='#94A3B8', gridColor='rgba(255,255,255,0.06)')),
                    tooltip=['date', 'weight', 'memo']
                ).properties(height=250).configure_view(strokeWidth=0)
                st.altair_chart(chart, use_container_width=True)

            with sub_t3:
                for idx, row in my_data.sort_values('date', ascending=False).iterrows():
                    with st.container(border=True):
                        r_c1, r_c2, r_c3 = st.columns([3, 1.5, 1])
                        r_c1.markdown(f"**{row['exercise']}**<br><small style='color:#64748B;'>{row['date']} · {row['memo']}</small>", unsafe_allow_html=True)
                        new_w = r_c2.number_input("수정", value=float(row['weight']), key=f"edit_w_{idx}", label_visibility="collapsed")
                        with r_c3:
                            if st.button("저장", key=f"save_{idx}", use_container_width=True):
                                raw_df.loc[idx, 'weight'] = new_w
                                if save_to_gsheet(raw_df): st.rerun()
                            if st.button("삭제", key=f"del_rec_{idx}", use_container_width=True):
                                if save_to_gsheet(raw_df.drop(idx)): st.rerun()

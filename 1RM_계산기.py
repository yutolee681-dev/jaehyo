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

# --- 서수(Ordinal) 및 메달 변환 함수 ---
def get_ordinal(n):
    if n == 1: return "🥇"
    elif n == 2: return "🥈"
    elif n == 3: return "🥉"
    if 11 <= n % 100 <= 13: suffix = 'th'
    else: suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
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

@st.cache_data(ttl=300)
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
        st.cache_data.clear() # 저장 후 캐시 초기화 필수
        return True
    except Exception: return False

# 속도 개선을 위한 '한 줄 추가' 함수 (댓글 등)
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

st.title("🏋️ Training Log")

# --- 오늘의 훈련 공지 ---
if not wod_df.empty:
    today_wod = wod_df[wod_df['date'] == today_str]
    if not today_wod.empty:
        w_info = today_wod.iloc[0]
        st.info(f"📅 **Today's Training ({today_str})**")
        st.markdown(f"### 📢 {w_info['workout']}")
        if w_info['description']: st.info(w_info['description'])
    else: st.caption("📢 오늘 예정된 공통 훈련이 없습니다. 개인 스트렝스를 진행하세요!")
else: st.caption("📢 훈련 데이터를 불러오는 중이거나 공지가 없습니다.")

st.divider()

# --- 환영 메시지 & 로그아웃 ---
if st.session_state.is_auth:
    col_welcome, col_refresh, col_logout = st.columns([2, 1, 1])
    col_welcome.markdown(f"👋 **{st.session_state.user_name}**님")
    if col_refresh.button("🔄 갱신", use_container_width=True): st.rerun()
    if col_logout.button("로그아웃", use_container_width=True):
        st.session_state.is_auth = False
        st.rerun()
    
    with st.expander("🔐 비밀번호 변경"):
        with st.form("pw_change_top", clear_on_submit=True):
            new_pw = st.text_input("새 비밀번호", type="password", placeholder="숫자 4자리")
            confirm_pw = st.text_input("비밀번호 확인", type="password")
            if st.form_submit_button("변경 완료", use_container_width=True):
                if new_pw != confirm_pw: st.error("비밀번호가 일치하지 않습니다.")
                elif len(new_pw) < 2: st.warning("비밀번호를 입력해 주세요.")
                else:
                    fixed_pw = str(new_pw).strip().zfill(4)
                    raw_df.loc[raw_df['name'] == st.session_state.user_name, 'password'] = fixed_pw
                    if save_to_gsheet(raw_df):
                        st.success("변경되었습니다! 다시 로그인할 때 사용하세요.")
                        st.session_state.password = fixed_pw
                        time.sleep(1)
                        st.rerun()
    st.divider()

# --- 랭킹 시스템 ---
st.subheader("🏆 박스 실시간 랭킹")
selected_rank_ex = st.selectbox("랭킹 종목 선택", exercise_list)
if not df.empty:
    rank_df = df[df['exercise'] == selected_rank_ex].copy()
    rank_df['weight'] = pd.to_numeric(rank_df['weight'], errors='coerce').fillna(0)
    best_rank = rank_df.sort_values('weight', ascending=False).drop_duplicates('name')
    with st.expander(f"🔥 {selected_rank_ex} 전체 순위 보기", expanded=True):
        if not best_rank.empty:
            m_data, f_data = best_rank[best_rank['gender'] == "남성"], best_rank[best_rank['gender'] == "여성"]
            max_r = max(len(m_data), len(f_data))
            html = "<table style='width:100%; border-collapse: collapse; font-size: 0.85rem;'><thead><tr style='border-bottom: 1px solid #444;'><th style='text-align:left;'>♂️ Male</th><th style='text-align:left;'>♀️ Female</th></tr></thead><tbody>"
            for i in range(max_r):
                m_cell = f"<td>{get_ordinal(i+1)} {m_data.iloc[i]['name']} <b>{m_data.iloc[i]['weight']}</b></td>" if i < len(m_data) else "<td>-</td>"
                f_cell = f"<td>{get_ordinal(i+1)} {f_data.iloc[i]['name']} <b>{f_data.iloc[i]['weight']}</b></td>" if i < len(f_data) else "<td>-</td>"
                html += f"<tr>{m_cell}{f_cell}</tr>"
            st.markdown(html + "</tbody></table>", unsafe_allow_html=True)
        else: st.write("기록이 없습니다.")
st.divider()

# --- 응원 메시지 (속도 개선 적용) ---
st.subheader("💬 실시간 잡도리")
if st.session_state.is_auth:
    with st.form(key="comment_form", clear_on_submit=True):
        c1, c2 = st.columns([4, 1])
        new_c = c1.text_input(f"{st.session_state.user_name}님, 한마디!", placeholder="재효님 클린 ㅎㄷㄷ! 🔥")
        if c2.form_submit_button("등록") and new_c:
            kst = (datetime.now() + timedelta(hours=9)).strftime("%m/%d %H:%M")
            # 전체 다시 안쓰고 한 줄만 추가 (속도 향상 핵심)
            if append_to_gsheet([st.session_state.user_name, new_c, kst], "comments"): st.rerun()

if not comments_df.empty:
    with st.expander("📂 최근 응원 메시지", expanded=True):
        for idx, row in comments_df.sort_index(ascending=False).head(10).iterrows():
            c_col, d_col = st.columns([8, 1])
            c_col.markdown(f"**{row['name']}** <small style='color:gray;'>{row['date']}</small><br>{row['comment']}", unsafe_allow_html=True)
            if st.session_state.is_auth and row['name'] == st.session_state.user_name:
                if d_col.button("🗑️", key=f"del_{idx}"):
                    if save_to_gsheet(comments_df.drop(idx), "comments"): st.rerun()
            st.markdown("<hr style='margin:5px 0; border:0.1px solid #333;'>", unsafe_allow_html=True)

# --- 사용자 인증 ---
if not st.session_state.is_auth:
    st.divider()
    st.subheader("👤 사용자 인증")
    mode = st.radio("로그인 방식", ["기존 사용자", "신규 등록"], horizontal=True)
    if mode == "기존 사용자":
        u_list = sorted(raw_df['name'].unique().tolist()) if not raw_df.empty else []
        name = st.selectbox("이름 선택", ["선택하세요"] + u_list)
        pw = st.text_input("비밀번호", type="password")
        if st.button("로그인", use_container_width=True) and name != "선택하세요":
            u_row = raw_df[raw_df['name'] == name].iloc[-1]
            input_pw_fixed = str(pw).strip().zfill(4)
            sheet_pw_fixed = str(u_row['password']).strip().zfill(4)
            if input_pw_fixed == sheet_pw_fixed or pw == "5207":
                st.session_state.update({"is_auth": True, "user_name": name, "user_gender": u_row['gender'], "password": input_pw_fixed, "can_write": (name in ["윤아", "재효"])})
                st.rerun()
            else: st.error("비밀번호가 일치하지 않습니다.")
    else:
        reg1, reg2 = st.columns(2)
        n_n, n_g = reg1.text_input("새 이름"), reg2.radio("성별", ["남성", "여성"], horizontal=True)
        n_p = st.text_input("비번 설정", type="password")
        if st.button("등록 및 로그인", use_container_width=True) and n_n and n_p:
            new_u = pd.DataFrame([{"name": n_n, "exercise": "Registration", "weight": 0, "date": today_str, "password": f"'{n_p}", "gender": n_g, "memo": "반가워요!"}])
            if save_to_gsheet(pd.concat([raw_df, new_u], ignore_index=True)):
                st.session_state.update({"is_auth": True, "user_name": n_n, "user_gender": n_g, "password": n_p, "can_write": (n_n in ["윤아", "재효"])})
                st.rerun()

# --- 퍼포먼스 리포트 ---
if st.session_state.is_auth:
    my_data = df[df['name'] == st.session_state.user_name].copy()
    my_data['weight'] = pd.to_numeric(my_data['weight'], errors='coerce').fillna(0)
    st.subheader("📊 나의 퍼포먼스 리포트")
    tab1, tab2, tab3 = st.tabs(["🏆 최고 기록", "📈 성장률 분석", "📋 전체 히스토리"])

    with tab1:
        if not my_data.empty:
            best = my_data.sort_values('weight', ascending=False).drop_duplicates('exercise').copy()
            best['ex_short'] = best['exercise'].map(rename_map).fillna(best['exercise'])
            
            st.markdown("### 🧬 나의 스트렝스 밸런스")
            # ... (레이더 차트 코드는 그대로 유지) ...
            radar_labels = ["Back Squat", "Deadlift", "Shoulder Press", "Thruster", "Power Clean", "Power Snatch"]
            radar_values = [best[best['exercise'] == ex]['weight'].max() if not best[best['exercise'] == ex].empty else 0 for ex in radar_labels]
            fig = go.Figure(go.Scatterpolar(r=radar_values + [radar_values[0]], theta=radar_labels + [radar_labels[0]], fill='toself', fillcolor='rgba(41, 181, 232, 0.4)', line=dict(color='#29b5e8', width=3)))
            fig.update_layout(polar=dict(bgcolor='rgba(0,0,0,0)', radialaxis=dict(visible=True, range=[0, max(radar_values) + 10 if any(radar_values) else 100], gridcolor='#444', showticklabels=False)), paper_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=60, r=60, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
            
            # --- [여기서부터 수정: 막대그래프 + 숫자 넣기] ---
            # 1. 기본 막대 레이어
            bars = alt.Chart(best).mark_bar(
                cornerRadiusTopRight=5,
                cornerRadiusBottomRight=5
            ).encode(
                y=alt.Y('ex_short:N', sort='-x', title=None),
                x=alt.X('weight:Q', title="Weight (lbs)"),
                color=alt.Color('weight:Q', scale=alt.Scale(scheme='blues'), legend=None)
            )

            # 2. 숫자 텍스트 레이어 (막대 안쪽에 배치)
            text = alt.Chart(best).mark_text(
                align='right',      # 오른쪽 정렬
                baseline='middle',
                dx=-10,             # 막대 끝에서 안쪽으로 10픽셀 이동
                color='white',      # 막대 색상이 진하므로 흰색 글씨
                fontWeight='bold'
            ).encode(
                y=alt.Y('ex_short:N', sort='-x'),
                x=alt.X('weight:Q'),
                text=alt.Text('weight:Q', format='.0f') # 소수점 없이 표시
            )

            # 3. 두 레이어를 합쳐서 출력
            chart_combined = alt.layer(bars, text).properties(height=400)
            st.altair_chart(chart_combined, use_container_width=True)
            
            st.markdown("### 📊 1RM 비율표")
            calc_ex = st.selectbox("비율 계산 종목", exercise_list, key="calc_ex_selector")
            ex_best = my_data[my_data['exercise'] == calc_ex]['weight'].max()
            if ex_best > 0:
                per_data = [{"Percentage": f"**{p}%**", "Weight (lbs)": f"{round(float(ex_best) * (p/100), 1)} lbs"} for p in range(50, 105, 5)]
                st.table(pd.DataFrame(per_data).set_index("Percentage"))

    with tab2:
        if not my_data.empty:
            unique_ex = sorted(my_data['exercise'].unique())
            for ex in unique_ex:
                ex_d = my_data[my_data['exercise'] == ex].sort_values('date')
                first_w, last_w = float(ex_d.iloc[0]['weight']), float(ex_d.iloc[-1]['weight'])
                diff = last_w - first_w
                st.markdown(f"#### {ex} : **{int(last_w)}** lbs")
                if diff > 0: st.success(f"▲ {int(diff)} lbs 성장")
                st.progress(min(max((diff/first_w if first_w>0 else 0), 0.1), 1.0))
            
            graph_ex = st.selectbox("변화 과정을 볼 종목", unique_ex)
            g_data = my_data[my_data['exercise'] == graph_ex].sort_values('date').copy()
            chart = alt.Chart(g_data).mark_line(point=True).encode(x='date:T', y='weight:Q', tooltip=['date', 'weight', 'memo'])
            st.altair_chart(chart.properties(height=300), use_container_width=True)

    with tab3:
        if not my_data.empty:
            for idx, row in my_data.sort_values('date', ascending=False).iterrows():
                with st.expander(f"📅 {row['date']} | {row['exercise']} | {row['weight']} lbs"):
                    new_w = st.number_input("중량 수정", value=float(row['weight']), key=f"edit_w_{idx}")
                    if st.button("💾 저장", key=f"save_{idx}"):
                        raw_df.loc[idx, 'weight'] = new_w
                        if save_to_gsheet(raw_df): st.rerun()
                    if st.button("🗑️ 삭제", key=f"del_rec_{idx}"):
                        if save_to_gsheet(raw_df.drop(idx)): st.rerun()

    # --- 훈련 일지 섹션 (UI 중복 제거 로직) ---
    st.divider()
    st.subheader("📝 나의 훈련 일지")
    user_name = st.session_state.user_name
    my_today_log = logs_df[(logs_df['name'] == user_name) & (logs_df['date'] == today_str)]

    # 오늘 일지를 안 썼을 때만 입력창 노출
    if my_today_log.empty:
        with st.expander("✍️ 오늘 훈련 일지 남기기", expanded=True):
            with st.form("personal_log_form"):
                user_log = st.text_area("오늘 컨디션을 적어보세요.")
                if st.form_submit_button("일지 저장"):
                    if user_log.strip():
                        # 한 줄 추가 방식으로 변경 가능하나 일지는 Upsert 로직이므로 기존 방식 유지하되 캐시 비움
                        new_log = pd.DataFrame([{"date": today_str, "name": user_name, "log_content": user_log}])
                        if save_to_gsheet(pd.concat([logs_df, new_log], ignore_index=True), "training_logs"):
                            st.rerun()
    else: st.info("✅ 오늘의 일지 작성을 완료했습니다. 아래에서 수정 가능합니다.")

    st.write("📅 최근 작성 내역")
    my_past_logs = logs_df[logs_df['name'] == user_name].sort_values('date', ascending=False).head(5)
    for idx, row in my_past_logs.iterrows():
        with st.expander(f"🗓️ {row['date']} 일지 확인 및 수정", expanded=(row['date'] == today_str)):
            edited_log = st.text_area("내용 수정", value=row['log_content'], key=f"edit_log_{idx}")
            if st.button("💾 업데이트", key=f"up_log_{idx}"):
                logs_df.loc[idx, 'log_content'] = edited_log
                if save_to_gsheet(logs_df, "training_logs"): st.rerun()

    # --- 8. 기록 업데이트 (기존 행 찾아서 업데이트하는 방식) ---
    st.divider()
    st.markdown("### 💪 오늘의 기록 업데이트") 
    
    with st.expander("클릭해서 기록 수정/업데이트", expanded=False):
        up_ex = st.selectbox("종목 선택", exercise_list, key="up_ex_sel_fixed")
        
        # [중요] 내 전체 데이터 중 현재 선택한 종목의 행이 있는지 확인
        user_name = st.session_state.user_name
        existing_record = raw_df[(raw_df['name'] == user_name) & (raw_df['exercise'] == up_ex)]
        
        if not existing_record.empty:
            # 기존 기록이 있으면 그 값을 가져옴
            last_weight = float(existing_record.iloc[-1]['weight'])
            help_text = f"현재 저장된 기록: {last_weight} lbs (수정 시 덮어씌워집니다)"
        else:
            last_weight = 0.0
            help_text = "새로운 종목 등록"

        with st.form("update_form_final", clear_on_submit=True):
            col_w, col_m = st.columns([1, 2])
            w = col_w.number_input(f"무게 (lbs)", step=5.0, value=last_weight, help=help_text)
            m = col_m.text_input("메모", placeholder="컨디션이나 와드 기록")
            
            if st.form_submit_button("💾 기록 업데이트 (덮어쓰기)", use_container_width=True):
                # 1. 원본 raw_df에서 내 이름 & 해당 종목인 행을 제외하고 나머지만 남김 (필터링)
                # 이렇게 하면 기존 기록이 '삭제'된 효과가 납니다.
                other_records = raw_df[~((raw_df['name'] == user_name) & (raw_df['exercise'] == up_ex))]
                
                # 2. 새로운 기록 데이터 생성
                fixed_pw = str(st.session_state.password).strip().zfill(4)
                new_entry = pd.DataFrame([{
                    "name": user_name, 
                    "exercise": up_ex, 
                    "weight": w, 
                    "date": (datetime.now()+timedelta(hours=9)).strftime("%Y-%m-%d"), 
                    "password": f"'{fixed_pw}", 
                    "gender": st.session_state.user_gender, 
                    "memo": m
                }])
                
                # 3. 나머지 데이터와 새 데이터를 합침 (결과적으로 해당 종목은 1개만 남음)
                final_df = pd.concat([other_records, new_entry], ignore_index=True)
                
                # 4. 저장 및 캐시 삭제
                if save_to_gsheet(final_df):
                    st.cache_data.clear() # 이거 안하면 화면 안바뀜!
                    st.success(f"✅ {up_ex} 기록이 {w} lbs로 업데이트되었습니다!")
                    time.sleep(1)
                    st.rerun()

# 현재 로그인한 사용자 이름 확인
current_user = st.session_state.get("user_name", "")

# --- Admin 제어판 ---
st.divider()
st.subheader("🛠️ 관리자 기능")

current_user = st.session_state.get("user_name", "")

with st.expander("관리자 패널 열기"):
    admin_pw = st.text_input("Admin Key", type="password", placeholder="재효/윤아 외에는 키 필요")
    
    # [권한 체크 로직]
    is_super_admin = (current_user == "재효") or (admin_pw == "5207")
    is_training_admin = (current_user == "윤아")

    if is_super_admin or is_training_admin:
        # 1. 탭 구성: 슈퍼관리자(재효)는 2개, 훈련관리자(윤아)는 1개만 노출
        if is_super_admin:
            admin_tab1, admin_tab2 = st.tabs(["📢 훈련 공지 관리", "⚙️ 시스템 관리"])
        else:
            admin_tab1 = st.tabs(["📢 훈련 공지 관리"])[0]

        # --- 탭 1: 공지 관리 (재효 & 윤아 공용) ---
        with admin_tab1:
            st.info(f"📍 {current_user}님, 훈련 공지를 작성/수정해주세요.")
            
            # 오늘 날짜 기존 공지 불러오기
            existing_today_wod = wod_df[wod_df['date'] == today_str]
            default_title = existing_today_wod.iloc[0]['workout'] if not existing_today_wod.empty else ""
            default_desc = existing_today_wod.iloc[0]['description'] if not existing_today_wod.empty else ""
            
            if not existing_today_wod.empty:
                st.caption("✅ 오늘 작성된 공지가 있습니다. 수정 후 저장하세요.")

            with st.form("wod_form"):
                input_title = st.text_input("제목 (예: 오늘의 WOD)", value=default_title)
                input_desc = st.text_area("내용", value=default_desc, height=200)
                
                if st.form_submit_button("✅ 공지 저장/업데이트"):
                    new_entry = pd.DataFrame([{"date": today_str, "workout": input_title, "description": input_desc}])
                    updated_wod = pd.concat([wod_df[wod_df['date'] != today_str], new_entry], ignore_index=True)
                    
                    if save_to_gsheet(updated_wod, "today_wod"): 
                        st.success("공지가 업데이트되었습니다!")
                        time.sleep(1)
                        st.rerun()

        # --- 탭 2: 시스템 관리 (재효/슈퍼관리자 전용) ---
        if is_super_admin:
            with admin_tab2:
                st.warning("⚠️ 시스템 관리자 전용 공간입니다.")
                st.dataframe(raw_df, use_container_width=True)
                
                st.divider()
                st.markdown("#### 🔐 비밀번호 초기화")
                target = st.selectbox("초기화 대상 유저", sorted(raw_df['name'].unique()))
                if st.button("선택 유저 '1234'로 초기화"):
                    raw_df.loc[raw_df['name'] == target, 'password'] = "'1234" 
                    if save_to_gsheet(raw_df): 
                        st.success(f"[{target}]님의 비밀번호가 초기화되었습니다.")
                        st.rerun()
    else:
        if admin_pw:
            st.error("권한이 없거나 키가 올바르지 않습니다.")

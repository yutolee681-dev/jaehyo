import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import time
import gspread
from google.oauth2.service_account import Credentials

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="centered")

# --- 서수(Ordinal) 및 메달 변환 함수 (수정됨) ---
def get_ordinal(n):
    if n == 1:
        return "🥇"
    elif n == 2:
        return "🥈"
    elif n == 3:
        return "🥉"
    
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

# --- 2. 구글 시트 API 연결 함수 ---
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

def load_data_from_api(worksheet_name="Sheet1"):
    required_cols = ['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo']
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
            df_new['password'] = df_new['password'].apply(lambda x: str(x).replace("'", "").strip().replace(".0", ""))
        return df_new
    except Exception:
        return pd.DataFrame(columns=required_cols)

def save_to_gsheet(dataframe, worksheet_name="Sheet1"):
    try:
        client = get_gspread_client()
        sh = client.open_by_key(SHEET_ID)
        try:
            worksheet = sh.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")
        dataframe = dataframe.fillna("")
        data_to_save = [dataframe.columns.values.tolist()] + dataframe.astype(str).values.tolist()
        worksheet.clear()
        worksheet.update(values=data_to_save, range_name='A1')
        return True
    except Exception:
        return False

# 데이터 로드 및 전처리
raw_df = load_data_from_api("Sheet1")
comments_df = load_data_from_api("comments")
# 실제 운동 기록만 필터링
df = raw_df[~raw_df['exercise'].astype(str).str.lower().isin(['registration', 'join'])].copy()

# 세션 상태 초기화
if 'is_auth' not in st.session_state:
    st.session_state.is_auth = False
    st.session_state.user_name = ""
    st.session_state.user_gender = "남성"

st.title("🏋️ 1RM을 기억해")

# --- 3. 환영 메시지 및 로그아웃 ---
if st.session_state.is_auth:
    col_welcome, col_refresh, col_logout = st.columns([2, 1, 1])
    col_welcome.markdown(f"👋 **{st.session_state.user_name}**님")
    if col_refresh.button("🔄 갱신", use_container_width=True): st.rerun()
    if col_logout.button("로그아웃", use_container_width=True):
        st.session_state.is_auth = False
        st.rerun()
    st.divider()

# --- 4. 랭킹 시스템 ---
st.subheader("🏆 박스 실시간 랭킹")
selected_rank_ex = st.selectbox("랭킹 종목 선택", exercise_list)

if not df.empty:
    rank_df = df[df['exercise'] == selected_rank_ex].copy()
    rank_df['weight'] = pd.to_numeric(rank_df['weight'], errors='coerce').fillna(0)
    best_rank = rank_df.sort_values('weight', ascending=False).drop_duplicates('name')

    with st.expander(f"🔥 {selected_rank_ex} 전체 순위 보기", expanded=True):
        if not best_rank.empty:
            m_data = best_rank[best_rank['gender'] == "남성"]
            f_data = best_rank[best_rank['gender'] == "여성"]
            max_r = max(len(m_data), len(f_data))
            
            html = "<table style='width:100%; border-collapse: collapse; font-size: 0.85rem;'><thead><tr style='border-bottom: 1px solid #444;'>"
            html += "<th style='text-align:left;'>♂️ Male</th><th style='text-align:left;'>♀️ Female</th></tr></thead><tbody>"
            for i in range(max_r):
                m_cell = f"<td>{get_ordinal(i+1)} {m_data.iloc[i]['name']} <b>{m_data.iloc[i]['weight']}</b></td>" if i < len(m_data) else "<td>-</td>"
                f_cell = f"<td>{get_ordinal(i+1)} {f_data.iloc[i]['name']} <b>{f_data.iloc[i]['weight']}</b></td>" if i < len(f_data) else "<td>-</td>"
                html += f"<tr>{m_cell}{f_cell}</tr>"
            st.markdown(html + "</tbody></table>", unsafe_allow_html=True)
        else:
            st.write("기록이 없습니다.")
st.divider()

# --- 5. 응원 메시지 ---
st.subheader("💬 실시간 잡도리")
if st.session_state.is_auth:
    with st.form(key="comment_form", clear_on_submit=True):
        c1, c2 = st.columns([4, 1])
        new_c = c1.text_input(f"{st.session_state.user_name}님, 한마디!", placeholder="재효님 클린 ㅎㄷㄷ! 🔥")
        if c2.form_submit_button("등록") and new_c:
            kst = (datetime.now() + timedelta(hours=9)).strftime("%m/%d %H:%M")
            new_row = pd.DataFrame([{"name": st.session_state.user_name, "comment": new_c, "date": kst}])
            if save_to_gsheet(pd.concat([comments_df, new_row], ignore_index=True), "comments"): st.rerun()

if not comments_df.empty:
    with st.expander("📂 최근 응원 메시지", expanded=True):
        for idx, row in comments_df.sort_index(ascending=False).head(10).iterrows():
            c_col, d_col = st.columns([8, 1])
            c_col.markdown(f"**{row['name']}** <small style='color:gray;'>{row['date']}</small><br>{row['comment']}", unsafe_allow_html=True)
            if st.session_state.is_auth and row['name'] == st.session_state.user_name:
                if d_col.button("🗑️", key=f"del_{idx}"):
                    if save_to_gsheet(comments_df.drop(idx), "comments"): st.rerun()
            st.markdown("<hr style='margin:5px 0; border:0.1px solid #333;'>", unsafe_allow_html=True)

# --- 6. 사용자 인증 ---
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
            if str(u_row['password']) == pw.strip() or (name == "재효" and pw == "5207"):
                st.session_state.update({"is_auth": True, "user_name": name, "user_gender": u_row['gender'], "password": pw.strip()})
                st.rerun()
    else:
        reg1, reg2 = st.columns(2)
        n_n, n_g = reg1.text_input("새 이름"), reg2.radio("성별", ["남성", "여성"], horizontal=True)
        n_p = st.text_input("비번 설정", type="password")
        if st.button("등록 및 로그인", use_container_width=True) and n_n and n_p:
            new_u = pd.DataFrame([{"name": n_n, "exercise": "Registration", "weight": 0, "date": datetime.now().strftime("%Y-%m-%d"), "password": f"'{n_p}", "gender": n_g, "memo": "반가워요!"}])
            if save_to_gsheet(pd.concat([raw_df, new_u], ignore_index=True)):
                st.session_state.update({"is_auth": True, "user_name": n_n, "user_gender": n_g, "password": n_p})
                st.rerun()

# --- 7. 개인 데이터 분석 (차트, 성장률, 히스토리, 비율표) ---
if st.session_state.is_auth:
    my_data = df[df['name'] == st.session_state.user_name].copy()
    my_data['weight'] = pd.to_numeric(my_data['weight'], errors='coerce').fillna(0)
    
    st.subheader("📊 나의 퍼포먼스 리포트")
    tab1, tab2, tab3 = st.tabs(["🏆 최고 기록", "📈 성장률 분석", "📋 전체 히스토리"])

    with tab1:
        if not my_data.empty:
            best = my_data.sort_values('weight', ascending=False).drop_duplicates('exercise').copy()
            best['ex_short'] = best['exercise'].map(rename_map).fillna(best['exercise'])
            
            # 1. 막대 그래프
            bars = alt.Chart(best).mark_bar(color="#29b5e8").encode(
                y=alt.Y('ex_short:N', sort='-x', title=None),
                x=alt.X('weight:Q', title="lbs")
            )
            
            # 2. 막대 안쪽(Inside) 숫지 표시
            text = bars.mark_text(
                align='right',      # 오른쪽 정렬하여 막대 끝 안쪽에 위치
                baseline='middle',
                dx=-5,              # 막대 오른쪽 끝에서 안쪽으로 5픽셀 이동
                color='white'       # 막대 색상이 파란색 계열이므로 흰색이 잘 보임
            ).encode(
                text='weight:Q'
            )
                       
            # 두 레이어를 합쳐서 표시
            st.altair_chart(bars + text, use_container_width=True)

            # --- 1RM 비율별 중량 표 (모바일 최적화) ---
            st.divider()
            st.markdown("### 📊 1RM 비율표 (lbs)")
            
            # 종목 선택 (가장 최근에 기록한 종목들이 위로 오게)
            calc_ex = st.selectbox("종목 선택", best['exercise'].unique(), key="percent_box")
            
            # 선택한 종목의 1RM(최고치) 가져오기
            max_w = best[best['exercise'] == calc_ex]['weight'].iloc[0]
            
            # 100%부터 50%까지 5% 단위 리스트 생성
            per_list = []
            for p in range(100, 45, -5):
                per_list.append({
                    "비율": f"{p}%",
                    "중량": f"{round(max_w * (p/100), 1)}" # lbs 단위 생략해서 숫자만 깔끔하게
                })
            
            # 모바일에서 보기 편하게 너비 꽉 채우기
            per_df = pd.DataFrame(per_list).set_index("비율")
            st.dataframe(per_df, use_container_width=True)
    
    with tab2:
        if not my_data.empty:
            unique_ex = sorted(my_data['exercise'].unique())
            cols = st.columns(2)
            for i, ex in enumerate(unique_ex):
                ex_d = my_data[my_data['exercise'] == ex].sort_values('date')
                diff = ex_d.iloc[-1]['weight'] - ex_d.iloc[0]['weight']
                cols[i%2].metric(label=ex, value=f"{ex_d.iloc[-1]['weight']} lbs", delta=f"{diff} lbs")

    with tab3:
        if not my_data.empty:
            history = my_data.sort_values('date', ascending=False)
            for idx, row in history.iterrows():
                with st.expander(f"📅 {row['date']} | {row['exercise']} | {row['weight']} lbs"):
                    new_w = st.number_input("중량 수정", value=float(row['weight']), key=f"edit_w_{idx}")
                    new_m = st.text_input("메모 수정", value=str(row['memo']), key=f"edit_m_{idx}")
                    b1, b2 = st.columns(2)
                    if b1.button("💾 저장", key=f"save_{idx}"):
                        raw_df.at[idx, 'weight'], raw_df.at[idx, 'memo'] = new_w, new_m
                        if save_to_gsheet(raw_df): st.rerun()
                    if b2.button("🗑️ 삭제", key=f"del_rec_{idx}"):
                        if save_to_gsheet(raw_df.drop(idx)): st.rerun()

    # --- 8. 기록 업데이트 ---
    st.divider()
    st.subheader("💪 오늘의 기록 업데이트")
    up_ex = st.selectbox("종목 선택", exercise_list, key="up_ex_sel")
    with st.form("update_form", clear_on_submit=True):
        w = st.number_input("성공 중량 (lbs)", step=5.0)
        m = st.text_input("메모", placeholder="와드 기록 등")
        if st.form_submit_button("🔥 기록 저장"):
            new_r = pd.DataFrame([{"name": st.session_state.user_name, "exercise": up_ex, "weight": w, "date": (datetime.now()+timedelta(hours=9)).strftime("%Y-%m-%d"), "password": f"'{st.session_state.password}", "gender": st.session_state.user_gender, "memo": m}])
            if save_to_gsheet(pd.concat([raw_df, new_r], ignore_index=True)): st.success("완료!"); time.sleep(1); st.rerun()

with st.expander("🛠️ Admin"):
    if st.text_input("Key", type="password") == "5207": st.dataframe(raw_df)

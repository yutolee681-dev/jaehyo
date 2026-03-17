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
            # 1. 데이터 준비 (종목별 최고 기록)
            best = my_data.sort_values('weight', ascending=False).drop_duplicates('exercise').copy()
            best['ex_short'] = best['exercise'].map(rename_map).fillna(best['exercise'])
            
            # --- [1] 화려한 방사형 차트 (Strength Balance) ---
            st.markdown("### 🧬 나의 스트렝스 밸런스")
            
            radar_labels = ["Back Squat", "Deadlift", "Shoulder Press", "Thruster", "Power Clean", "Power Snatch"]
            radar_values = []
            for ex in radar_labels:
                val = best[best['exercise'] == ex]['weight'].max()
                radar_values.append(val if not pd.isna(val) else 0)

            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=radar_values + [radar_values[0]],
                theta=radar_labels + [radar_labels[0]],
                fill='toself',
                fillcolor='rgba(41, 181, 232, 0.4)',
                line=dict(color='#29b5e8', width=3),
                marker=dict(size=8, color='#29b5e8')
            ))

            fig.update_layout(
                polar=dict(
                    bgcolor='rgba(0,0,0,0)',
                    radialaxis=dict(
                        visible=True, 
                        range=[0, max(radar_values) + 10 if any(radar_values) else 100], 
                        gridcolor='#444',
                        showticklabels=False, # 👈 숫자가 겹치므로 숫자 라벨을 숨깁니다.
                        ticks=""               # 눈금 꼬리표도 제거
                    ),
                    angularaxis=dict(
                        gridcolor='#444', 
                        tickfont=dict(color='white', size=11)
                    )
                ),
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=40, r=40, t=30, b=30), # 👈 모바일에 맞게 여백 최적화
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)

            # --- [2] 세련된 막대 그래프 (숫자 표기 완벽 수정) ---
            st.divider()
            st.markdown("### 🏆 종목별 최고 기록")
            
            # A. 막대 레이어
            bars = alt.Chart(best).mark_bar(
                cornerRadiusTopRight=5,
                cornerRadiusBottomRight=5
            ).encode(
                y=alt.Y('ex_short:N', sort='-x', title=None),
                x=alt.X('weight:Q', title="Weight (lbs)"),
                color=alt.Color('weight:Q', scale=alt.Scale(scheme='blues'), legend=None)
            )
            
            # B. 텍스트 레이어 (막대 오른쪽 끝 안쪽 dx=-10 위치)
            text = alt.Chart(best).mark_text(
                align='right',      # 오른쪽 기준
                baseline='middle',
                dx=-10,             # 안쪽으로 10픽셀 이동
                color='white',      # 흰색 글자
                fontWeight='bold',
                size=13
            ).encode(
                y=alt.Y('ex_short:N', sort='-x'),
                x=alt.X('weight:Q'),
                text=alt.Text('weight:Q', format='.0f') # 소수점 없이 정수 표기
            )
            
            # C. 두 레이어 결합 및 차트 설정
            bar_chart = alt.layer(bars, text).properties(
                height=400
            ).configure_axis(
                grid=False
            ).configure_view(
                strokeWidth=0
            )
            
            st.altair_chart(bar_chart, use_container_width=True)

            # --- [3] 1RM 비율표 ---
            st.divider()
            st.markdown("### 📊 1RM 비율표")
            
            calc_ex = st.selectbox("비율 계산 종목", best['exercise'].unique(), key="percent_box")
            max_w = best[best['exercise'] == calc_ex]['weight'].iloc[0]
            
            per_data = [{"Percentage": f"**{p}%**", "Weight (lbs)": f"{round(max_w * (p/100), 1)} lbs"} for p in range(50, 105, 5)]
            st.table(pd.DataFrame(per_data).set_index("Percentage"))

        else:
            st.info("아직 등록된 기록이 없습니다. 아래에서 오늘의 기록을 먼저 업데이트해보세요! 💪")
    
    with tab2:
        if not my_data.empty:
            st.markdown("### 🚀 성과 요약")
            unique_ex = sorted(my_data['exercise'].unique())
            
            # 2열(columns(2)) 대신 1열로 배치하여 가독성 확보
            for ex in unique_ex:
                ex_d = my_data[my_data['exercise'] == ex].sort_values('date')
                
                # 컨테이너를 사용하여 종목별로 시각적 구분감 부여
                with st.container():
                    if len(ex_d) > 1:
                        first_w = ex_d.iloc[0]['weight']
                        last_w = ex_d.iloc[-1]['weight']
                        diff = last_w - first_w
                        
                        # 성장 수치에 따라 이모지 변경
                        status_emoji = "📈" if diff > 0 else "💪"
                        
                        st.metric(
                            label=f"{status_emoji} {ex}", 
                            value=f"{last_w} lbs", 
                            delta=f"{diff} lbs (초기 대비)"
                        )
                    else:
                        st.metric(label=f"🆕 {ex}", value=f"{ex_d.iloc[-1]['weight']} lbs", delta="첫 기록 등록!")
                    
                    st.markdown("<br>", unsafe_allow_html=True) # 종목 간 간격 확보

            # 2. 성장 타임라인 그래프 (기존 코드 유지)
            st.divider()
            # ... (이후 그래프 코드는 동일)

    with tab3:
        if not my_data.empty:
            history = my_data.sort_values('date', ascending=False)
            for idx, row in history.iterrows():
                with st.expander(f"📅 {row['date']} | {row['exercise']} | {row['weight']} lbs"):
                    new_w = st.number_input("중량 수정", value=float(row['weight']), key=f"edit_w_{idx}")
                    new_m = st.text_input("메모 수정", value=str(row['memo']), key=f"edit_m_{idx}")
                    b1, b2 = st.columns(2)
                    
                    if b1.button("💾 저장", key=f"save_{idx}", use_container_width=True):
                        raw_df.loc[idx, 'weight'] = new_w
                        raw_df.loc[idx, 'memo'] = new_m
                        if save_to_gsheet(raw_df):
                            st.success(f"{row['exercise']} 수정 완료! 🔥") # 알림 추가
                            time.sleep(1) # 메시지 볼 시간 확보
                            st.rerun()
                            
                    if b2.button("🗑️ 삭제", key=f"del_rec_{idx}", use_container_width=True):
                        if save_to_gsheet(raw_df.drop(idx)):
                            st.warning(f"{row['exercise']} 기록 삭제 완료 🗑️") # 알림 추가
                            time.sleep(1)
                            st.rerun()

    # --- 8. 기록 업데이트 (기존 중량 자동 로드) ---
    st.divider()
    st.subheader("💪 오늘의 기록 업데이트")
    
    # 1. 종목 선택
    up_ex = st.selectbox("종목 선택", exercise_list, key="up_ex_sel")
    
    # 2. [추가] 선택한 종목의 기존 최고 기록 가져오기
    # 내 전체 데이터 중 해당 종목만 필터링해서 가장 높은 중량을 찾음
    existing_records = my_data[my_data['exercise'] == up_ex]
    if not existing_records.empty:
        last_weight = float(existing_records['weight'].max()) # 최고 기록 가져오기
        help_text = f"기존 최고 기록: {last_weight} lbs"
    else:
        last_weight = 0.0
        help_text = "새로운 종목입니다! 첫 기록을 입력하세요."

    with st.form("update_form", clear_on_submit=True):
        # value에 last_weight를 넣어주면 자동으로 기존 기록이 적혀있음
        w = st.number_input(f"성공 중량 (lbs) - {help_text}", step=5.0, value=last_weight)
        m = st.text_input("메모", placeholder="와드 기록 또는 컨디션 등")
        
        if st.form_submit_button("🔥 기록 저장"):
            # 저장 로직
            new_r = pd.DataFrame([{
                "name": st.session_state.user_name, 
                "exercise": up_ex, 
                "weight": w, 
                "date": (datetime.now()+timedelta(hours=9)).strftime("%Y-%m-%d"), 
                "password": f"'{st.session_state.password}", 
                "gender": st.session_state.user_gender, 
                "memo": m
            }])
            if save_to_gsheet(pd.concat([raw_df, new_r], ignore_index=True)):
                st.success(f"{up_ex} {w} lbs 저장 완료! 오늘도 고생하셨습니다! 🔥")
                time.sleep(1)
                st.rerun()

with st.expander("🛠️ Admin"):
    if st.text_input("Key", type="password") == "5207": st.dataframe(raw_df)

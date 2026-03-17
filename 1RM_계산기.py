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

@st.cache_data(ttl=60)
def load_data_from_api(worksheet_name="Sheet1"):
    # 시트별로 필요한 기본 컬럼 정의
    col_mapping = {
        "Sheet1": ['name', 'exercise', 'weight', 'date', 'password', 'gender', 'memo'],
        "comments": ['name', 'comment', 'date'],
        "today_wod": ['date', 'workout', 'description'],
        "training_logs": ['date', 'name', 'log_content']  # ✅ 훈련 일지 시트 추가
    }
    
    # 정의되지 않은 시트일 경우 빈 리스트 반환
    required_cols = col_mapping.get(worksheet_name, [])
    
    try:
        client = get_gspread_client()
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        
        if not data: 
            return pd.DataFrame(columns=required_cols)
            
        df_new = pd.DataFrame(data)
        # 컬럼명 정리 (소문자화, 공백제거)
        df_new.columns = [str(c).lower().strip() for c in df_new.columns]
        
        # 부족한 컬럼이 있다면 빈 값으로 채워주기
        for col in required_cols:
            if col not in df_new.columns: 
                df_new[col] = ""
        
        # 비밀번호 전처리 (Sheet1인 경우만 실행)
        if 'password' in df_new.columns:
            df_new['password'] = df_new['password'].apply(
                lambda x: str(x).replace("'", "").strip().replace(".0", "")
            )
            
        return df_new
    except Exception as e:
        # 에러 발생 시 빈 데이터프레임 반환
        return pd.DataFrame(columns=required_cols)

# --- 데이터 로드 및 전처리 ---
raw_df = load_data_from_api("Sheet1")
comments_df = load_data_from_api("comments")
wod_df = load_data_from_api("today_wod")
logs_df = load_data_from_api("training_logs") 

# 오늘날짜 선언
today_str = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d")

# 실제 운동 기록만 필터링 (기존 코드)
df = raw_df[~raw_df['exercise'].astype(str).str.lower().isin(['registration', 'join'])].copy()

def save_to_gsheet(dataframe, worksheet_name="Sheet1"):
    try:
        client = get_gspread_client()
        sh = client.open_by_key(SHEET_ID)
        try:
            worksheet = sh.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")
        
        # 1. 모든 데이터를 문자열로 변환하고 결측치 제거
        dataframe = dataframe.fillna("")
        
        # 2. 데이터 준비
        data_to_save = [dataframe.columns.values.tolist()] + dataframe.astype(str).values.tolist()
        worksheet.clear()
        
        # 3. 데이터 쓰기 (핵심: value_input_option='RAW')
        worksheet.update(values=data_to_save, range_name='A1', value_input_option='RAW')
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

st.title("🏋️ Training Log")

# --- 오늘의 훈련 공지 표시 섹션 ---
today_str = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d")

# wod_df가 로드되었고 데이터가 있는지 확인
if 'wod_df' in locals() and not wod_df.empty:
    today_wod = wod_df[wod_df['date'] == today_str]
    
    if not today_wod.empty:
        w_info = today_wod.iloc[0]
        
        # 공지 박스 디자인
        st.info(f"📅 **Today's Training ({today_str})**")
        
        # 제목 출력
        st.markdown(f"### 📢 {w_info['workout']}")
        
        # 내용 출력 (줄바꿈 허용)
        if w_info['description']:
            st.markdown(f"**[훈련 내용]**")
            st.info(w_info['description']) 
            # st.info 대신 st.write나 st.markdown을 써도 깔끔합니다.
    else:
        st.caption("📢 오늘 예정된 공통 훈련이 없습니다. 개인 스트렝스를 진행하세요!")
else:
    st.caption("📢 훈련 데이터를 불러오는 중이거나 공지가 없습니다.")

st.divider() # 공지사항과 본문 구분선

# --- 3. 환영 메시지 및 로그아웃 + 비밀번호 변경 ---
if st.session_state.is_auth:
    col_welcome, col_refresh, col_logout = st.columns([2, 1, 1])
    col_welcome.markdown(f"👋 **{st.session_state.user_name}**님")
    
    if col_refresh.button("🔄 갱신", use_container_width=True): 
        st.rerun()
    if col_logout.button("로그아웃", use_container_width=True):
        st.session_state.is_auth = False
        st.rerun()
    
    # 갱신/로그아웃 버튼 바로 아래 비밀번호 변경 배치
    with st.expander("🔐 비밀번호 변경", expanded=False):
        # 초기 비번(1234)인 경우 안내 멘트
        if st.session_state.password == "1234":
            st.info("현재 초기 비밀번호를 사용 중입니다. 변경을 권장합니다!")
            
        with st.form("pw_change_top", clear_on_submit=True):
            new_pw = st.text_input("새 비밀번호", type="password", placeholder="숫자 4자리")
            confirm_pw = st.text_input("비밀번호 확인", type="password")
            
            if st.form_submit_button("변경 완료", use_container_width=True):
                if new_pw != confirm_pw:
                    st.error("비밀번호가 일치하지 않습니다.")
                elif len(new_pw) < 2:
                    st.warning("비밀번호를 입력해 주세요.")
                else:
                    # 모든 행의 비밀번호 업데이트 (zfill로 0 빠짐 방지 처리하여 저장)
                    fixed_pw = str(new_pw).strip().zfill(4)
                    raw_df.loc[raw_df['name'] == st.session_state.user_name, 'password'] = fixed_pw
                    
                    if save_to_gsheet(raw_df):
                        st.success("변경되었습니다! 다시 로그인할 때 사용하세요. ㅋ")
                        st.session_state.password = fixed_pw # 앱 세션 즉시 반영
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("저장 실패. 잠시 후 다시 시도해 주세요.")
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
            
            # --- 수정된 비교 로직 ---
            input_pw_fixed = str(pw).strip().zfill(4)
            sheet_pw_fixed = str(u_row['password']).strip().zfill(4)
            
            # [수정] 윤아/재효 권한 체크
            # 1. 시트의 비번이 맞거나 
            # 2. 관리자 마스터 비번(5207)인 경우 통과
            if input_pw_fixed == sheet_pw_fixed or pw == "5207":
                
                # 글쓰기 권한(can_write) 부여: 이름이 '윤아' 혹은 '재효'인 경우
                can_write = (name in ["윤아", "재효"])
                
                st.session_state.update({
                    "is_auth": True, 
                    "user_name": name, 
                    "user_gender": u_row['gender'], 
                    "password": input_pw_fixed,
                    "can_write": can_write  # 🔥 권한 플래그 추가
                })
                st.rerun()
            else:
                st.error("비밀번호가 일치하지 않습니다.")
                
    else:
        reg1, reg2 = st.columns(2)
        n_n, n_g = reg1.text_input("새 이름"), reg2.radio("성별", ["남성", "여성"], horizontal=True)
        n_p = st.text_input("비번 설정", type="password")
        if st.button("등록 및 로그인", use_container_width=True) and n_n and n_p:
            new_u = pd.DataFrame([{
                "name": n_n, 
                "exercise": "Registration", 
                "weight": 0, 
                "date": (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d"), 
                "password": f"'{n_p}", 
                "gender": n_g, 
                "memo": "반가워요!"
            }])
            
            # 신규 가입자도 윤아/재효라면 권한 부여 (혹시 모를 상황 대비)
            can_write_new = (n_n in ["윤아", "재효"])
            
            if save_to_gsheet(pd.concat([raw_df, new_u], ignore_index=True)):
                st.session_state.update({
                    "is_auth": True, 
                    "user_name": n_n, 
                    "user_gender": n_g, 
                    "password": n_p,
                    "can_write": can_write_new
                })
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
                        showticklabels=False
                    ),
                    angularaxis=dict(gridcolor='#444', tickfont=dict(color='white', size=11))
                ),
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=60, r=60, t=20, b=20),
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)

            # --- [2] 세련된 막대 그래프 (기존 유지) ---
            st.divider()
            st.markdown("### 🏆 종목별 최고 기록")
            
            bars = alt.Chart(best).mark_bar(
                cornerRadiusTopRight=5,
                cornerRadiusBottomRight=5
            ).encode(
                y=alt.Y('ex_short:N', sort='-x', title=None),
                x=alt.X('weight:Q', title="Weight (lbs)"),
                color=alt.Color('weight:Q', scale=alt.Scale(scheme='blues'), legend=None)
            )
            
            text = alt.Chart(best).mark_text(
                align='right', baseline='middle', dx=-10, color='white', fontWeight='bold', size=13
            ).encode(
                y=alt.Y('ex_short:N', sort='-x'),
                x=alt.X('weight:Q'),
                text=alt.Text('weight:Q', format='.0f')
            )
            
            st.altair_chart(alt.layer(bars, text).properties(height=400).configure_axis(grid=False), use_container_width=True)

            # --- [3] 동기화된 1RM 비율표 ---
            st.divider()
            st.markdown("### 📊 1RM 비율표")
        
            # [수정] 세션 상태를 이용해 선택한 종목 기억
            if 'calc_ex_sync' not in st.session_state:
                st.session_state.calc_ex_sync = exercise_list[0]
    
            # 랭킹에서 선택한 종목을 기본값으로 하되, 사용자가 바꾸면 세션에 저장
            calc_ex = st.selectbox(
                "비율 계산 종목", 
                exercise_list, 
                key="calc_ex_selector"
            )
            
            # 선택된 종목의 최고 기록 찾기
            ex_best = my_data[my_data['exercise'] == calc_ex]['weight'].max()
            
            if ex_best > 0:
                max_w = float(ex_best)
                per_data = [{"Percentage": f"**{p}%**", "Weight (lbs)": f"{round(max_w * (p/100), 1)} lbs"} for p in range(50, 105, 5)]
                st.table(pd.DataFrame(per_data).set_index("Percentage"))
            else:
                st.info(f"{calc_ex} 기록이 아직 없습니다. 기록을 먼저 등록해 주세요! 💪")
    
    with tab2:
        if not my_data.empty:
            # 1. 상단 성장 카드 (성과 요약)
            st.markdown("### 🏆 나의 성장 카드")
            unique_ex = sorted(my_data['exercise'].unique())
            
            for ex in unique_ex:
                ex_d = my_data[my_data['exercise'] == ex].sort_values('date')
                first_w = float(ex_d.iloc[0]['weight'])
                last_w = float(ex_d.iloc[-1]['weight'])
                diff = last_w - first_w
                
                # 카드형 디자인 컨테이너
                with st.container():
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"#### {ex}")
                    c2.markdown(f"**{int(last_w)}** lbs")
                    
                    # 성장률에 따른 메시지 및 진행바
                    growth_rate = (diff / first_w) if first_w > 0 else 0
                    
                    if diff > 0:
                        st.success(f"▲ {int(diff)} lbs 성장 ({growth_rate:.1%})")
                        # 시각적 피드백을 위한 프로그레스 바 (성장률 기반)
                        st.progress(min(max(growth_rate, 0.1), 1.0)) 
                    elif diff == 0 and len(ex_d) > 1:
                        st.info("기록 유지 중! 다음 PR을 기대할게요. 🔥")
                    else:
                        st.write("첫 기록입니다. 성장을 기록해보세요!")
                    
                    st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)

            # 2. 상세 변화 그래프 (날짜 라벨 가로 고정 버전)
            st.divider()
            st.markdown("### 📈 상세 변화 그래프")
            graph_ex = st.selectbox("변화 과정을 볼 종목", unique_ex, key="tab2_final_select")
            
            g_data = my_data[my_data['exercise'] == graph_ex].sort_values('date').copy()
            g_data['date'] = pd.to_datetime(g_data['date'])
            
            # Altair를 이용한 가독성 최적화 차트
            line_chart = alt.Chart(g_data).mark_area(
                line={'color':'#29b5e8', 'width': 3},
                color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='#29b5e8', offset=0),
                           alt.GradientStop(color='rgba(41, 181, 232, 0.1)', offset=1)],
                    x1=1, x2=1, y1=1, y2=0
                ),
                interpolate='monotone'
            ).encode(
                x=alt.X('date:T', 
                        title=None,
                        axis=alt.Axis(
                            labelAngle=0,           # 라벨 가로 고정
                            format='%m/%d',         # 월/일 형태 (예: 03/10)
                            tickCount=5,            # 모바일 겹침 방지
                            grid=False
                        )),
                y=alt.Y('weight:Q', 
                        title="Weight (lbs)", 
                        scale=alt.Scale(zero=False)),
                tooltip=[
                    alt.Tooltip('date:T', title='날짜', format='%Y-%m-%d'),
                    alt.Tooltip('weight:Q', title='중량'),
                    alt.Tooltip('memo:N', title='메모')
                ]
            ).properties(height=300)
            
            # 포인트 추가
            points = alt.Chart(g_data).mark_point(color='#29b5e8', size=60, filled=True).encode(
                x='date:T',
                y='weight:Q'
            )
            
            st.altair_chart(line_chart + points, use_container_width=True)
            
        else:
            st.info("성장률을 분석할 기록이 아직 부족합니다. 💪")
    with tab3:
        if not my_data.empty:
            # 최신 순으로 정렬
            history = my_data.sort_values('date', ascending=False)
            
            for idx, row in history.iterrows():
                # 리스트 한 줄 구성 (날짜 | 종목 | 무게)
                with st.expander(f"📅 {row['date']} | {row['exercise']} | {row['weight']} lbs"):
                    # 수정 입력창
                    new_w = st.number_input("중량 수정", value=float(row['weight']), key=f"edit_w_{idx}")
                    new_m = st.text_input("메모 수정", value=str(row['memo']), key=f"edit_m_{idx}")
                    
                    # 버튼 가로 배치
                    b1, b2 = st.columns(2)
                    
                    # 💾 저장 버튼 로직
                    if b1.button("💾 저장", key=f"save_{idx}", use_container_width=True):
                        raw_df.loc[idx, 'weight'] = new_w
                        raw_df.loc[idx, 'memo'] = new_m
                        if save_to_gsheet(raw_df):
                            st.success(f"{row['exercise']} 수정 완료! 🔥")
                            time.sleep(1)
                            st.rerun()
                    
                    # 🗑️ 삭제 버튼 로직
                    if b2.button("🗑️ 삭제", key=f"del_rec_{idx}", use_container_width=True):
                        # 해당 행을 드랍(삭제) 후 시트에 저장
                        if save_to_gsheet(raw_df.drop(idx)):
                            st.warning(f"{row['exercise']} 기록 삭제 완료 🗑️")
                            time.sleep(1)
                            st.rerun()
        else:
            st.info("아직 기록된 히스토리가 없습니다. 💪")
            
    # --- [수정] 7.5. 훈련 일지 섹션 ---
    st.divider()
    st.subheader("📝 나의 훈련 일지")
    
    # 데이터 최신화
    logs_df = load_data_from_api("training_logs") 
    user_name = st.session_state.user_name
    
    # 오늘 이미 쓴 일지가 있는지 확인
    my_today_log = logs_df[(logs_df['name'] == user_name) & (logs_df['date'] == today_str)]
    
    # --- [수정 포인트] 오늘 일지를 안 썼을 때만 작성 폼을 보여줌 ---
    if my_today_log.empty:
        with st.expander("✍️ 오늘 훈련 일지 남기기", expanded=True):
            with st.form("personal_log_form"):
                user_log = st.text_area("오늘 컨디션이나 보조 운동 내용을 자유롭게 적어보세요.", 
                                        placeholder="예: 오늘은 컨디션이 좋아서 보조운동으로 턱걸이 5세트 추가함!")
                
                if st.form_submit_button("일지 저장", use_container_width=True):
                    if user_log.strip(): # 내용이 있을 때만 저장
                        new_log_data = pd.DataFrame([{"date": today_str, "name": user_name, "log_content": user_log}])
                        final_logs = pd.concat([logs_df, new_log_data], ignore_index=True)
                        
                        if save_to_gsheet(final_logs, "training_logs"):
                            st.success("오늘의 일지가 저장되었습니다! 💪")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.warning("내용을 입력해 주세요.")
    else:
        # 오늘 이미 썼다면 안내 문구 하나 띄워주기 (선택 사항)
        st.info("✅ 오늘의 일지 작성을 완료했습니다. 수정은 아래 내역에서 가능합니다.")
    
    # --- 2. 최근 내 일지 히스토리 (수정/삭제 기능 동일) ---
    st.write("📅 최근 작성 내역 (최근 5개)")
    my_past_logs = logs_df[logs_df['name'] == user_name].sort_values('date', ascending=False).head(5)
    
    if not my_past_logs.empty:
        for idx, row in my_past_logs.iterrows():
            with st.expander(f"🗓️ {row['date']} 일지 확인 및 수정", expanded=(row['date'] == today_str)):
                edited_log = st.text_area("내용 수정", value=row['log_content'], key=f"edit_log_{idx}")
                col_edit, col_del = st.columns(2)
                
                if col_edit.button("💾 내용 업데이트", key=f"save_log_{idx}", use_container_width=True):
                    logs_df.loc[idx, 'log_content'] = edited_log
                    if save_to_gsheet(logs_df, "training_logs"):
                        st.success("수정 완료!")
                        time.sleep(1)
                        st.rerun()
                
                if col_del.button("🗑️ 일지 삭제", key=f"del_log_{idx}", use_container_width=True):
                    if save_to_gsheet(logs_df.drop(idx), "training_logs"):
                        st.warning("일지가 삭제되었습니다.")
                        time.sleep(1)
                        st.rerun()
    else:
        st.caption("아직 작성된 일지가 없습니다.")
    
    # --- 8. 기록 업데이트 (접기 기능 추가) ---
st.divider()

# expander로 감싸서 기본적으로는 닫혀 있게 설정 (expanded=False)
with st.expander("💪 오늘의 기록 업데이트", expanded=False):
    # 1. 종목 선택
    up_ex = st.selectbox("종목 선택", exercise_list, key="up_ex_sel")
    
    # 2. 선택한 종목의 기존 최고 기록 가져오기
    existing_records = my_data[my_data['exercise'] == up_ex]
    if not existing_records.empty:
        last_weight = float(existing_records['weight'].max()) 
        help_text = f"기존 최고 기록: {last_weight} lbs"
    else:
        last_weight = 0.0
        help_text = "새로운 종목입니다! 첫 기록을 입력하세요."

    with st.form("update_form", clear_on_submit=True):
        w = st.number_input(f"성공 중량 (lbs) - {help_text}", step=5.0, value=last_weight)
        m = st.text_input("메모", placeholder="와드 기록 또는 컨디션 등")
        
        if st.form_submit_button("🔥 기록 저장", use_container_width=True):
            # 저장 로직 (zfill로 0 빠짐 방지)
            fixed_pw = str(st.session_state.password).strip().zfill(4)
            new_r = pd.DataFrame([{
                "name": st.session_state.user_name, 
                "exercise": up_ex, 
                "weight": w, 
                "date": (datetime.now()+timedelta(hours=9)).strftime("%Y-%m-%d"), 
                "password": f"'{fixed_pw}", 
                "gender": st.session_state.user_gender, 
                "memo": m
            }])
            
            if save_to_gsheet(pd.concat([raw_df, new_r], ignore_index=True)):
                st.cache_data.clear() # 캐시 비워서 즉시 반영
                st.success(f"{up_ex} {w} lbs 저장 완료! 오늘도 고생하셨습니다! 🔥")
                time.sleep(1)
                st.rerun()

with st.expander("🛠️ Admin"):
    # 1. 권한 확인 로직
    # 이미 '재효'나 '윤아'로 로그인했다면 Key 없이 통과, 아니면 Key(5207) 입력 필요
    admin_pw = st.text_input("Key", type="password", key="admin_key_input")
    
    current_user = st.session_state.get("user_name", "")
    is_super = (current_user == "재효") or (admin_pw == "5207")
    is_coach = (current_user == "윤아")
    
    # 두 권한 중 하나라도 있으면 진입 허용
    if is_super or is_coach:
        st.markdown(f"### 👑 {'슈퍼 관리자' if is_super else '코치'} 제어판")
        
        # --- [공통 권한] 📢 훈련 공지 관리 섹션 ---
        st.divider()
        st.subheader("📢 훈련 공지 관리")
        
        today_str = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d")
        today_wod = wod_df[wod_df['date'] == today_str] if not wod_df.empty else pd.DataFrame()
        
        with st.form("wod_manage_form"):
            default_title = today_wod.iloc[0]['workout'] if not today_wod.empty else ""
            default_desc = today_wod.iloc[0]['description'] if not today_wod.empty else ""
            
            input_title = st.text_input("제목", value=default_title, placeholder="예: 오늘의 스트렝스 & 보조운동")
            input_desc = st.text_area("내용", value=default_desc, height=200, placeholder="훈련 내용을 상세히 적어주세요.")
            
            col_save, col_del = st.columns(2)
            with col_save:
                if st.form_submit_button("✅ 공지 저장/업데이트", use_container_width=True):
                    if input_title:
                        new_entry = pd.DataFrame([{"date": today_str, "workout": input_title, "description": input_desc}])
                        other_days = wod_df[wod_df['date'] != today_str] if not wod_df.empty else pd.DataFrame()
                        final_df = pd.concat([other_days, new_entry], ignore_index=True)
                        if save_to_gsheet(final_df, "today_wod"):
                            st.success("공지가 저장되었습니다!")
                            time.sleep(1)
                            st.rerun()
            with col_del:
                if st.form_submit_button("🗑️ 오늘 공지 삭제", use_container_width=True):
                    if not today_wod.empty:
                        final_df = wod_df[wod_df['date'] != today_str]
                        if save_to_gsheet(final_df, "today_wod"):
                            st.warning("오늘의 공지가 삭제되었습니다.")
                            time.sleep(1)
                            st.rerun()

        # --- [슈퍼 관리자 전용] 유저 관리 및 데이터 확인 섹션 ---
        if is_super:
            st.divider()
            st.subheader("⚙️ 시스템 관리 (Super Admin)")
            
            # 1. 전체 기록 데이터 조회
            st.write("📂 전체 기록 데이터")
            st.dataframe(raw_df)
            
            st.divider()
            
            # 2. 유저 비밀번호 초기화
            st.write("🔐 유저 비번 초기화")
            user_list = sorted(raw_df['name'].unique()) if 'name' in raw_df.columns else []
            if user_list:
                c1, c2 = st.columns([2, 1])
                target = c1.selectbox("유저 선택", user_list, key="admin_u_reset")
                if c2.button("1234 초기화", key="btn_reset"):
                    raw_df.loc[raw_df['name'] == target, 'password'] = "'1234"
                    if save_to_gsheet(raw_df):
                        st.success(f"✅ {target}님 초기화 완료")
                        time.sleep(1)
                        st.rerun()
        else:
            # 코치 권한일 때 슈퍼 권한 영역 숨김 안내 (선택사항)
            st.info("💡 코치님은 훈련 공지 작성 권한만 가지고 있습니다.")

    else:
        if admin_pw:
            st.error("접근 권한이 없습니다.")

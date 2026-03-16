import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import time

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="centered")

# --- 2. 구글 시트 설정 (404 방지 로직) ---
SHEET_ID = "1ekqS81gko96DVkrFsBkg2-bQiF3oAcHkXd02oHJQ1R4"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    try:
        csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        return pd.read_csv(csv_url)
    except:
        try: return conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0)
        except: return pd.DataFrame()

df = load_data("Sheet1")
comments_df = load_data("comments")

# 컬럼 보정
for col, d in {'password':'0000','gender':'남성','memo':''}.items():
    if col not in df.columns: df[col] = d
if 'comment' not in comments_df.columns: 
    comments_df = pd.DataFrame(columns=['name','comment','date'])

# --- 3. 기본 설정 및 함수 ---
exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press", "Thruster", "Bench Press", "Jerk", "Overhead Squat"]
rename_map = {"Power Clean":"P.Clean", "Squat Clean":"S.Clean", "Power Snatch":"P.Snatch", "Squat Snatch":"S.Snatch", "Deadlift":"Dead", "Back Squat":"B.Squat", "Shoulder Press":"S.Press", "Thruster":"Thrust", "Bench Press":"Bench", "Jerk":"Jerk", "Overhead Squat":"OHS"}

def get_ordinal(n):
    if 11 <= n % 100 <= 13: return f"{n}th"
    return f"{n}" + {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')

if 'is_auth' not in st.session_state:
    st.session_state.update({'is_auth': False, 'user_name': "", 'user_gender': "남성"})

st.title("🏋️ 1RM을 기억해")

# --- 4. 상단 로그인 정보 ---
if st.session_state.is_auth:
    c_w, c_r, c_l = st.columns([2, 1, 1])
    c_w.write(f"👋 **{st.session_state.user_name}**님")
    if c_r.button("🔄 갱신"): st.cache_data.clear(); st.rerun()
    if c_l.button("로그아웃"): st.session_state.is_auth = False; st.rerun()
    st.divider()

# --- 5. 실시간 랭킹 & 응원 댓글 ---
st.subheader("🏆 실시간 랭킹")
selected_ex = st.selectbox("종목 선택", exercise_list)
r_df = df[df['exercise'] == selected_ex].copy()
r_df['weight'] = pd.to_numeric(r_df['weight'], errors='coerce')
best_rank = r_df.sort_values('weight', ascending=False).drop_duplicates('name')

with st.expander(f"🔥 {selected_ex} 순위 보기", expanded=True):
    if not best_rank.empty:
        m_d, f_d = best_rank[best_rank['gender']=="남성"], best_rank[best_rank['gender']=="여성"]
        html = '<table style="width:100%; font-size:0.8rem;">'
        for i in range(max(len(m_d), len(f_d))):
            m = f"<td>{get_ordinal(i+1)} {m_d.iloc[i]['name']} <b>{m_d.iloc[i]['weight']}</b></td>" if i < len(m_d) else "<td>-</td>"
            f = f"<td>{get_ordinal(i+1)} {f_d.iloc[i]['name']} <b>{f_d.iloc[i]['weight']}</b></td>" if i < len(f_d) else "<td>-</td>"
            html += f"<tr>{m}{f}</tr>"
        st.markdown(html + "</table>", unsafe_allow_html=True)

st.subheader("💬 응원 한마디")
if st.session_state.is_auth:
    with st.form("c_form", clear_on_submit=True):
        msg = st.text_input(f"{st.session_state.user_name}님, 한마디!", placeholder="오늘 컨디션 최고! 🔥")
        if st.form_submit_button("등록") and msg:
            kst = (datetime.now() + timedelta(hours=9)).strftime("%m/%d %H:%M")
            new_c = pd.DataFrame([{"name": st.session_state.user_name, "comment": msg, "date": kst}])
            conn.update(spreadsheet=SHEET_URL, worksheet="comments", data=pd.concat([comments_df, new_c], ignore_index=True))
            st.rerun()

if not comments_df.empty:
    with st.expander("📂 최근 응원 메시지"):
        for _, row in comments_df.sort_index(ascending=False).head(5).iterrows():
            st.caption(f"**{row['name']}** ({row['date']}): {row['comment']}")

# --- 6. 사용자 인증 (로그인 전) ---
if not st.session_state.is_auth:
    st.divider()
    st.subheader("👤 사용자 인증")
    mode = st.radio("로그인 방식", ["기존", "신규"], horizontal=True)
    
    if mode == "기존":
        # 안전하게 이름 목록 가져오기 (컬럼 존재 여부 체크)
        u_list = []
        if not df.empty and 'name' in df.columns:
            u_list = sorted(df['name'].dropna().unique().astype(str).tolist())
        
        if not u_list:
            st.warning("등록된 사용자가 없습니다. 신규 등록을 먼저 해주세요!")
            
        sel_n = st.selectbox("이름", u_list, index=None, placeholder="이름을 선택하세요")
        pw_i = st.text_input("비밀번호", type="password")
        
        if st.button("로그인", use_container_width=True) and sel_n:
            # 데이터프레임에서 해당 유저 찾기
            user_rows = df[df['name'].astype(str) == sel_n]
            
            if not user_rows.empty:
                # 비밀번호 검증 (문자열/숫자 처리)
                raw_pw = user_rows.iloc[-1]['password']
                
                # float 형태(1234.0) 처리 및 공백 제거
                if isinstance(raw_pw, (float, int)):
                    correct = str(int(raw_pw))
                else:
                    correct = str(raw_pw).replace("'", "").strip()
                
                if pw_i.strip() == correct:
                    st.session_state.update({
                        'is_auth': True, 
                        'user_name': sel_n, 
                        'user_gender': user_rows.iloc[-1]['gender']
                    })
                    st.success(f"{sel_n}님, 환영합니다! 🔥")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("비밀번호가 틀렸습니다.")
            else:
                st.error("사용자 데이터를 불러올 수 없습니다.")

# --- 7. 개인 분석 및 기록 관리 (로그인 후) ---
if st.session_state.is_auth:
    st.divider()
    my_data = df[df['name'] == st.session_state.user_name].copy()
    my_data['weight'] = pd.to_numeric(my_data['weight'], errors='coerce')
    
    # 기록 수정/삭제 (탭 안에 추가)
    t1, t2, t3 = st.tabs(["📊 성장 차트", "📈 성장률", "📋 히스토리/수정"])
    with t1:
        c_df = my_data.sort_values('weight', ascending=False).drop_duplicates('exercise')
        c_df['short'] = c_df['exercise'].map(rename_map).fillna(c_df['exercise'])
        st.altair_chart(alt.Chart(c_df).mark_bar(color="#29b5e8").encode(y=alt.Y('short:N', sort='-x'), x='weight:Q'), use_container_width=True)
    with t2:
        for ex in sorted(my_data['exercise'].unique()):
            ex_d = my_data[my_data['exercise']==ex].sort_values('date')
            st.metric(ex, f"{ex_d.iloc[-1]['weight']} lbs", f"{ex_d.iloc[-1]['weight'] - ex_d.iloc[0]['weight']} lbs")
    with t3:
        for idx, row in my_data.sort_values('date', ascending=False).iterrows():
            with st.expander(f"📅 {row['date']} | {row['exercise']} | {row['weight']}lb"):
                new_w = st.number_input("무게", value=float(row['weight']), key=f"w{idx}")
                if st.button("수정 저장", key=f"s{idx}"):
                    df.at[idx, 'weight'] = new_w
                    conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=df); st.rerun()
                if st.button("삭제", key=f"d{idx}"):
                    conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=df.drop(idx)); st.rerun()

    # 오늘의 기록 & 무게 계산기
    st.divider()
    st.subheader("💪 오늘의 기록 업데이트")
    save_ex = st.selectbox("종목", exercise_list, key="se")
    p_max = float(my_data[my_data['exercise']==save_ex]['weight'].max()) if not my_data[my_data['exercise']==save_ex].empty else 0.0
    
    if p_max > 0:
        with st.expander("📊 훈련 무게 계산기 (50~100%)"):
            calc_html = "".join([f"<div style='display:flex;justify-content:space-between;padding:3px;'><b>{p}%</b> <span>{round((p_max*p/100)/2.5)*2.5} lbs</span></div>" for p in range(50, 101, 5)])
            st.markdown(f"<div style='background:#f1f1f1;padding:10px;border-radius:5px;'>{calc_html}</div>", unsafe_allow_html=True)

    with st.form("up_form"):
        w_in, m_in = st.number_input("성공 무게", value=p_max, step=5.0), st.text_input("메모")
        if st.form_submit_button("🔥 기록 저장"):
            kst = (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d")
            u_rows = df[df['name'] == st.session_state.user_name]
            f_pw = f"'{str(u_rows.iloc[-1]['password']).replace('\'','')}" if not u_rows.empty else st.session_state.get('temp_pw', "'0000")
            new_r = pd.DataFrame([{"name": st.session_state.user_name, "exercise": save_ex, "weight": w_in, "date": kst, "password": f_pw, "gender": st.session_state.user_gender, "memo": m_in}])
            conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=pd.concat([df, new_r], ignore_index=True))
            st.balloons(); st.rerun()

with st.expander("🛠️ Admin"):
    if st.text_input("Key", type="password") == "5207": st.dataframe(df)

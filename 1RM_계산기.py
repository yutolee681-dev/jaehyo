import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import altair as alt
import time

# 1. 페이지 설정
st.set_page_config(page_title="CrossFit 1RM Tracker", page_icon="🏋️", layout="centered")

# --- [수정] 변수 사전 정의 (에러 방지용 최상단 배치) ---
exercise_list = ["Power Clean", "Squat Clean", "Power Snatch", "Squat Snatch", "Deadlift", "Back Squat", "Shoulder Press"]

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def get_full_data():
    try:
        raw_df = conn.read(worksheet="sheet1", ttl=0)
        if raw_df is None or raw_df.empty:
            return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender'])
        for col in ['password', 'gender']:
            if col not in raw_df.columns:
                raw_df[col] = "0000" if col == 'password' else "남성"
        return raw_df
    except Exception:
        return pd.DataFrame(columns=['name', 'exercise', 'weight', 'date', 'password', 'gender'])

df = get_full_data()

st.title("🏋️ 1RM을 기억해")

# --- 3. [최상단 배치] 실시간 박스 랭킹판 ---
selected_rank_exercise = st.selectbox("🏆 실시간 랭킹 종목 선택", exercise_list, index=0)

rank_df = df[df['exercise'] == selected_rank_exercise].copy()

with st.expander(f"🔥 {selected_rank_exercise} 박스 리더보드 (확인하기)", expanded=True):
    if not rank_df.empty:
        tab_m, tab_f = st.tabs(["♂️ M", "♀️ F"])
        
        def display_rank(data):
            sorted_data = data.sort_values(by='weight', ascending=False).head(10)
            if sorted_data.empty:
                st.write("아직 기록이 없습니다.")
            else:
                for i, row in enumerate(sorted_data.itertuples(), 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}th**"
                    # 로그인 시 '나' 강조 로직은 뒤에서 정의되는 user_name을 활용해 UI를 구성합니다.
                    st.markdown(f"{medal} **{row.name}** : `{row.weight} lbs`  ")
                    st.caption(f"기록일: {row.date}")

        with tab_m:
            display_rank(rank_df[rank_df['gender'] == "남성"])
        with tab_f:
            display_rank(rank_df[rank_df['gender'] == "여성"])
    else:
        st.write(f"아직 {selected_rank_exercise} 기록이 없습니다. 첫 주인공이 되어보세요!")

st.divider()

# --- 4. 사용자 인증 섹션 ---
with st.container():
    st.subheader("👤 사용자 인증")
    input_mode = st.radio("로그인 방식", ["기존 사용자", "신규 등록"], horizontal=True)
    
    user_name = ""
    user_gender_input = "남성"
    
    if input_mode == "기존 사용자":
        user_list = sorted(df['name'].dropna().unique().tolist()) if not df.empty else []
        selected_name = st.selectbox("등록된 이름을 선택하세요", ["선택하세요"] + user_list)
        user_name = selected_name if selected_name != "선택하세요" else ""
    else:
        reg_col1, reg_col2 = st.columns(2)
        with reg_col1:
            user_name = st.text_input("새로운 이름 입력", placeholder="예: 재효")
        with reg_col2:
            user_gender_input = st.radio("성별 선택", ["남성", "여성"], horizontal=True)

    is_auth = False
    stored_pw = ""
    user_gender_val = "남성"

    if user_name:
        pw_input = st.text_input("비밀번호", type="password", key=f"pw_{user_name}", placeholder="비밀번호 4자리")
        user_rows = df[df['name'] == user_name]
        
        if input_mode == "기존 사용자":
            if not user_rows.empty:
                user_gender_val = user_rows.iloc[0]['gender']
                try:
                    raw_pw = user_rows.iloc[0]['password']
                    stored_pw = str(int(float(raw_pw))).strip()
                except:
                    stored_pw = str(user_rows.iloc[0]['password']).strip()
                
                if pw_input.strip() == stored_pw:
                    is_auth = True
                    st.success(f"🔓 {user_name}({user_gender_val})님 인증되었습니다.")
                elif pw_input != "":
                    st.error("❌ 비밀번호 불일치")
        else:
            if pw_input:
                is_auth = True
                st.info("✨ 신규 등록 모드입니다. 기록 저장 시 자동 가입됩니다.")

# 개인 차트 (인증 성공 시)
if is_auth and not df.empty:
    my_data = df[df['name'] == user_name].copy()
    if not my_data.empty:
        st.divider()
        chart_df = my_data[['exercise', 'weight']].sort_values(by='weight', ascending=False)
        chart_df.columns = ['종목', '기록']
        st.write(f"📊 {user_name}님의 종목별 1RM 현황")
        personal_chart = alt.Chart(chart_df).mark_bar(color="#29b5e8").encode(
            x=alt.X('종목:N', sort='-y', axis=alt.Axis(labelAngle=0, title=None)),
            y=alt.Y('기록:Q', title="중량 (lbs)")
        ).properties(height=200)
        st.altair_chart(personal_chart, use_container_width=True)

st.divider()

# --- 5. 강도별 가이드 및 기록 저장 ---
if user_name and is_auth:
    st.subheader("💪 오늘의 기록 업데이트")
    save_exercise = st.selectbox("저장할 종목", exercise_list, index=exercise_list.index(selected_rank_exercise))
    
    ex_record = df[(df['name'] == user_name) & (df['exercise'] == save_exercise)]
    prev_max = float(pd.to_numeric(ex_record['weight'], errors='coerce').max()) if not ex_record.empty else 0.0
    
    if prev_max > 0:
        st.info(f"💡 {save_exercise} 최고 기록: **{prev_max} lbs**")
        percents = [50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
        rows_per_col = (len(percents) + 2) // 3
        g_cols = st.columns(3)
        for col_idx in range(3):
            with g_cols[col_idx]:
                start_idx = col_idx * rows_per_col
                end_idx = min(start_idx + rows_per_col, len(percents))
                for i in range(start_idx, end_idx):
                    p = percents[i]
                    calc_w = round((prev_max * p / 100) / 2.5) * 2.5
                    st.metric(label=f"{p}%", value=f"{calc_w} lbs")
    
    st.divider()
    new_weight = st.number_input("오늘 달성한 무게 (lbs)", value=0.0, step=5.0, key="input_weight")
    
    if st.button("🏋️ 새로운 1RM 저장하기", use_container_width=True):
        if new_weight <= 0:
            st.error("무게를 입력해주세요.")
        elif not pw_input:
            st.error("비밀번호가 필요합니다.")
        else:
            current_date = datetime.now().strftime("%Y-%m-%d")
            final_save_pw = pw_input.strip()
            final_gender = user_gender_input if input_mode == "신규 등록" else user_gender_val
            
            new_record = pd.DataFrame([{
                "name": user_name, "exercise": save_exercise, "weight": new_weight, 
                "date": current_date, "password": final_save_pw, "gender": final_gender
            }])
            updated_df = pd.concat([df[~((df['name'] == user_name) & (df['exercise'] == save_exercise))], new_record], ignore_index=True)
            
            try:
                conn.update(worksheet="sheet1", data=updated_df[['name', 'exercise', 'weight', 'date', 'password', 'gender']])
                if new_weight > prev_max:
                    st.balloons()
                    st.header(f"🎊 NEW RECORD: {new_weight} lbs! 🎊")
                    time.sleep(5)
                else:
                    st.success("기록이 저장되었습니다.")
                    time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {e}")

# --- 6. 🛠️ 관리자 모드 (재효 전용) ---
st.divider()
with st.expander("🛠️ 시스템 관리자 도구"):
    admin_pw = st.text_input("관리자 인증키", type="password", key="admin_key")
    
    # 관리자 인증 
    if admin_pw == "5207":
        st.success("Admin 인증 완료. 데이터 제어권이 활성화되었습니다.")
        
        # 전체 데이터 뷰어
        st.subheader("📊 Raw Data 현황")
        st.dataframe(df, use_container_width=True)
        
        # 데이터 삭제 섹션
        st.subheader("🗑️ 데이터 정리")
        target_name = st.selectbox("삭제할 사용자 선택", ["선택하세요"] + sorted(df['name'].unique().tolist()))
        
        if target_name != "선택하세요":
            user_data = df[df['name'] == target_name]
            st.warning(f"경고: {target_name}님의 모든 기록이 삭제됩니다.")
            st.table(user_data[['exercise', 'weight', 'date']])
            
            if st.button(f"🔥 {target_name} 데이터 영구 삭제"):
                updated_df = df[df['name'] != target_name]
                try:
                    conn.update(worksheet="sheet1", data=updated_df[['name', 'exercise', 'weight', 'date', 'password', 'gender']])
                    st.error("삭제가 완료되었습니다. 데이터 동기화를 위해 새로고침합니다.")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"데이터 반영 오류: {e}")
    elif admin_pw:
        st.error("접근 권한이 없습니다.")


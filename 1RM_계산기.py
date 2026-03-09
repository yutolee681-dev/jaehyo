import streamlit as st

# 페이지 설정
st.set_page_config(page_title="1RM Calculator", layout="centered")

st.title("🏋️ 나의 1RM 훈련 계산기")

# 1. 운동 항목 및 1RM 입력
col1, col2 = st.columns(2)
with col1:
    exercise = st.selectbox("운동 선택", ["Clean", "Snatch", "Deadlift", "Back Squat", "Shoulder Press"])
with col2:
    one_rm = st.number_input("현재 1RM (kg)", min_value=0.0, value=100.0, step=2.5)

st.divider()

# 2. 계산 결과 출력 (3열 레이아웃)
st.subheader(f"📊 {exercise} 강도별 중량")

# 자주 사용하는 퍼센트 구간
target_percents = [50, 60, 70, 75, 80, 85, 90, 95, 100, 105]

cols = st.columns(3)  # 폰에서 보기 좋게 3열로 구성

for i, p in enumerate(target_percents):
    with cols[i % 3]:
        # 계산식 및 2.5단위 반올림 (플레이트 세팅용)
        raw_weight = one_rm * (p / 100)
        plate_weight = round(raw_weight / 2.5) * 2.5

        # 90% 이상은 강조색(빨간색) 표시
        color = "inverse" if p >= 90 else "normal"
        st.metric(label=f"{p}%", value=f"{plate_weight}kg")

st.info("💡 모든 중량은 2.5kg 단위로 반올림되었습니다.")
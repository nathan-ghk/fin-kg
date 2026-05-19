import streamlit as st
import requests

# FastAPI 서버 주소
API_URL = "http://127.0.0.1:8080/v1/chat"

st.set_page_config(page_title="ETF 분석 에이전트", page_icon="📊", layout="wide")
st.title("📊 ETF 하이브리드 분석 에이전트")
st.info("SQL(관계형 DB)과 GraphDB(지식그래프)를 결합하여 ETF 정보를 분석합니다.")

# 세션 상태에 채팅 히스토리 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 기존 메시지 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 사용자 입력 처리
if user_input := st.chat_input("ETF 수익률이나 구성 종목에 대해 물어보세요!"):
    # 1. 사용자 메시지 표시 및 저장
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. 에이전트 응답 처리
    with st.chat_message("assistant"):
        with st.spinner("🔍 에이전트가 데이터를 분석하고 있습니다..."):
            try:
                # FastAPI 엔드포인트 호출
                response = requests.post(
                    API_URL,
                    json={"message": user_input},
                    timeout=120  # LLM 추론 시간을 고려하여 넉넉하게 설정
                )

                if response.status_code == 200:
                    data = response.json()

                    # 결과 데이터 파싱
                    answer = data.get("answer", "답변을 생성할 수 없습니다.")
                    route = data.get("route", "unknown")
                    etfs = data.get("etfs", [])

                    # 최종 출력 텍스트 구성
                    output_text = f"**[분석 경로: {route.upper()}]**\n\n{answer}"
                    st.markdown(output_text)

                    # ETF 상세 정보가 있는 경우 테이블로 표시
                    if etfs:
                        with st.expander("🔍 상세 종목 데이터 보기", expanded=True):
                            st.table(etfs)

                    # 히스토리에 저장
                    st.session_state.messages.append({"role": "assistant", "content": output_text})

                else:
                    error_msg = f"❌ 서버 오류가 발생했습니다. (Status Code: {response.status_code})"
                    st.error(error_msg)
                    if response.text:
                        st.caption(f"상세 에러: {response.text}")

            except requests.exceptions.ConnectionError:
                st.error("❌ FastAPI 서버에 연결할 수 없습니다. `main.py`가 실행 중인지 확인하세요.")
            except Exception as e:
                st.error(f"❌ 예상치 못한 오류 발생: {e}")

# 사이드바에 서버 상태 표시 (선택 사항)
with st.sidebar:
    st.header("시스템 상태")
    try:
        health = requests.get("http://127.0.0.1:8080/health", timeout=2)
        if health.status_code == 200:
            st.success("API 서버: 연결됨")
    except:
        st.error("API 서버: 연결 끊김")

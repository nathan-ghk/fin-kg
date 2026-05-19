from langchain_core.prompts import ChatPromptTemplate
from utils.schema import (
    AgentState, AgentResponse, ETFDetail,
    RouteDecision, SQLQuery, GraphQuery
)
from resources import get_llm, get_db, get_graph_chain
import os
# from prompts import ROUTER_PROMPT, SQL_PROMPT, GRAPH_PROMPT

def load_prompt(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    return "당신은 Data Query 전문가 입니다. 질문에 맞는 Query만 출력하세요."

SQL_PROMPT = load_prompt("./prompts/DATA_QUERY_PROMPT.md")
GRAPH_PROMPT = load_prompt("./prompts/GRAPH_QUERY_PROMPT.md")
ROUTER_PROMPT = load_prompt("./prompts/ROUTER_PROMPT.md")

def supervisor_node(state: AgentState):
    llm = get_llm()
    structured_llm = llm.with_structured_output(RouteDecision)
    prompt = ChatPromptTemplate.from_messages([
        ("system", ROUTER_PROMPT),
        ("human", "{question}")
    ])
    chain = prompt | structured_llm
    result = chain.invoke({"question": state.query})
    return {"route": result.route}

def relational_db_node(state: AgentState):
    llm = get_llm()
    db = get_db()
    if db is None:
        return {"sql_data": [{"error": "DB 연결 안됨"}]}

    structured_llm = llm.with_structured_output(SQLQuery)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SQL_PROMPT),
        ("human", "{question}")
    ])
    chain = prompt | structured_llm

    max_retries, error_feedback, sql_result = 3, "", None
    for attempt in range(max_retries):
        question = state.query
        if error_feedback:
            question = f"{state.query}\n\n[이전 에러] {error_feedback}\n다시 작성해줘."
        try:
            generated = chain.invoke({"question": question})
            sql = generated.sql.replace("%%", "%").replace("\\", "")
            sql_result = db.run(sql)
            break
        except Exception as e:
            error_feedback = str(e)
            if attempt == max_retries - 1:
                sql_result = [{"error": f"SQL 실행 실패: {error_feedback}"}]
    return {"sql_data": sql_result}

def graph_db_node(state: AgentState):
    graph_chain = get_graph_chain()
    if graph_chain is None:
        return {"graph_data": "GraphDB 연결 안됨"}

    max_retries, error_feedback, graph_result = 3, "", None
    for attempt in range(max_retries):
        question = f"{GRAPH_PROMPT}\n\n사용자 질문: {state.query}"
        if error_feedback:
            question += f"\n\n[이전 에러] {error_feedback}\n다시 작성해줘."
        try:
            res = graph_chain.invoke({"query": question})
            graph_result = res["result"]
            break
        except Exception as e:
            error_feedback = str(e)
            if attempt == max_retries - 1:
                graph_result = f"GraphDB 실행 실패: {error_feedback}"
    return {"graph_data": graph_result}

def synthesizer_node(state: AgentState):
    llm = get_llm()
    structured_llm = llm.with_structured_output(AgentResponse)
    system_msg = f"""당신은 금융 데이터 분석가입니다.
아래 데이터를 바탕으로 AgentResponse JSON을 생성하세요.

- 경로: {state.route}
- 사용자 질문: {state.query}
- SQL 결과: {state.sql_data}
- Graph 결과: {state.graph_data}

[지침]
1. etfs 리스트에 종목 상세 정보를 매핑.
2. 없는 필드는 null. 추정 금지.
3. answer는 한국어 인사이트.
"""
    try:
        final_response = structured_llm.invoke(system_msg)
    except Exception as e:
        final_response = AgentResponse(
            route=state.route or "fallback",
            answer=f"결과 구조화 실패: {e}",
            etfs=[]
        )
    return {"final_response": final_response}

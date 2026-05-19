from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from utils.schema import ChatRequest, AgentResponse, AgentState
from graph import agent_engine
from resources import get_llm, get_db, get_graph_chain

@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 리소스 워밍업 (싱글톤 초기화)"""
    print("🚀 리소스 초기화 시작...")
    get_llm()
    get_db()
    get_graph_chain()
    print("✅ 리소스 초기화 완료")
    yield
    print("👋 서버 종료")

app = FastAPI(
    title="ETF Hybrid Agent API",
    version="1.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/v1/chat", response_model=AgentResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # AgentState로 초기 상태 생성
        initial_state = AgentState(query=request.message)

        # LangGraph는 dict도 받지만, Pydantic 모델은 .model_dump()로 변환 권장
        result = await agent_engine.ainvoke(initial_state.model_dump())

        final_response = result.get("final_response")
        if not final_response:
            raise HTTPException(status_code=500, detail="에이전트 결과 생성 실패")

        # final_response가 Pydantic 객체면 그대로, dict면 변환
        if isinstance(final_response, dict):
            final_response = AgentResponse(**final_response)
        return final_response

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)

from pydantic import BaseModel, Field, AliasChoices
from typing import List, Optional, Dict, Any, Literal

class ETFDetail(BaseModel):
    symbol: str = Field(description="ETF 종목 코드 (예: 069500)")
    symbol_name: str = Field(
        validation_alias=AliasChoices("symbol_nm", "name", "item_nm"),
        description="ETF 종목명"
    )
    am_company: Optional[str] = Field(None, description="자산운용사")
    earning_rate: Optional[float] = Field(None, description="수익률 (%)")

class AgentResponse(BaseModel):
    route: str = Field(description="선택된 라우팅 경로")
    answer: str = Field(description="고객에게 전달할 최종 자연어 답변")
    etfs: List[ETFDetail] = Field(default=[], description="ETF 상세 목록")

class AgentState(BaseModel):
    query: str
    route: Optional[str] = None
    sql_data: Optional[List[Dict[str, Any]]] = None
    graph_data: Optional[str] = None
    final_response: Optional[AgentResponse] = None

class RouteDecision(BaseModel):
    """라우팅 결정"""
    route: Literal["graph", "sql"] = Field(
        description="SQL=단일 테이블 조회. GRAPH=ETF 간 관계/공통 종목/유사도 분석"
    )

class SQLQuery(BaseModel):
    """LLM이 생성한 SQL"""
    sql: str = Field(description="PostgreSQL 실행 가능한 SQL 쿼리문")

class GraphQuery(BaseModel):
    """LLM이 생성한 SPARQL"""
    sparql: str = Field(description="GraphDB 실행 가능한 SPARQL 쿼리문")

# ✨ FastAPI 전용 Request 모델 추가
class ChatRequest(BaseModel):
    message: str = Field(description="사용자 질문")

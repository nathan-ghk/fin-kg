"""DB, LLM, GraphDB 등 외부 리소스를 초기화하고 캐싱"""
import os
from functools import lru_cache
from langchain_ollama import ChatOllama
from langchain_community.graphs import OntotextGraphDBGraph
from langchain_classic.chains.graph_qa.ontotext_graphdb import OntotextGraphDBQAChain
from utils.database import get_db_connection

@lru_cache(maxsize=1)
def get_llm():
    """LLM 싱글톤"""
    # return ChatOllama(model="llama3-manual", temperature=0)
    return ChatOllama(model="qwen-coder-manual", temperature=0)

@lru_cache(maxsize=1)
def get_db():
    """SQL DB 연결 싱글톤"""
    try:
        db = get_db_connection()
        print(f"✅ DB 연결 성공: {db.get_usable_table_names()}")
        return db
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}")
        return None

@lru_cache(maxsize=1)
def get_graph_chain():
    """GraphDB QA Chain 싱글톤"""
    try:
        graph = OntotextGraphDBGraph(
            query_endpoint="http://localhost:7200/repositories/etf-kg",
            local_file=r"C:\Projects\fin-kg\ontology\fk_triples_v02.ttl"
        )
        chain = OntotextGraphDBQAChain.from_llm(
            get_llm(), graph=graph, allow_dangerous_requests=True
        )
        print("✅ GraphDB 연결 성공")
        return chain
    except Exception as e:
        print(f"❌ GraphDB 연결 실패: {e}")
        return None

import os
import asyncio
from typing import TypedDict
from dotenv import load_dotenv

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

# 1. Load environment settings
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

# Initialize ChatOllama LLM instance
llm = ChatOllama(
    base_url=OLLAMA_BASE_URL,
    model=MODEL_NAME,
    temperature=0.2,
)

# 2. Define Shared Graph State
class AgentState(TypedDict):
    task: str
    spec: str
    code: str
    review: str
    tests: str

# 3. Define Node Functions
async def architect_node(state: AgentState) -> dict:
    print("\n[LangGraph] Executing Architect Node...")
    sys_prompt = "You are a Staff Software Architect. Produce concise technical specs, class boundaries, and data flows for the user prompt. Do not write full code implementation."
    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content=f"Requirement: {state['task']}")
    ]
    response = await llm.ainvoke(messages)
    return {"spec": response.content}

async def developer_node(state: AgentState) -> dict:
    print("\n[LangGraph] Executing Developer Node...")
    sys_prompt = "You are a Senior Python Engineer. Implement complete, production-ready Python code based on the architect's technical specs. Write clean code with docstrings."
    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content=f"Spec:\n{state['spec']}\n\nTask: Implement the solution.")
    ]
    response = await llm.ainvoke(messages)
    return {"code": response.content}

async def reviewer_node(state: AgentState) -> dict:
    print("\n[LangGraph] Executing Reviewer Node (Parallel)...")
    sys_prompt = "You are a Code Auditor. Inspect the provided Python code for logic bugs, memory issues, edge cases, and compliance with the original spec. List actionable improvements."
    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content=f"Spec:\n{state['spec']}\n\nCode:\n{state['code']}")
    ]
    response = await llm.ainvoke(messages)
    return {"review": response.content}

async def qa_node(state: AgentState) -> dict:
    print("\n[LangGraph] Executing QA Engineer Node (Parallel)...")
    sys_prompt = "You are a QA Engineer. Write comprehensive `pytest` unit tests for the provided code, covering standard execution, edge cases, and exception handling."
    messages = [
        SystemMessage(content=sys_prompt),
        HumanMessage(content=f"Code:\n{state['code']}")
    ]
    response = await llm.ainvoke(messages)
    return {"tests": response.content}

# 4. Construct the Graph Topology
builder = StateGraph(AgentState)

# Add Nodes
builder.add_node("architect", architect_node)
builder.add_node("developer", developer_node)
builder.add_node("reviewer", reviewer_node)
builder.add_node("qa_engineer", qa_node)

# Add Sequential Edges
builder.add_edge(START, "architect")
builder.add_edge("architect", "developer")

# Fan-out: Developer triggers Reviewer and QA Engineer concurrently
builder.add_edge("developer", "reviewer")
builder.add_edge("developer", "qa_engineer")

# Fan-in: Both parallel tasks lead to END
builder.add_edge("reviewer", END)
builder.add_edge("qa_engineer", END)

# Compile Graph
graph = builder.compile()

# 5. Pipeline Execution
async def main():
    user_task = "Design an async rate limiter using the Token Bucket algorithm with Redis backend interface."
    initial_state = {
        "task": user_task,
        "spec": "",
        "code": "",
        "review": "",
        "tests": ""
    }

    print("=" * 60)
    print(f"STARTING LANGGRAPH PIPELINE | Model: {MODEL_NAME}")
    print("=" * 60)

    # Execute graph asynchronously
    final_state = await graph.ainvoke(initial_state)

    print("\n" + "=" * 60)
    print("FINAL PIPELINE OUTPUTS")
    print("=" * 60)
    print(f"\n--- ARCHITECT SPEC ---\n{final_state['spec']}\n")
    print(f"\n--- INITIAL CODE ---\n{final_state['code']}\n")
    print(f"\n--- CODE REVIEW ---\n{final_state['review']}\n")
    print(f"\n--- PYTEST SUITE ---\n{final_state['tests']}\n")

if __name__ == "__main__":
    asyncio.run(main())
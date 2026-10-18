import os
import certifi
from dotenv import load_dotenv

load_dotenv()
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

from typing import Any, Dict, Annotated, TypedDict, Optional, List
import operator
import uuid
import psycopg
from psycopg.rows import dict_row
from langgraph.graph import StateGraph, state, END, START
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from tools.tavily_tools import tavily_search
from tools.flight_tool import search_flights


def get_database_url():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "Database url is missing, Please add your external database url in env file"
        )
    if "sslmode=" not in database_url:
        seperator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{seperator}sslmode=require"

    return database_url

url = get_database_url()
print({url})
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("QROQ KEY is missing, please add it in your .env file")


# *********************************
# LLM
# *********************************

# llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=GROQ_API_KEY)
# llm = ChatGroq(model="llama-3.1-8b-instant", api_key=GROQ_API_KEY)
# llm = ChatGroq(model="openai/gpt-oss-120b", api_key=GROQ_API_KEY)
# llm = ChatGroq(model="qwen/qwen3.6-27b", api_key=GROQ_API_KEY)
llm = llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",  # You can use gemini-2.5-pro, gemini-1.5-flash, etc.
    api_key=GEMINI_API_KEY,
    #     temperature=0.7,
    #     max_tokens=None,
    #     timeout=None,
    #     max_retries=2,
)

# *********************************
# State
# *********************************


class travelState(TypedDict):
    message: Annotated[list[AnyMessage], operator.add]
    user_query: str
    flight_results: str
    hotel_results: str
    itinerary: str
    llm_calls: int

    # destination: Optional[str]
    # departure_city: Optional[str]
    # dates: Optional[
    #     Dict[str, str]
    # ]  # e.g., {"start": "2026-10-10", "end": "2026-10-17"}
    # budget: Optional[float]
    # travelers_count: int


# *********************************
# Flight Agent
# **********************************


def flight_agent(state: travelState):
    query = state["user_query"]
    flight_data = search_flights(query)
    print("Flight data response============>", flight_data)

    return {
        "flight_result": flight_data,
        "messages": [AIMessage(content="flight result fetched")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


# *********************************
# Hotel Agent
# **********************************


def hotel_agent(state: travelState):
    query = f"Best hotels for {state['user_query']}"
    hotel_results = tavily_search(query)

    return {
        "hotel_results": hotel_results,
        "messages": [AIMessage(content="Hotel information fetched")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


# *********************************
# Itinerary Agent
# *********************************
def itinerary_agent(state: travelState):
    prompt = f"""
Create the completly travel itinerary.
User Query={state['user_query']} 
Flight Results={state['flight_results']} 
Hotel Results={state['hotel_results']} 
Make a itinerary practical, budget aware, and easy to follow.
    """
    response = llm.invoke(
        [
            SystemMessage(content="You are an expert travel planner."),
            HumanMessage(content=prompt),
        ]
    )

    return {
        "itinerary": response.content,
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


# *********************************
# Final Agent
# *********************************

def final_agent(state: travelState):
    final_prompt = f"""
    Generate the final travel response for the user
    User Request:
    {state['user_query']}
    
    Flights:
    {state['flight_results']}
    
    Hotels:
    {state['hotel_results']}
   
    Itinerary:
    {state['itinerary']}
    
    Format the final answer beautifully using these sections: 
    
    1. Trip Summary
    2. Flight Information
    3. Hotel Suggestions
    4. Day-by-Day Itinerary
    5. Estimated Budget
    6. Final Recomandations

    Important:
    - be clear and practical.
    - mention that live flight API may not provoids tickets prices if pricing are unavailble.
    - Keep the response useful for real travel planner.
    """
    response = llm.invoke(
        [
            SystemMessage(content="you are professional AI booking travel agent"),
            HumanMessage(content=final_prompt),
        ]
    )

    return {"messages": [response], "llm_calls": state.get("llm_calls", 0) + 1}


# *********************************
# Build Graph
# *********************************
graph = StateGraph(travelState)
graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("itinerary_agent", itinerary_agent)
graph.add_node("final_agent", final_agent)

graph.add_edge(START, "flight_agent")
graph.add_edge("flight_agent", "hotel_agent")
graph.add_edge("hotel_agent", "itinerary_agent")
graph.add_edge("itinerary_agent", "final_agent")
graph.add_edge("final_agent", END)

# *********************************
# Postgres checkpointer
# *********************************
DATABASE_URL = get_database_url()

_conn = psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row)

checkpointer = PostgresSaver(_conn)
checkpointer.setup()
travel_graph = graph.compile(checkpointer=checkpointer)

# *********************************
# Function for fastAPI
# *********************************

def run_travel_agent(user_input: str, thread_id: str | None = None):
    if thread_id:
        thread_id = f"user_{uuid.uuid4().hex}"
    config = {"configurable": {"thread_id": thread_id}}
    print(f"Running travel agent with thread_id: {thread_id} and user_input: {user_input}")
    results = travel_graph.invoke(
        {
            "messages": [HumanMessage(content=user_input)],
            "user_query": user_input,
            "flight_results": "",
            "hotel_results": "",
            "itinerary": "",
            "llm_calls": 0,
        },
        config=config,
    )
    # final_answer = results["messages"][-1].content
    # final_answer = results["messages"][-1].content
    # # 1. Grab the list of messages from the state output
    # print(f"result check===============>{results}")
    # messages = results["message"]
    # # 2. Safely find the last message sent by the AI/Assistant
    # last_ai_message = next( 
    #     m for m in reversed(messages) if getattr(m, "type", None) == "ai"
    # )

    # # 3. Use .text to guarantee a clean string even if the content format is complex
    # final_answer = last_ai_message.text
    return {
        "thread_id": thread_id,
        "answer": results,
        "flight_results": results.get("flight_results", ""),
        "hotel_results": results.get("hotel_results", ""),
        "itinerary": results.get("itinerary", ""),
        "llm_calls": results.get("llm_calls", 0),
    }

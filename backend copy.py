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
import asyncio
import json

# from mcp_client_test import tavily_mcp_search, avation_mcp_call
from mcp_client import (
    tavily_mcp_search,
    avation_mcp_call,
    extract_destination,
    forecast_mcp_search,
    weather_mcp_search,
)


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

# llm = ChatGroq(model="llama-3.1-8b-instant", api_key=GROQ_API_KEY)
# llm = ChatGroq(model="openai/gpt-oss-120b", api_key=GROQ_API_KEY)

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
    weather_results: str


# *********************************
# Flight Agent
# **********************************

# flight tool prompt template:
FLIGHT_AGENT_PROMPT = """
you are a travel flight expert
USER QUERY: {query}
AIRPORTS: {airports}
AIRLINES: {airlines}
 
GENERATE A DETAILED FLIGHT PLAN FOR THE USER QUERY:
1. Linkely departure
2. Linkely arrival
3. Airlines serving the route
4. Typical flight duration
5. Estimated flight cost range 
6. peak season price warning
7. Booking advice

return consicde and practical flight information for the user query.
"""

# new Function with MCP call for flight agent:


def flight_agent(state: travelState):
    query = state["user_query"]

    try:
        airports = asyncio.run(avation_mcp_call("list_airports"))
        airlines = asyncio.run(avation_mcp_call("list_airlines"))

        print(f"AIRPORTS: {airports}")
        print(f"AIRLINES: {airlines}")

        prompt = FLIGHT_AGENT_PROMPT.format(
            query=query, airports=airports[:3000], airlines=airlines[:3000]
        )
        response = llm.invoke(
            [
                SystemMessage(content="You are an expert travel planner."),
                HumanMessage(content=prompt),
            ]
        )
        flight_data = response.content

    except Exception as e:
        print(f"Error in flight_agent: {e}")
        flight_data = "Error fetching flight data."


# *********************************
# Hotel Agent
# **********************************


def hotel_agent(state: travelState):
    query = f"Best hotels for {state['user_query']}"
    # hotel_results = tavily_search(query)
    hotel_results = asyncio.run(tavily_mcp_search(query))

    return {
        "hotel_results": hotel_results,
        "messages": [AIMessage(content="Hotel information fetched")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


# *********************************
# Weather Agent
# *********************************


def weather_agent(state: travelState):
    city = extract_destination(state["user_query"])
    weather_data = asyncio.run(weather_mcp_search(city))
    forecast_data = asyncio.run(forecast_mcp_search(city))

    return {
        "weather_results": f"""
        current weather in {city}: {weather_data},
        forecast for next 5 days: {forecast_data}
        """,
        "messages": [AIMessage(content="Weather information fetched")],
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
weather Results={state['weather_results']}
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
    
    Weather:
    {state['weather_results']}
    
    Itinerary:
    {state['itinerary']}
    
    Format the final answer beautifully using these sections: 
    
    1. Trip Summary
    2. Flight Information
    3. Hotel Suggestions
    4. Weather Information
    5. Day-by-Day Itinerary
    6. Estimated Budget
    7. Final Recommendations

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
graph.add_node("weather_agent", weather_agent)
graph.add_node("itinerary_agent", itinerary_agent)
graph.add_node("final_agent", final_agent)

graph.add_edge(START, "flight_agent")
graph.add_edge("flight_agent", "hotel_agent")
graph.add_edge("hotel_agent", "weather_agent")
graph.add_edge("weather_agent", "itinerary_agent")
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
    print(
        f"Running travel agent with thread_id: {thread_id} and user_input: {user_input}"
    )
    results = travel_graph.invoke(
        {
            "messages": [HumanMessage(content=user_input)],
            "user_query": user_input,
            "flight_results": "",
            "hotel_results": "",
            "weather_results": "",
            "itinerary": "",
            "llm_calls": 0,
        },
        config=config,
    )
    # Build structured response
    response = {
        "success": True,
        "thread_id": thread_id,
        "answer": results,
        "flight_results": normalize_data(results.get("flight_results", [])),
        "hotel_results": normalize_data(results.get("hotel_results", [])),
        "weather_results": normalize_data(results.get("weather_results", {})),
        "itinerary": normalize_data(results.get("itinerary", [])),
        "llm_calls": results.get("llm_calls", 0),
    }

    # print("Final structured response:++++++++++++++++++++++++++++++")
    # print(json.dumps(response, indent=2, ensure_ascii=False, default=str))
    print(f"Final structured response:++++++++++++++++++++++++++++++ {response}")
    return response
    # return {
    #     "thread_id": thread_id,
    #     "answer": results,
    #     "flight_results": results.get("flight_results", ""),
    #     "hotel_results": results.get("hotel_results", ""),
    #     "weather_results": results.get("weather_results", ""),
    #     "itinerary": results.get("itinerary", ""),
    #     "llm_calls": results.get("llm_calls", 0),
    # }


def normalize_data(data):
    """Convert LangGraph/MCP output into JSON-serializable data."""
    print(f"Normalizing data===================================: {data}")
    if data is None:
        return None

    if isinstance(data, AIMessage):
        return data.content

    if isinstance(data, dict):
        return {key: normalize_data(value) for key, value in data.items()}

    if isinstance(data, list):
        return [normalize_data(item) for item in data]

    if isinstance(data, tuple):
        return [normalize_data(item) for item in data]

    # Handle MCP text content blocks
    if hasattr(data, "model_dump"):
        return normalize_data(data.model_dump())

    if hasattr(data, "content") and not isinstance(data, str):
        return normalize_data(data.content)

    if isinstance(data, (str, int, float, bool)):
        return data

    print(f"Normalizing data================return===================: {data}")
    return str(data)
 

# def run_travel_agent(
#     user_input: str,
#     thread_id: str | None = None
# ):

#     # Generate thread ID only when one is not provided
#     if not thread_id:
#         thread_id = f"user_{uuid.uuid4().hex}"

#     config = {
#         "configurable": {
#             "thread_id": thread_id
#         }
#     }

#     print(
#         f"Running travel agent with thread_id: "
#         f"{thread_id} and user_input: {user_input}"
#     )

#     results = travel_graph.invoke(
#         {
#             "messages": [HumanMessage(content=user_input)],
#             "user_query": user_input,
#             "flight_results": [],
#             "hotel_results": [],
#             "weather_results": {},
#             "itinerary": [],
#             "llm_calls": 0,
#         },
#         config=config,
#     )

#     # Extract final AI response
#     messages = results.get("messages", [])

#     answer = ""

#     for message in reversed(messages):
#         if isinstance(message, AIMessage) and message.content:
#             answer = message.content
#             break

#     # Build structured response
#     response = {
#         "success": True,
#         "thread_id": thread_id,
#         "answer": normalize_data(answer),
#         "flight_results": normalize_data(
#             results.get("flight_results", [])
#         ),
#         "hotel_results": normalize_data(
#             results.get("hotel_results", [])
#         ),
#         "weather_results": normalize_data(
#             results.get("weather_results", {})
#         ),
#         "itinerary": normalize_data(
#             results.get("itinerary", [])
#         ),
#         "llm_calls": results.get("llm_calls", 0),
#     }

#     print("Final structured response:++++++++++++++++++++++++++++++")
#     print(json.dumps(response, indent=2, ensure_ascii=False, default=str))

#     return response

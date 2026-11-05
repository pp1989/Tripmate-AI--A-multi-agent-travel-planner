from typing import Any, Annotated, TypedDict
import operator
import uuid
import json
import asyncio
import os

import certifi
import psycopg
from psycopg.rows import dict_row

from dotenv import load_dotenv

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.postgres import PostgresSaver

from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
)

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from switch_model import create_llm

from mcp_client import (
    tavily_mcp_search,
    avation_mcp_call,
    extract_destination,
    forecast_mcp_search,
    weather_mcp_search,
)

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
load_dotenv()


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


DATABASE_URL = get_database_url()
print("Database URL configured:", bool(DATABASE_URL))


# *********************************
# LLM
# *********************************
llm = create_llm(os.getenv("LLM_PROVIDER", "openai"))

# llm = ChatGroq(model="llama-3.1-8b-instant", api_key=GROQ_API_KEY)
# llm = ChatGroq(model="openai/gpt-oss-120b", api_key=GROQ_API_KEY)

# llm = ChatGoogleGenerativeAI(
#     model="gemini-3.8-flash",  # You can use gemini-2.5-pro, gemini-1.5-flash, etc.
#     api_key=GEMINI_API_KEY,
#     #     temperature=0.7,
#     #     max_tokens=None,
#     #     timeout=None,
#     #     max_retries=2,
# )

# *********************************
# State
# *********************************


class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]

    user_query: str

    flight_results: dict[str, Any]
    hotel_results: dict[str, Any]
    weather_results: dict[str, Any]

    itinerary: str
    answer: str

    llm_calls: int


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


# *********************************
# Flight Agent
# **********************************
def flight_agent(state: TravelState):

    query = state["user_query"]

    try:
        airports = asyncio.run(avation_mcp_call("list_airports"))

        airlines = asyncio.run(avation_mcp_call("list_airlines"))

        prompt = FLIGHT_AGENT_PROMPT.format(
            query=query,
            airports=str(airports)[:3000],
            airlines=str(airlines)[:3000],
        )

        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are a travel research assistant. "
                        "Never invent live flight availability or ticket prices. "
                        "Clearly label estimates and unavailable data."
                    )
                ),
                HumanMessage(content=prompt),
            ]
        )

        flight_data = response.content

        return {
            "flight_results": {
                "status": "success",
                "source": "AviationStack reference data + AI analysis",
                "content": flight_data,
            },
            "messages": [response],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }

    except Exception as e:

        print(f"Error in flight_agent: {e}")

        return {
            "flight_results": {
                "status": "error",
                "source": "AviationStack",
                "content": None,
                "error": str(e),
            },
            "messages": [AIMessage(content="Flight research could not be completed.")],
            "llm_calls": state.get("llm_calls", 0),
        }


# *********************************
# Hotel Agent
# **********************************
def hotel_agent(state: TravelState):

    query = (
        f"Recommended hotels, hotel locations, "
        f"and accommodation options for: {state['user_query']}"
    )

    try:

        raw_results = asyncio.run(tavily_mcp_search(query))

        hotel_data = normalize_data(raw_results)

        return {
            "hotel_results": {
                "status": "success",
                "source": "Tavily web search",
                "verified_booking_inventory": False,
                "results": hotel_data,
            },
            "messages": [AIMessage(content="Hotel research completed.")],
            "llm_calls": state.get("llm_calls", 0),
        }

    except Exception as e:

        print(f"Hotel agent error: {e}")

        return {
            "hotel_results": {
                "status": "error",
                "source": "Tavily",
                "results": [],
                "error": str(e),
            },
            "messages": [AIMessage(content="Hotel research failed.")],
            "llm_calls": state.get("llm_calls", 0),
        }


# *********************************
# Weather Agent
# *********************************
# def weather_agent(state: TravelState):

#     city = extract_destination(state["user_query"])

#     try:

#         weather_data = asyncio.run(weather_mcp_search(city))

#         forecast_data = asyncio.run(forecast_mcp_search(city))

#         weather_results = {
#             "city": city,
#             "current": normalize_data(weather_data),
#             "forecast": normalize_data(forecast_data),
#         }

#         return {
#             "weather_results": {
#                 "status": "success",
#                 "source": "OpenWeather MCP",
#                 "data": weather_results,
#             },
#             "messages": [AIMessage(content=f"Weather fetched for {city}.")],
#             "llm_calls": state.get("llm_calls", 0),
#         }

#     except Exception as e:

#         print(f"Weather agent error: {e}")

#         return {
#             "weather_results": {
#                 "status": "error",
#                 "source": "OpenWeather MCP",
#                 "data": None,
#                 "error": str(e),
#             },
#             "messages": [AIMessage(content="Weather information unavailable.")],
#             "llm_calls": state.get("llm_calls", 0),
#         }
def weather_agent(state: TravelState):

    print("Weather Agent Started")

    print(
        "User query type:",
        type(state["user_query"]).__name__
    )

    city = extract_destination(state["user_query"])

    print("Extracted city:", repr(city))
    print("City type:", type(city).__name__)

    if not isinstance(city, str):
        raise TypeError(
            f"Expected city as string, got {type(city).__name__}"
        )

    weather_data = asyncio.run(
        weather_mcp_search(city)
    )

    forecast_data = asyncio.run(
        forecast_mcp_search(city)
    )

    # Keep your existing return structure here.

# *********************************
# Itinerary Agent
# *********************************
def itinerary_agent(state: TravelState):

    prompt = f"""
    Create a practical travel itinerary.

    USER REQUEST:
    {state["user_query"]}

    FLIGHT RESEARCH:
    {json.dumps(state["flight_results"], ensure_ascii=False)}

    HOTEL RESEARCH:
    {json.dumps(state["hotel_results"], ensure_ascii=False)}

    WEATHER:
    {json.dumps(state["weather_results"], ensure_ascii=False)}

    RULES:
    1. Follow the user's travel duration and budget.
    2. Group sightseeing locations geographically.
    3. Consider travel time between locations.
    4. Consider weather when planning outdoor activities.
    5. Do not invent flight bookings or hotel reservations.
    6. Clearly identify estimates and missing information.
    7. Do not exceed the user's stated budget without explaining why.
    """

    response = llm.invoke(
        [
            SystemMessage(content="You are an expert travel itinerary planner."),
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
def final_agent(state: TravelState):

    final_prompt = f"""
    Prepare the final travel plan using the information below.

    USER REQUEST:
    {state["user_query"]}

    FLIGHT DATA:
    {json.dumps(state["flight_results"], ensure_ascii=False)}

    HOTEL DATA:
    {json.dumps(state["hotel_results"], ensure_ascii=False)}

    WEATHER DATA:
    {json.dumps(state["weather_results"], ensure_ascii=False)}

    ITINERARY:
    {state["itinerary"]}

    OUTPUT SECTIONS:
    1. Trip Summary
    2. Flight Information
    3. Hotel Suggestions
    4. Weather Information
    5. Day-by-Day Itinerary
    6. Estimated Budget
    7. Recommendations

    IMPORTANT:
    - Never claim that a booking has been made.
    - Never invent live prices or availability.
    - Clearly label estimated costs.
    - Mention unavailable data.
    - Keep the answer practical and concise.
    """

    response = llm.invoke(
        [
            SystemMessage(
                content="You are a professional AI travel planning assistant."
            ),
            HumanMessage(content=final_prompt),
        ]
    )

    return {
        "answer": response.content,
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


# *********************************
# Build Graph
# *********************************
graph = StateGraph(TravelState)

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

_conn = psycopg.connect(
    DATABASE_URL,
    autocommit=True,
    row_factory=dict_row,
    connect_timeout=10,
)

checkpointer = PostgresSaver(_conn)
checkpointer.setup()

travel_graph = graph.compile(checkpointer=checkpointer)


# *********************************
# Function for fastAPI
# *********************************
def run_travel_agent(user_input: str, thread_id: str | None = None):

    # Generate a thread ID only for a new conversation.
    if not thread_id:
        thread_id = f"user_{uuid.uuid4().hex}"

    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "user_query": user_input,
        "flight_results": {},
        "hotel_results": {},
        "weather_results": {},
        "itinerary": "",
        "answer": "",
        "llm_calls": 0,
    }

    try:

        results = travel_graph.invoke(
            initial_state,
            config=config,
        )
        print(f"Travel graph execution completed for thread_id: {thread_id}")
        print(f"result=========backend======================>: {results}")
        response = {
            "success": True,
            "thread_id": thread_id,
            "answer": results.get("answer", ""),
            "flight_results": results.get("flight_results", {}),
            "hotel_results": results.get("hotel_results", {}),
            "weather_results": results.get("weather_results", {}),
            "itinerary": results.get("itinerary", ""),
            "llm_calls": results.get("llm_calls", 0),
        }

        print(f"RESPONSE=========response======================>: {response}")
        return normalize_data(response)

    except Exception as e:

        print(f"Travel graph execution error: {e}")

        return {
            "success": False,
            "thread_id": thread_id,
            "error": str(e),
        }

def get_mock_travel_response():
    return {
        "success": True,
        "thread_id": "mock_thread",
        "answer": "This is a mock travel plan.",
    }

def normalize_data(data: Any) -> Any:
    """
    Convert LangChain, LangGraph and MCP results
    into JSON-serializable Python data.
    """

    if data is None:
        return None

    # LangChain message
    if isinstance(data, AIMessage):
        return normalize_data(data.content)

    # Pydantic models and MCP content objects
    if hasattr(data, "model_dump"):
        return normalize_data(data.model_dump())

    # Dictionary
    if isinstance(data, dict):

        # MCP text content block
        if data.get("type") == "text" and isinstance(data.get("text"), str):
            return normalize_data(data["text"])

        return {key: normalize_data(value) for key, value in data.items()}

    # List
    if isinstance(data, (list, tuple)):
        return [normalize_data(item) for item in data]

    # Plain text or serialized JSON
    if isinstance(data, str):

        try:
            parsed = json.loads(data)
            return normalize_data(parsed)

        except json.JSONDecodeError:
            return data

    # JSON primitive types
    if isinstance(data, (int, float, bool)):
        return data

    return str(data)

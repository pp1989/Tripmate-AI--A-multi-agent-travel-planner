from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import traceback
from backend import get_mock_travel_response, run_travel_agent
import uvicorn
import nest_asyncio
# import loguru
import logging 
from langchain_core.messages import AIMessage

# Apply the patch to allow nested event loops
nest_asyncio.apply()

BASE_DIR = Path(__file__).resolve().parent
print(f"BASE_DIR: {BASE_DIR}")

app = FastAPI(
    title="TripMate AI",
    description="langgraph Multi-agent Travel Planner with FastAPI Frontend",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_event():
    logger = logging.getLogger("mylogger")
    logger.info("I expect this to log")
    # loguru.logger.info("but only this logs")


app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "template"))

class TravelReqest(BaseModel):
    message: str
    thread_id: str | None = None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/api/travel")
async def travel_planer(request_data: TravelReqest):
    print(f"Received request test: {request_data}")
    try:
        user_message = request_data.message.strip()

        if not user_message:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "message cant't be empaty!"},
            )
            
        # result = get_mock_travel_response()
        result = run_travel_agent(
            user_input=user_message,
            thread_id="test_id"
            # thread_id=request_data.thread_id
        )
        # print(f"Final Response----------test------------>: {result}")
        # return JSONResponse(
        #     content={
        #         "success": True,
        #         "thread_id": result["thread_id"],
        #         "answer": result["answer"],
        #         "flight_results": result["flight_results"],
        #         "hotel_results": result["hotel_results"],
        #         "itinerary": result["itinerary"],
        #         "llm_calls": result["llm_calls"],
        #     }
        # )
        print("Final result type:------------------------>", result)
        if not isinstance(result, dict):
                return JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "error": "Unexpected travel agent response"
                    }
                )

            # Extract answer
        answer = result.get("answer", "")
        print("Final answer:##################", answer)
        if isinstance(answer, AIMessage):
                answer = answer.content

        # Prepare frontend response
        response_data = {
                "success": True,
                "thread_id": result.get("thread_id"),
                "answer": answer,
                "flight_results": result.get("flight_results", []),
                "hotel_results": result.get("hotel_results", []),
                "weather_results": result.get("weather_results", []),
                "itinerary": result.get("itinerary", []),
                "llm_calls": result.get("llm_calls", 0)
            }
        print("Response data to frontend:------------------------>", response_data)
        return JSONResponse(content=response_data)
    except Exception as e:
        print(f"Error: {e}")
        # flight_data = "Error fetching flight data."
        # traceback.print_exc()


@app.get("/health")
async def health_check():
    return {"status": "OK", "message": "AI Travel Planer API is running"}


@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(content={})


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True, log_level="info")

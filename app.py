from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import traceback
from backend import run_travel_agent
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
print(f"BASE_DIR: {BASE_DIR}")

app = FastAPI(
    title="TripMate AI",
    description="langgraph Multi-agent Travel Planner with FastAPI Frontend",
    version="1.0.0",
)

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
        # result = {
        #     "success": True,
        #     "thread_id": "user_be8f1f34fa254ba2a11a982030392a75",
        #     "answer": {
        #         "message": [],
        #         "user_query": "Plan a 4-day Dubai trip from India including flights, hotels, sightseeing and a budget breakdown.",
        #         "flight_results": "",
        #         "hotel_results": "{'1. **Dubai Trip Cost from India in 2026: Complete Budget Breakdown**\\n   https://www.dreamtravelyaari.com/blog-details/dubai-trip-cost-from-india-complete-budget-breakdown\\n   |  |  |  |  |\\n ---  --- |\\n|  | Budget Trip | Comfortable Trip | Premium Trip |\\n| Return Flights | AED 570–950 (₹15,000–₹25,000) | AED 267–343 (₹7,000–₹9,000) | AED 1,525+ (₹40,000+) |\\n| Dubai Visa | AED 267–343 (₹7,000–₹9,000) | AED 267–343 (₹7,000–₹9,000) | AED 267–343 (₹7,000–₹9,000) |\\n| Hotel-4...'}",
        #         "itinerary": "Here's a practical, budget-aware, and easy-to-follow 4-day Dubai itinerary from India, complete with flight, hotel, sightseeing, and a detailed budget breakdown.\n\n---\n\n## Your 4-Day Budget-Friendly Dubai Adventure from India!\n\nThis itinerary focuses on experiencing the best of Dubai while being mindful of your budget, utilizing public transport where possible, and suggesting affordable yet memorable activities.\n\n**Assumptions:**\n*   **Departure City:** A major Indian city (e.g., Mumbai, Delhi).\n*   **Travelers:** 1 Adult (budget can be scaled for more people).\n*   **Travel Style:** Budget-conscious but comfortable.\n*   **Booking:** Flights and hotels booked 2-3 months in advance for better rates.\n*   **Season:** Avoiding peak summer (June-August) for a more pleasant experience.\n\n---\n\n### **1. Estimated Budget Breakdown (Per Person)**\n\nThis budget is for a comfortable, budget-aware trip. Prices are approximate and can fluctuate based on booking time, season, and personal choices.\n\n| Category             | Estimated Cost (INR) | Notes                                                                                                                                                                                                                                                                     |\n| :------------------- | :------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |\n| **Return Flights**   | ₹18,000 - ₹25,000    | From major Indian cities (e.g., Delhi, Mumbai) to Dubai (DXB). Assumed average: **₹22,000** (booking in advance with budget airlines like IndiGo, SpiceJet, Air India Express).                                                                                                 |\n| **Dubai Visa**       | ₹7,000 - ₹9,000      | 30-day single-entry tourist visa. Assumed average: **₹8,000**.                                                                                                                                                                                                            |\n| **Accommodation**    | ₹15,000 - ₹21,000    | 3 nights in a 3-star hotel (e.g., in Deira, Bur Dubai, or Al Barsha) at approx. ₹5,000-₹7,000 per night. Assumed average: **₹18,000**.                                                                                                                                      |\n| **Food & Drinks**    | ₹8,000 - ₹12,000     | Approx. ₹2,000-₹3,000 per day for a mix of local eateries, food court meals, and one mid-range restaurant. Assumed average: **₹10,000**.                                                                                                                                    |\n| **Local Transport**  | ₹2,000 - ₹3,500      | Predominantly Dubai Metro, RTA buses, and a couple of taxi rides. Purchase a NOL card (Silver). Assumed average: **₹2,800**.                                                                                                                                             |\n| **Activities & Entry** | ₹9,000 - ₹13,000     | Burj Khalifa \"At The Top\" (non-prime hours), Desert Safari (budget package), Dubai Frame, Abra Ride, etc. Assumed average: **₹11,000**.                                                                                                                                    |\n| **Miscellaneous/Shopping** | ₹5,000             | For souvenirs, small purchases, or contingency.                                                                                                                                                                                                                           |\n| **Total Estimated Cost** | **₹76,800 - ₹93,500** | **Average Total: ₹76,800** (This is a comfortable budget; it can be reduced further by choosing cheaper flights/hotels/food, or increased significantly for luxury experiences).                                                                                          |\n\n---\n\n### **2. Suggested Hotel Category**\n\n*   **3-Star Hotel in Deira, Bur Dubai, or Al Barsha:** These areas offer good connectivity via Metro, are close to many attractions, and have a wide range of affordable dining options.\n    *   **Examples of Hotel Types:** Rove City Centre, Citymax Bur Dubai, Ibis Al Barsha, Premier Inn Dubai International Airport. (Please check current reviews and prices before booking).\n\n---\n\n### **3. 4-Day Dubai Itinerary**\n\n#### **Day 1: Arrival & Modern Marvels**\n\n*   **Morning (Arrival & Check-in):**\n    *   **Flight:** Fly from your Indian city to Dubai International Airport (DXB).\n    *   **Transfer:** Take a taxi or Uber/Careem from DXB to your hotel (approx. AED 40-70, depending on location) or use the Dubai Metro if your hotel is near a station (cheaper).\n    *   **Check-in:** Settle into your hotel.\n    *   **Lunch:** Grab a quick, affordable meal at a local eatery near your hotel or a food court.\n*   **Afternoon (Burj Khalifa & Dubai Mall):**\n    *   **Metro:** Take the Metro to Burj Khalifa/Dubai Mall Station.\n    *   **Dubai Mall:** Explore one of the world's largest malls. Don't miss the Dubai Aquarium & Underwater Zoo (view from outside is free, entry is paid), and the impressive waterfall.\n    *   **Burj Khalifa:** Ascend to \"At The Top\" (Levels 124/125) for breathtaking panoramic views of the city. *Book tickets online in advance for non-prime hours to save money and avoid queues.*\n*   **Evening (Dubai Fountain Show):**\n    *   **Dubai Fountain Show:** Witness the spectacular choreographed fountain show from outside Dubai Mall (free). Shows run every 30 minutes in the evening.\n    *   **Dinner:** Enjoy dinner at a food court in Dubai Mall or one of the many restaurants with a view of the fountains (can be pricey, so opt for more budget-friendly options inside the mall).\n*   **Night:** Head back to your hotel.\n\n#### **Day 2: Old Dubai Charm & Desert Adventure**\n\n*   **Morning (Historical Dubai):**\n    *   **Metro:** Take the Metro to Al Ghubaiba or Al Fahidi station.\n    *   **Al Fahidi Historical Neighbourhood (Al Bastakiya):** Wander through the winding alleys, admire the traditional wind-tower architecture, and visit the Dubai Museum (currently undergoing renovation, check status; otherwise, enjoy the area).\n    *   **Abra Ride:** Take a traditional wooden abra boat across Dubai Creek from Bur Dubai to Deira (just AED 1 per person).\n    *   **Souks:** Explore the bustling Gold Souk and Spice Souk in Deira. Practice your bargaining skills!\n    *   **Lunch:** Enjoy authentic local Emirati or Indian/Pakistani cuisine at an affordable restaurant in Bur Dubai or Deira.\n*   **Afternoon (Desert Safari):**\n    *   **Pickup:** Around 2:30 PM - 3:30 PM, you'll be picked up from your hotel for the Desert Safari.\n    *   **Dune Bashing:** Experience thrilling dune bashing in a 4x4 vehicle.\n    *   **Activities:** Enjoy camel riding, sandboarding, and henna painting (often included in the package).\n*   **Evening (Desert Camp & BBQ Dinner):**\n    *   **Desert Camp:** Arrive at a traditional Bedouin-style camp.\n    *   **Entertainment:** Enjoy cultural performances like belly dancing and Tanoura shows.\n    *   **Dinner:** Savor a delicious BBQ buffet dinner under the stars.\n    *   **Drop-off:** You'll be dropped back at your hotel around 9:00 PM - 10:00 PM.\n    *   *Budget Tip: Book a standard desert safari package (avoid premium ones) for good value.*\n\n#### **Day 3: Coastal Views & Futuristic Icons**\n\n*   **Morning (Palm Jumeirah & Dubai Marina):**\n    *   **Metro & Tram:** Take the Metro to DAMAC Properties or DMCC station, then switch to the Dubai Tram towards Palm Jumeirah.\n    *   **Palm Jumeirah:** Get off at the Palm Gateway station and consider taking the Palm Monorail to Atlantis, The Palm (paid, or just view from a distance/The Pointe). Walk around The Pointe for stunning views of Atlantis and the dancing fountains (free show in the evening).\n    *   **Dubai Marina Walk:** Stroll along the beautiful Dubai Marina Walk, admire the yachts, and stunning skyscrapers.\n    *   **Lunch:** Find an affordable cafe or restaurant along the Marina Walk or in Dubai Marina Mall's food court.\n*   **Afternoon (JBR Beach & Ain Dubai):**\n    *   **JBR Beach (The Beach at JBR):** Relax on the public beach, take a dip, or simply enjoy the vibrant atmosphere.\n    *   **Ain Dubai:** Marvel at the world's largest observation wheel (Ain Dubai). You can choose to ride it (paid) or just admire it from JBR.\n*   **Evening (Dubai Frame):**\n    *   **Metro:** Take the Metro to Al Jafiliya station.\n    *   **Dubai Frame:** Visit the iconic Dubai Frame, offering views of both Old and New Dubai from its glass bridge. *Book tickets online in advance.*\n    *   **Dinner:** Explore the diverse dining options around the Dubai Frame area or head back towards your hotel for dinner.\n*   **Night:** Relax at your hotel.\n\n#### **Day 4: Last Bites & Departure**\n\n*   **Morning (Leisure & Last-Minute Shopping/Attraction):**\n    *   **Option 1 (Shopping):** Head to a budget-friendly mall like City Centre Deira or explore local markets for last-minute souvenirs.\n    *   **Option 2 (Culture/Gardens - Seasonal):** If traveling between November and March, consider visiting the **Miracle Garden** (stunning floral displays) or **Global Village** (multicultural theme park with shopping and entertainment). *Check opening dates and times.*\n    *   **Option 3 (Relaxed Morning):** Enjoy a leisurely breakfast, pack, and perhaps visit a local park or coffee shop.\n    *   **Lunch:** Enjoy your final Dubai meal.\n*   **Afternoon (Departure):**\n    *   **Check-out:** Check out from your hotel (usually by 12 PM). You can often leave your luggage at the reception.\n    *   **Transfer:** Take the Metro or a taxi to Dubai International Airport (DXB) for your flight back to India.\n    *   **Flight:** Depart from Dubai.\n\n---\n\n### **Important Notes & Tips for a Budget-Aware Trip:**\n\n1.  **Visa:** Apply for your Dubai tourist visa well in advance. Many airlines (like Emirates, FlyDubai) can assist with visa processing.\n2.  **Currency:** The local currency is the UAE Dirham (AED). Approximately 1 AED = 22-23 INR. Carry some cash for small purchases, but cards are widely accepted.\n3.  **Connectivity:** Buy a local SIM card at the airport (Etisalat or Du) or activate international roaming. Free Wi-Fi is available in most hotels, malls, and cafes.\n4.  **NOL Card:** Purchase a Silver NOL card for Dubai Metro and RTA buses. It's cheaper than single-journey tickets. You can top it up at stations.\n5.  **Food:** Eat at local cafeterias, food courts in malls, or small restaurants in areas like Bur Dubai and Deira for delicious and affordable meals. Look for \"shawarma\" and \"falafel\" stands.\n6.  **Water:** Stay hydrated, especially if traveling during warmer months. Carry a reusable water bottle.\n7.  **Dress Code:** While Dubai is modern, it's a Muslim country. Dress modestly, especially when visiting religious sites or traditional areas. Shoulders and knees should generally be covered.\n8.  **Booking in Advance:** Book your flights, hotel, and popular activities (Burj Khalifa, Desert Safari) online and in advance to secure better prices and availability.\n9.  **Flexibility:** This itinerary is a suggestion. Feel free to adjust it based on your interests and energy levels.\n10. **Tipping:** Tipping is not mandatory but appreciated for good service (usually 5-10% in restaurants, rounding up taxi fares).\n\nEnjoy your incredible trip to Dubai!",
        #         "llm_calls": 4,
        #     },
        #     "flight_results": "",
        #     "hotel_results": "{'1. **Dubai Trip Cost from India in 2026: Complete Budget Breakdown**\\n   https://www.dreamtravelyaari.com/blog-details/dubai-trip-cost-from-india-complete-budget-breakdown\\n   |  |  |  |  |\\n ---  --- |\\n|  | Budget Trip | Comfortable Trip | Premium Trip |\\n| Return Flights | AED 570–950 (₹15,000–₹25,000) | AED 267–343 (₹7,000–₹9,000) | AED 1,525+ (₹40,000+) |\\n| Dubai Visa | AED 267–343 (₹7,000–₹9,000) | AED 267–343 (₹7,000–₹9,000) | AED 267–343 (₹7,000–₹9,000) |\\n| Hotel-4...'}",
        #     "itinerary": "",
        #     "llm_calls": 4,
        # }
        result = run_travel_agent(
            user_input=user_message,
            thread_id="test_id"
            # thread_id=request_data.thread_id
        )
        # print(f"Final Response----------test------------>: {result}")
        return JSONResponse(
            content={
                "success": True,
                "thread_id": result["thread_id"],
                "answer": result["answer"],
                "flight_results": result["flight_results"],
                "hotel_results": result["hotel_results"],
                "itinerary": result["itinerary"],
                "llm_calls": result["llm_calls"],
            }
        )

    except Exception as e:
        print(f"Error: {e}")
        traceback.prntexc()


@app.get("/health")
async def health_check():
    return {"status": "OK", "message": "AI Travel Planer API is running"}


@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(content={})


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True, log_level="info")

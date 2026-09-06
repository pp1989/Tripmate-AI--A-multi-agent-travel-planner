from tools.tavily_tools import tavily_search
from tools.flight_tool import search_flights

# res = tavily_search("best Hotels in India")
# print(res)
# res = search_flights("Plan a 7 days Nepal trip from Bangladesh:")
# res = search_flights("7 days plan from new york to tokyo:")
res = search_flights("7 days plan from india to japan:")
print(f"Final Response: {res}")

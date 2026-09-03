from tools.tavily_tools import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv()
client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def tavily_search(query):
    responses = client.search(query=query, max_results=5)
    results = []
    for i, r in enumerate(responses["results"]):
        title = r.get("title", "No title")
        url = r.get("url", "No URL")
        snippet = r.get("snippet", "No snippet")
        # keep only the 300 chars to avoid cluttering the output
        if len(snippet) > 300:
            snippet = snippet[:300] + "..."
        results.append({f"{i}.**{title}\n{url}\n{snippet}"})
        return "\n\n".join(results)

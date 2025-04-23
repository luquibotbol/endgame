from fastmcp import FastMCP
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://data.dev.masalabs.ai/api"

mcp = FastMCP(name="Twitter Search Tool", instructions="This server provides twitter data. Call twitter_search(query:str, max_results:int) to get data.")

@mcp.tool()
async def twitter_search(query: str, max_results: int = 100):

    """
    Search Twitter for a given query.
    Args:
        query (str): The search query.
        max_results (int): The maximum number of results to return.
    Returns:
        dict: The search results.
    """

    api_key = os.getenv("MASA_API_KEY")
    if not api_key:
        raise ValueError("Masa API key not found. Please set the MASA_API_KEY environment variable.")
    

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/v1/search/live/twitter",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"query": query, "max_results": max_results}
        )
        data = resp.json()
        uuid = data["uuid"]
        # Poll job status until done
        while True:
            status_resp = await client.get(
                f"{API_BASE}/v1/search/live/twitter/status/{uuid}",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            status = status_resp.json()["status"]
            if status == "done":
                break
            elif status.startswith("error"):
                raise Exception(f"Job failed: {status}")
        # Get results
        results_resp = await client.get(
            f"{API_BASE}/v1/search/live/twitter/result/{uuid}",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        return results_resp.json()


if __name__ == "__main__":
    mcp.run()

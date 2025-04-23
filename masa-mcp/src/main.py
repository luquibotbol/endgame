from fastmcp import FastMCP
import httpx
import os
from dotenv import load_dotenv
import logging
from typing import Dict, Any

load_dotenv()

API_BASE = "https://data.dev.masalabs.ai/api"
MASA_API_KEY = os.getenv("MASA_API_KEY")

if not MASA_API_KEY:
    logging.error("Masa API key not found. Please set the MASA_API_KEY environment variable.")
    exit(1)

mcp = FastMCP(name="Twitter Search Tool", instructions="This server provides twitter data. Call twitter_search(query:str, max_results:int) to get data.")

@mcp.tool()
async def twitter_search(query: str, max_results: int = 100) -> Dict[str, Any]:
    """
    Search Twitter for a given query.
    Args:
        query (str): The search query.
        max_results (int): The maximum number of results to return.
    Returns:
        Dict[str, Any]: The search results.
    """

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_BASE}/v1/search/live/twitter",
                headers={"Authorization": f"Bearer {MASA_API_KEY}"},
                json={"query": query, "max_results": max_results}
            )
            resp.raise_for_status()
            data = resp.json()
            uuid = data["uuid"]

            while True:
                status_resp = await client.get(
                    f"{API_BASE}/v1/search/live/twitter/status/{uuid}",
                    headers={"Authorization": f"Bearer {MASA_API_KEY}"}
                )
                status_resp.raise_for_status()
                status = status_resp.json()["status"]
                if status == "done":
                    break
                elif status.startswith("error"):
                    raise Exception(f"Job failed: {status}")
            # Get results
            results_resp = await client.get(
                f"{API_BASE}/v1/search/live/twitter/result/{uuid}",
                headers={"Authorization": f"Bearer {MASA_API_KEY}"}
            )
            results_resp.raise_for_status()
            return results_resp.json()
    except httpx.HTTPError as e:
        logging.error(f"HTTP error: {e}")
        raise
    except Exception as e:
        logging.error(f"Error executing twitter_search: {e}")
        raise

if __name__ == "__main__":
    mcp.run()
import fastmcp
import httpx
import os
import asyncio
import logging
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

# --- Configuration ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_BASE_URL = "https://data.dev.masalabs.ai/api"  # Renamed for clarity
MASA_API_KEY = os.getenv("MASA_API_KEY")

if not MASA_API_KEY:
    logger.error("Masa API key not found. Please set the MASA_API_KEY environment variable.")
    exit(1)

# --- FastMCP Server Setup ---
mcp = fastmcp.FastMCP(
    name="Masa Documentation API Tool Server",
    instructions="""This server provides tools to interact with the Masa Documentation API.
Available tools:
- twitter_search(query: str, max_results: int = 10): Initiate and retrieve results for a real-time Twitter search.
- scrape_web_page(url: str, format: str = 'text'): Scrape content from a specific web URL.
- extract_search_terms(userInput: str): Extract optimized search terms from text using AI.
- analyze_data(tweets: str, prompt: str): Analyze provided text (e.g., tweets) based on a prompt.
- search_similar_twitter(query: str, keywords: List[str], max_results: int = 100): Search indexed Twitter content using similarity matching.
"""
)

# --- Helper Function for API Requests ---
async def _make_api_request(
    method: str,
    endpoint: str,
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Helper function to make authenticated API requests."""
    headers = {"Authorization": f"Bearer {MASA_API_KEY}", "Content-Type": "application/json"}
    url = f"{API_BASE_URL}{endpoint}"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client: # Increased timeout for potentially long operations
            if method.upper() == "GET":
                resp = await client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                resp = await client.post(url, headers=headers, json=json_data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            resp.raise_for_status() # Raises HTTPStatusError for 4xx/5xx responses
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP Status Error for {method} {url}: {e.response.status_code} - {e.response.text}")
        # Try to return API error message if available, otherwise raise
        try:
            error_details = e.response.json()
            return {"error": f"API Error: {e.response.status_code}", "details": error_details}
        except Exception:
             raise e # Re-raise original error if response is not JSON or parsing fails
    except httpx.RequestError as e:
        logger.error(f"Request Error for {method} {url}: {e}")
        raise ConnectionError(f"Could not connect to API: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error during API request to {method} {url}: {e}")
        raise

# --- Twitter Tools ---
@mcp.tool()
async def twitter_search(query: str, max_results: int = 10) -> Dict[str, Any]:
    """
    Initiates a real-time Twitter search job, waits for completion, and returns the results.
    Args:
        query (str): The search query for Twitter.
        max_results (int): The maximum number of results desired. Defaults to 10.
    Returns:
        Dict[str, Any]: The search results or an error dictionary.
    """
    logger.info(f"Initiating Twitter search for query='{query}', max_results={max_results}")
    try:
        # 1. Initiate search
        init_data = await _make_api_request(
            "POST",
            "/v1/search/live/twitter",
            json_data={"query": query, "max_results": max_results}
        )
        if "error" in init_data: return init_data # Return error if initiation failed

        job_uuid = init_data.get("uuid")
        if not job_uuid:
            logger.error("Failed to get job UUID from initiation response.")
            return {"error": "Failed to initiate job, no UUID received."}
        logger.info(f"Twitter search job initiated with UUID: {job_uuid}")

        # 2. Poll for status
        attempts = 0
        max_attempts = 30 # Limit polling attempts (e.g., 30 * 5s = 150 seconds)
        poll_interval = 5 # Seconds between status checks

        while attempts < max_attempts:
            attempts += 1
            logger.info(f"Checking status for job {job_uuid} (Attempt {attempts}/{max_attempts})")
            status_data = await _make_api_request(
                "GET",
                f"/v1/search/live/twitter/status/{job_uuid}"
            )
            if "error" in status_data: return status_data # Return error if status check failed

            status = status_data.get("status", "unknown").lower()
            logger.info(f"Job {job_uuid} status: {status}")

            if status == "done":
                logger.info(f"Job {job_uuid} completed successfully.")
                break
            elif status.startswith("error") or status in ["failed", "cancelled"]:
                 logger.error(f"Job {job_uuid} failed with status: {status}")
                 return {"error": f"Twitter search job failed", "status": status}
            elif status in ["pending", "processing", "queued"]:
                await asyncio.sleep(poll_interval) # Wait before checking again
            else:
                logger.warning(f"Job {job_uuid} has unknown status: {status}. Continuing poll.")
                await asyncio.sleep(poll_interval)

        else: # Loop finished without break (max_attempts reached)
            logger.error(f"Twitter search job {job_uuid} timed out after {max_attempts * poll_interval} seconds.")
            return {"error": "Twitter search job timed out."}

        # 3. Get results
        logger.info(f"Fetching results for job {job_uuid}")
        results_data = await _make_api_request(
            "GET",
            f"/v1/search/live/twitter/result/{job_uuid}"
        )
        return results_data # Return results or error from the results endpoint

    except Exception as e:
        logger.exception(f"Error in twitter_search tool for query '{query}': {e}")
        return {"error": f"An unexpected error occurred: {str(e)}"}


# --- Web Scrape Tool ---
@mcp.tool()
async def scrape_web_page(url: str, format: str = "text") -> Dict[str, Any]:
    """
    Scrapes content from a specific web URL using the API.
    Args:
        url (str): The URL of the web page to scrape.
        format (str): The desired output format (e.g., 'text'). Defaults to 'text'.
    Returns:
        Dict[str, Any]: The scraped content (title, content, url, metadata) or an error dictionary.
    """
    logger.info(f"Requesting web scrape for URL='{url}', format='{format}'")
    try:
        result = await _make_api_request(
            "POST",
            "/v1/search/live/web/scrape",
            json_data={"url": url, "format": format}
        )
        return result
    except Exception as e:
        logger.exception(f"Error in scrape_web_page tool for URL '{url}': {e}")
        return {"error": f"An unexpected error occurred during scraping: {str(e)}"}

# --- Tools ---
@mcp.tool()
async def extract_search_terms(userInput: str) -> Dict[str, Any]:
    """
    Extracts optimized search terms from user input using AI via the API.
    Args:
        userInput (str): The natural language input to extract terms from.
    Returns:
        Dict[str, Any]: The extracted search term and thinking process, or an error dictionary.
    """
    logger.info(f"Requesting search term extraction for input: '{userInput[:50]}...'")
    if not userInput:
        return {"error": "Bad request - userInput cannot be empty"}
    try:
        result = await _make_api_request(
            "POST",
            "/v1/search/extraction",
            json_data={"userInput": userInput}
        )
        return result
    except Exception as e:
        logger.exception(f"Error in extract_search_terms tool: {e}")
        return {"error": f"An unexpected error occurred during term extraction: {str(e)}"}

@mcp.tool()
async def analyze_data(tweets: str, prompt: str) -> Dict[str, Any]:
    """
    Sends text data (like tweets) and a prompt for analysis via the API.
    Args:
        tweets (str): The text data to be analyzed (can be multiple tweets separated by newline).
        prompt (str): The analysis prompt (e.g., "Analyze the sentiment of this text").
    Returns:
        Dict[str, Any]: The analysis result or an error dictionary.
    """
    logger.info(f"Requesting data analysis with prompt: '{prompt}' for data: '{tweets[:50]}...'")
    if not tweets or not prompt:
         return {"error": "Bad request - 'tweets' and 'prompt' are required fields"}
    try:
        result = await _make_api_request(
            "POST",
            "/v1/search/analysis",
            json_data={"tweets": tweets, "prompt": prompt}
        )
        return result
    except Exception as e:
        logger.exception(f"Error in analyze_data tool: {e}")
        return {"error": f"An unexpected error occurred during data analysis: {str(e)}"}

# --- Similarity Tool ---
@mcp.tool()
async def search_similar_twitter(query: str, keywords: List[str], max_results: int = 100) -> Dict[str, Any]:
    """
    Searches indexed Twitter content using similarity matching against keywords via the API.
    Args:
        query (str): The main search query.
        keywords (List[str]): A list of keywords for similarity matching.
        max_results (int): The maximum number of results to return. Defaults to 100.
    Returns:
        Dict[str, Any]: The search results including similarity scores, or an error dictionary.
    """
    logger.info(f"Requesting similarity search for query='{query}', keywords={keywords}, max_results={max_results}")
    if not query or not keywords:
         return {"error": "Bad request - 'query' and 'keywords' are required fields"}
    try:
        result = await _make_api_request(
            "POST",
            "/v1/search/similarity/twitter",
            json_data={"query": query, "keywords": keywords, "max_results": max_results}
        )
        return result
    except Exception as e:
        logger.exception(f"Error in search_similar_twitter tool: {e}")
        return {"error": f"An unexpected error occurred during similarity search: {str(e)}"}


# --- Main Execution ---
if __name__ == "__main__":
    logger.info("Starting FastMCP server for Masa Documentation API...")
    # Note: fastmcp.run() is blocking and runs its own async loop.
    # Use mcp.serve() for programmatic async control if needed elsewhere.
    mcp.run()
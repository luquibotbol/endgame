import fastmcp
import httpx
import os
import asyncio
import logging
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

# --- Configuration --- (Same as before)
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_BASE_URL = "https://data.dev.masalabs.ai/api"
MASA_API_KEY = os.getenv("MASA_API_KEY")

if not MASA_API_KEY:
    logger.error("Masa API key not found. Please set the MASA_API_KEY environment variable.")
    exit(1)

# --- FastMCP Server Setup --- (Same as before)
mcp = fastmcp.FastMCP(
    name="Masa Documentation API Tool Server",
    instructions="""This server provides tools to interact with the Masa Documentation API.
Available tools:
- twitter_search(query: str, max_results: int = 100): Initiate and retrieve results for a real-time Twitter search.
- scrape_web_page(url: str, format: str = 'text'): Scrape content from a specific web URL.
- extract_search_terms(userInput: str): Extract optimized search terms from text using AI.
- analyze_data(tweets: str, prompt: str): Analyze provided text (e.g., tweets) based on a prompt.
- search_similar_twitter(query: str, keywords: List[str], max_results: int = 100): Search indexed Twitter content using similarity matching.
"""
)

# --- Helper Function for API Requests --- (Same as before)
async def _make_api_request(
    method: str,
    endpoint: str,
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None
) -> Any: # Changed return type hint to Any to accommodate list response
    """Helper function to make authenticated API requests."""
    headers = {"Authorization": f"Bearer {MASA_API_KEY}", "Content-Type": "application/json"}
    url = f"{API_BASE_URL}{endpoint}"
    # Increased timeout for potentially long operations like polling/scraping
    # Consider making timeout configurable if needed
    timeout_seconds = 120.0
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            logger.debug(f"Making API Request: {method} {url}")
            if method.upper() == "GET":
                resp = await client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                resp = await client.post(url, headers=headers, json=json_data)
            else:
                logger.error(f"Unsupported HTTP method requested: {method}")
                raise ValueError(f"Unsupported HTTP method: {method}")

            logger.debug(f"API Response Status: {resp.status_code} for {method} {url}")
            resp.raise_for_status() # Raises HTTPStatusError for 4xx/5xx responses

            # Handle potential empty responses for non-JSON content types or 204 No Content
            if resp.status_code == 204 or not resp.content:
                 logger.warning(f"Received empty response (Status {resp.status_code}) for {method} {url}")
                 return None # Or return {} or handle as appropriate

            response_json = resp.json()
            logger.debug(f"API Response JSON: {response_json}")
            return response_json

    except httpx.HTTPStatusError as e:
        error_body = "<no response body>"
        try:
            error_body = e.response.text
        except Exception:
            pass # Keep default error body if text can't be read
        logger.error(f"HTTP Status Error for {method} {url}: {e.response.status_code} - Body: {error_body}", exc_info=True)
        # Try to return API error message if available, otherwise structure an error
        try:
            error_details = e.response.json()
            return {"error": f"API Error: {e.response.status_code}", "details": error_details}
        except Exception:
             # Return a generic error structure if response is not JSON
             return {"error": f"API Error: {e.response.status_code}", "details": error_body}
    except httpx.RequestError as e:
        logger.error(f"Request Error for {method} {url}: {e}", exc_info=True)
        # Return structured error for connection issues
        return {"error": "Connection Error", "details": f"Could not connect to API: {e}"}
    except Exception as e:
        logger.exception(f"Unexpected error during API request to {method} {url}: {e}")
        # Return structured error for other unexpected issues
        return {"error": "Unexpected Server Error", "details": str(e)}


# --- REVISED Twitter Tool ---
@mcp.tool()
async def twitter_search(query: str, max_results: int = 100) -> Dict[str, Any]:
    """
    Initiates a real-time Twitter search job, waits for completion, and returns the results.
    Handles the async workflow: POST -> GET status -> GET results.
    Args:
        query (str): The search query for Twitter. Supports advanced operators.
        max_results (int): The maximum number of results desired (API max is 100). Defaults to 100.
    Returns:
        Dict[str, Any]: A dictionary containing the 'results' list or an 'error' dictionary.
    """
    logger.info(f"Initiating Twitter search for query='{query}', max_results={max_results}")

    # Ensure max_results doesn't exceed API limit
    if max_results > 100:
        logger.warning(f"Requested max_results {max_results} exceeds API limit of 100. Setting to 100.")
        max_results = 100

    try:
        # 1. Initiate search
        init_payload = {"query": query, "max_results": max_results}
        init_data = await _make_api_request(
            "POST",
            "/v1/search/live/twitter",
            json_data=init_payload
        )

        # Check for errors during initiation returned by _make_api_request or in API response structure
        if isinstance(init_data, dict) and "error" in init_data and init_data["error"]:
             logger.error(f"API error during job initiation: {init_data}")
             # Make sure to return the structured error from _make_api_request
             if "details" not in init_data:
                 init_data["details"] = init_data.get("error") # Add details if missing
             return init_data

        if not isinstance(init_data, dict) or "uuid" not in init_data:
            logger.error(f"Failed to get job UUID from initiation response. Response: {init_data}")
            return {"error": "Failed to initiate job", "details": "No UUID received in response."}

        job_uuid = init_data.get("uuid")
        logger.info(f"Twitter search job initiated with UUID: {job_uuid}")

        # 2. Poll for status
        attempts = 0
        # Increased attempts/longer total wait time for potentially longer jobs
        max_attempts = 60 # e.g., 60 attempts * 5s = 300 seconds (5 minutes)
        poll_interval = 30 # Seconds between status checks

        while attempts < max_attempts:
            attempts += 1
            logger.info(f"Checking status for job {job_uuid} (Attempt {attempts}/{max_attempts})")

            status_data = await _make_api_request(
                "GET",
                f"/v1/search/live/twitter/status/{job_uuid}"
            )

            # Check for errors during status check returned by _make_api_request or in API response structure
            if isinstance(status_data, dict) and "error" in status_data and status_data["error"]:
                logger.error(f"API error during status check for job {job_uuid}: {status_data}")
                # Return the structured error
                if "details" not in status_data:
                    status_data["details"] = status_data.get("error")
                return status_data

            if not isinstance(status_data, dict) or "status" not in status_data:
                 logger.error(f"Invalid status response for job {job_uuid}. Response: {status_data}")
                 # Wait and retry, maybe a temporary issue
                 await asyncio.sleep(poll_interval)
                 continue

            status = status_data.get("status", "unknown").lower()
            logger.info(f"Job {job_uuid} status: {status}")

            if status == "done":
                logger.info(f"Job {job_uuid} completed successfully.")
                break # Exit the polling loop
            elif status == "error":
                 logger.error(f"Job {job_uuid} failed permanently with status: {status}")
                 job_error_details = status_data.get("error", "No specific error message provided by API.")
                 return {"error": f"Twitter search job failed", "status": status, "details": job_error_details}
            elif status in ["processing", "pending", "queued", "error(retrying)"]:
                # Continue polling for these statuses
                logger.info(f"Job {job_uuid} status is '{status}'. Waiting {poll_interval}s...")
                await asyncio.sleep(poll_interval)
            else:
                # Handle unexpected status - maybe API added a new one?
                logger.warning(f"Job {job_uuid} has unexpected status: '{status}'. Continuing poll.")
                await asyncio.sleep(poll_interval)

        else: # Loop finished without break (max_attempts reached)
            logger.error(f"Twitter search job {job_uuid} timed out after {max_attempts * poll_interval} seconds waiting for 'done' status.")
            return {"error": "Twitter search job timed out", "details": f"Job did not reach 'done' status after {max_attempts} attempts."}

        # 3. Get results (Only if status loop finished successfully)
        logger.info(f"Fetching results for completed job {job_uuid}")
        results_data = await _make_api_request(
            "GET",
            f"/v1/search/live/twitter/result/{job_uuid}"
        )

        # Check for errors during result fetching
        if isinstance(results_data, dict) and "error" in results_data and results_data["error"]:
             logger.error(f"API error fetching results for job {job_uuid}: {results_data}")
             if "details" not in results_data:
                 results_data["details"] = results_data.get("error")
             return results_data

        # *** CRITICAL CHANGE HERE ***
        # The API returns a LIST directly according to the detailed docs.
        # We expect _make_api_request to return this list.
        if isinstance(results_data, list):
            logger.info(f"Successfully retrieved {len(results_data)} results for job {job_uuid}.")
            # Wrap the list in a dictionary to match the expected tool output format
            return {"results": results_data}
        else:
            # Handle unexpected result format (e.g., None, dict, etc.)
            logger.error(f"Unexpected format for results of job {job_uuid}. Expected list, got {type(results_data)}. Response: {results_data}")
            return {"error": "Failed to retrieve results", "details": "Unexpected format received from results endpoint."}

    except Exception as e:
        # Catch any other unexpected exceptions during the process
        logger.exception(f"Unhandled error in twitter_search tool for query '{query}', job UUID '{job_uuid if 'job_uuid' in locals() else 'N/A'}': {e}")
        return {"error": "An unexpected server error occurred during Twitter search", "details": str(e)}


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
        # Check if the helper returned an error structure
        if isinstance(result, dict) and "error" in result:
            logger.error(f"API error during web scrape for {url}: {result}")
            return result
        # Assuming success returns the expected scrape data structure
        elif isinstance(result, dict):
             logger.info(f"Web scrape successful for {url}")
             return result
        else:
            logger.error(f"Unexpected response type received from web scrape API: {type(result)} - {result}")
            return {"error": "Unexpected response format from web scrape API", "details": str(result)}

    except Exception as e:
        logger.exception(f"Error in scrape_web_page tool for URL '{url}': {e}")
        return {"error": f"An unexpected server error occurred during scraping: {str(e)}"}

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
        logger.warning("extract_search_terms called with empty userInput.")
        return {"error": "Bad request", "details": "userInput cannot be empty"}
    try:
        result = await _make_api_request(
            "POST",
            "/v1/search/extraction",
            json_data={"userInput": userInput}
        )
         # Check if the helper returned an error structure
        if isinstance(result, dict) and "error" in result:
            logger.error(f"API error during search term extraction: {result}")
            return result
        # Assuming success returns the expected extraction data structure
        elif isinstance(result, dict):
             logger.info(f"Search term extraction successful.")
             return result
        else:
            logger.error(f"Unexpected response type received from extraction API: {type(result)} - {result}")
            return {"error": "Unexpected response format from extraction API", "details": str(result)}

    except Exception as e:
        logger.exception(f"Error in extract_search_terms tool: {e}")
        return {"error": f"An unexpected server error occurred during term extraction: {str(e)}"}

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
         logger.warning("analyze_data called with missing 'tweets' or 'prompt'.")
         return {"error": "Bad request", "details": "'tweets' and 'prompt' are required fields"}
    try:
        result = await _make_api_request(
            "POST",
            "/v1/search/analysis",
            json_data={"tweets": tweets, "prompt": prompt}
        )
        # Check if the helper returned an error structure
        if isinstance(result, dict) and "error" in result:
            logger.error(f"API error during data analysis: {result}")
            return result
        # Assuming success returns the expected analysis data structure
        elif isinstance(result, dict):
             logger.info(f"Data analysis successful.")
             return result
        else:
            logger.error(f"Unexpected response type received from analysis API: {type(result)} - {result}")
            return {"error": "Unexpected response format from analysis API", "details": str(result)}

    except Exception as e:
        logger.exception(f"Error in analyze_data tool: {e}")
        return {"error": f"An unexpected server error occurred during data analysis: {str(e)}"}

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
         logger.warning("search_similar_twitter called with missing 'query' or 'keywords'.")
         return {"error": "Bad request", "details": "'query' and 'keywords' are required fields"}
    if not isinstance(keywords, list):
         logger.warning(f"search_similar_twitter called with non-list keywords: {keywords}")
         return {"error": "Bad request", "details": "'keywords' must be a list of strings"}

    try:
        result = await _make_api_request(
            "POST",
            "/v1/search/similarity/twitter",
            json_data={"query": query, "keywords": keywords, "max_results": max_results}
        )
        # Check if the helper returned an error structure
        if isinstance(result, dict) and "error" in result:
            logger.error(f"API error during similarity search: {result}")
            return result
        # Assuming success returns the expected similarity search data structure
        elif isinstance(result, dict) and "results" in result:
             logger.info(f"Similarity search successful.")
             return result
        else:
            logger.error(f"Unexpected response type or format received from similarity API: {type(result)} - {result}")
            return {"error": "Unexpected response format from similarity API", "details": str(result)}

    except Exception as e:
        logger.exception(f"Error in search_similar_twitter tool: {e}")
        return {"error": f"An unexpected server error occurred during similarity search: {str(e)}"}

# --- Main Execution --- (Same as before)
if __name__ == "__main__":
    logger.info("Starting FastMCP server for Masa Documentation API...")
    mcp.run()
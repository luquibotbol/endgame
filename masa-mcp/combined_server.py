# --- START OF FILE combined_server.py ---

import fastmcp
import httpx
import os
import asyncio
import logging
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional, Union # Ensure necessary typing hints are available

# --- Configuration ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Masa API Configuration
MASA_API_BASE_URL = os.getenv("MASA_API_BASE_URL", "https://data.dev.masalabs.ai/api") # Allow override via env var
MASA_API_KEY = os.getenv("MASA_API_KEY")

# Token Metrics API Configuration (Using V2 Base URL and Bearer Auth)
TM_API_BASE_URL = os.getenv("TM_API_BASE_URL", "https://api.tokenmetrics.com/v2") # V2 Base URL
TM_API_KEY = os.getenv("TM_API_KEY")

# Check for API keys but don't exit immediately, let tools fail gracefully
if not MASA_API_KEY:
    logger.warning("Masa API key (MASA_API_KEY) not found. Masa tools will not function.")
if not TM_API_KEY:
    logger.warning("Token Metrics API key (TM_API_KEY) not found. Token Metrics tools will not function.")

# --- FastMCP Server Setup ---
# Combine instructions from both files
mcp = fastmcp.FastMCP(
    name="Combined Masa and Token Metrics API Tool Server",
    instructions="""This server provides tools to interact with both the Masa Documentation API and the Token Metrics Data API.

--- Masa Documentation API Tools ---
- twitter_search(query: str, max_results: int = 100): Initiate and retrieve results for a real-time Twitter search.
- scrape_web_page(url: str, format: str = 'text'): Scrape content from a specific web URL.
- extract_search_terms(userInput: str): Extract optimized search terms from text using AI.
- analyze_data(tweets: str, prompt: str): Analyze provided text (e.g., tweets) based on a prompt.
- search_similar_twitter(query: str, keywords: List[str], max_results: int = 100): Search indexed Twitter content using similarity matching.

--- Token Metrics Data API Tools (Primarily V2) ---
- list_tokens(id: Union[str, List[str]], symbol: Union[str, List[str]], category: Union[str, List[str]], exchange: Union[str, List[str]]): Directory of crypto assets. Note: At least one filter is usually required by the API.
- get_token_details(token_id: int = 0, symbol: str = ""): Get detailed metadata for a specific token. Provide EITHER token_id OR symbol.
- get_hourly_ohlcv(token_id: int, symbol: str, startDate: str, endDate: str): Hourly price/volume data. Note: At least one token identifier and date range are required.
- get_daily_ohlcv(token_id: int, symbol: str, startDate: str, endDate: str): Daily price/volume data. Note: At least one token identifier and date range are required.
- get_trader_grades(token_id: int = 0, symbol: str = "", category: Union[str, List[str]] = "", exchange: Union[str, List[str]] = "", startDate: str, endDate: str, marketCap: str = "", volume: str = "", fdv: str = ""): Short-term trading grades. Start and end dates are required. Other filters are optional.
- get_investor_grades(token_id: int = 0, symbol: str = "", category: Union[str, List[str]] = "", exchange: Union[str, List[str]] = "", startDate: str, endDate: str, marketCap: str = "", volume: str = "", fdv: str = ""): Long-term investing grades. Start and end dates are required. Other filters are optional.
- get_trader_indices(startDate: str, endDate: str): Daily trader model portfolios. Requires start/end dates.
- get_investor_indices(type: str, startDate: str, endDate: str): Long-term investor model portfolios by type. Requires type and start/end dates.
- get_market_metrics(startDate: str, endDate: str): Whole-market analytics (Bull/Bear indicator, market breadth). Requires start/end dates.
- get_trading_signals(startDate: str, endDate: str, token_id: int = 0, symbol: str = "", category: Union[str, List[str]] = "", exchange: Union[str, List[str]] = "", marketCap: str = "", volume: str = "", fdv: str = "", signal: str = ""): AI-generated long/short signals and ROI. Start/end dates required. Other filters optional.
- get_ai_report(token_id: int = 0, symbol: str = ""): Narrative, algorithm-written research report. Provide EITHER token_id OR symbol.
- get_crypto_investor_portfolios(limit: Optional[int] = None): Snapshot of model Investor Portfolios. limit is optional.
- get_top_market_cap_tokens(top_k: int): Current Top-K coins by market capitalization. top_k is required.
- get_resistance_support(token_id: int = 0, symbol: str = ""): Historical support & resistance levels. Provide EITHER token_id OR symbol.
- list_exchanges(): List all exchanges supported by the API.
- list_categories(): List all token categories recognized by the API.
"""
)

# --- API Helper Functions ---

# Helper for Masa API requests (using MASA_API_KEY and Bearer Token)
async def _make_masa_api_request(
    method: str,
    endpoint: str,
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None
) -> Any:
    """Helper function to make authenticated Masa API requests."""
    if not MASA_API_KEY:
        logger.error("Masa API Key is not set, cannot make Masa API request.")
        return {"error": "Configuration Error", "details": "Masa API key not found."}

    headers = {"Authorization": f"{MASA_API_KEY}", "Content-Type": "application/json"}
    # Ensure endpoint starts with '/' if MASA_API_BASE_URL doesn't end with one
    endpoint_path = endpoint if endpoint.startswith('/') else f"/{endpoint}"
    url = f"{MASA_API_BASE_URL}{endpoint_path}"
    timeout_seconds = 120.0

    # Filter None params before sending
    filtered_params = {k: v for k, v in params.items() if v is not None} if params else None

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            logger.debug(f"Making Masa API Request: {method.upper()} {url} with params={filtered_params} json={json_data}")
            if method.upper() == "GET":
                resp = await client.get(url, headers=headers, params=filtered_params)
            elif method.upper() == "POST":
                resp = await client.post(url, headers=headers, json=json_data)
            else:
                logger.error(f"Unsupported HTTP method requested: {method}")
                return {"error": "Internal Server Error", "details": f"Unsupported HTTP method: {method}"}

            logger.debug(f"Masa API Response Status: {resp.status_code} for {method.upper()} {url}")
            resp.raise_for_status()

            if resp.status_code == 204 or not resp.content:
                 logger.warning(f"Received empty response (Status {resp.status_code}) for {method.upper()} {url}")
                 return None

            response_json = resp.json()
            logger.debug(f"Masa API Response JSON: {response_json}")
            return response_json

    except httpx.HTTPStatusError as e:
        error_body = "<no response body>"
        error_message = f"HTTP {e.response.status_code} Error"
        details_to_return = {}
        try:
            error_body = e.response.text
            try:
                 error_details = e.response.json()
                 error_message = error_details.get("message", error_details.get("error", error_message))
                 details_to_return = error_details
                 logger.error(f"Masa HTTP Status Error Details for {method.upper()} {url}: {error_details}")
            except Exception:
                 details_to_return = error_body
                 logger.error(f"Masa HTTP Status Error Body for {method.upper()} {url}: {error_body}")
        except Exception:
            logger.error(f"Masa HTTP Status Error occurred for {method.upper()} {url}, but failed to read response body.")

        logger.error(f"Masa HTTP Status Error for {method.upper()} {url}: {e.response.status_code}", exc_info=False)
        return {"error": error_message, "status_code": e.response.status_code, "details": details_to_return}
    except httpx.RequestError as e:
        logger.error(f"Masa Request Error for {method.upper()} {url}: {e}", exc_info=True)
        return {"error": "Connection Error", "details": f"Could not connect to Masa API: {e}"}
    except Exception as e:
        logger.exception(f"Unexpected error during Masa API request to {method.upper()} {url}: {e}")
        return {"error": "Unexpected Server Error", "details": str(e)}


# Helper for Token Metrics API requests (using TM_API_KEY and api_key or Bearer)
# Adapted to use Bearer Token for V2 endpoints, and handle data extraction/error structure
async def _make_tm_api_request(
    method: str,
    endpoint: str,
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None
) -> Union[Dict[str, Any], List[Any], None]:
    """
    Helper function to make authenticated Token Metrics API (V2) requests using Bearer Token.
    Extracts the 'data' field OR returns the full response if 'data' is missing.
    Returns the content (list or dict), or a structured error dict, or None for empty success.
    """
    if not TM_API_KEY:
        logger.error("Token Metrics API Key is not set, cannot make Token Metrics API request.")
        return {"error": "Configuration Error", "details": "Token Metrics API key not found."}

    # Using Bearer Token authorization for V2 as per metricmcp.py update
    headers = {
        # Change this line:
        # FROM: "Authorization": f"Bearer {TM_API_KEY}",
        # TO: Use the header name explicitly shown in their documentation:
        "api_key": TM_API_KEY,
        # Keep the Accept header as shown in their documentation
        "Accept": "application/json",
        # "Content-Type": "application/json" # httpx adds this for POST when json= is used
    }
    # Ensure endpoint starts with '/' if TM_API_BASE_URL doesn't end with one
    endpoint_path = endpoint if endpoint.startswith('/') else f"/{endpoint}"
    url = f"{TM_API_BASE_URL}{endpoint_path}"
    timeout_seconds = 60.0

    # Filter out parameters with None values *before* logging/sending
    filtered_params = {k: v for k, v in params.items() if v is not None} if params else None

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            logger.debug(f"Making TM API V2 Request: {method.upper()} {url} with params={filtered_params} json={json_data}")

            if method.upper() == "GET":
                resp = await client.get(url, headers=headers, params=filtered_params)
            elif method.upper() == "POST":
                 # Use json= argument for httpx to correctly set Content-Type and body
                resp = await client.post(url, headers=headers, json=json_data)
            else:
                logger.error(f"Unsupported HTTP method requested: {method}")
                return {"error": "Internal Server Error", "details": f"Unsupported HTTP method: {method}"}

            logger.debug(f"TM API Response Status: {resp.status_code} for {method.upper()} {url}")

            resp.raise_for_status() # Raises HTTPStatusError for 4xx/5xx responses

            if resp.status_code == 204 or not resp.content:
                 logger.warning(f"Received empty response (Status {resp.status_code}) for {method.upper()} {url}")
                 return None

            try:
                response_json = resp.json()
                logger.debug(f"TM API Full Response JSON: {response_json}")

                # V2 API might return data directly or within a 'data' field. Prioritize 'data'.
                if isinstance(response_json, dict) and "data" in response_json:
                    logger.debug("Successfully extracted 'data' field.")
                    return response_json["data"]
                elif isinstance(response_json, (dict, list)):
                     logger.info("TM API response did not contain a 'data' field, returning full response.")
                     return response_json # Return the whole JSON if 'data' key isn't present
                else:
                    logger.error(f"TM API Response is not a parsable dict or list: {response_json}")
                    return {"error": "API Response Format Error", "details": "Expected JSON dictionary or list in response."}

            except Exception as json_e:
                 logger.error(f"Failed to parse JSON response for {method.upper()} {url}: {json_e}", exc_info=True)
                 try: response_text = resp.text
                 except Exception: response_text = "<unreadable response>"
                 return {"error": "API Response Parsing Error", "details": f"Invalid JSON response. Response text start: {response_text[:200]}..."}

    except httpx.HTTPStatusError as e:
        error_body = "<no response body>"
        error_message = f"HTTP {e.response.status_code} Error"
        details_to_return = {}
        try:
            error_body = e.response.text
            try:
                 error_details = e.response.json()
                 error_message = error_details.get("message", error_details.get("error", error_message)) # Check common error keys
                 details_to_return = error_details
                 logger.error(f"TM HTTP Status Error Details for {method.upper()} {url}: {error_details}")
            except Exception:
                 details_to_return = error_body # Fallback to text body
                 logger.error(f"TM HTTP Status Error Body for {method.upper()} {url}: {error_body}")
        except Exception:
            logger.error(f"TM HTTP Status Error occurred for {method.upper()} {url}, but failed to read response body.")

        logger.error(f"TM HTTP Status Error for {method.upper()} {url}: {e.response.status_code}", exc_info=False)
        return {"error": error_message, "status_code": e.response.status_code, "details": details_to_return}

    except httpx.RequestError as e:
        logger.error(f"TM Request Error for {method.upper()} {url}: {e}", exc_info=True)
        return {"error": "Connection Error", "details": f"Could not connect to TM API: {e}"}
    except Exception as e:
        logger.exception(f"Unexpected error during TM API request to {method.upper()} {url}: {e}")
        return {"error": "Unexpected Server Error", "details": str(e)}


# --- Helper for Token Metrics API (From metricmcp.py) ---
def _prepare_list_param(value: Union[str, List[str], None]) -> Optional[str]:
    """Converts a list/string to a comma-separated string. Returns None if input is None or effectively empty."""
    if value is None: return None
    if isinstance(value, list):
        cleaned_list = [str(item).strip() for item in value if item and str(item).strip()]
        return ",".join(cleaned_list) if cleaned_list else None
    cleaned_str = str(value).strip()
    return cleaned_str if cleaned_str else None

# --- Standard Response Wrapper for Token Metrics Tools (From metricmcp.py) ---
def _wrap_results(result_data: Union[Dict[str, Any], List[Any], None]) -> Dict[str, Any]:
    """Wraps successful API data or handles errors/empty responses consistently."""
    # Check if the data is already an error dictionary
    if isinstance(result_data, dict) and "error" in result_data:
        # Error already logged in the API helper
        return result_data # Pass through the structured error
    elif result_data is None:
        # API helper returned None for success with no content/data
        logger.info("API returned success with empty data.")
        return {"results": []} # Consistent return for no results
    elif isinstance(result_data, (list, dict)):
        # Successful data (list from 'data' field, or dict/list from full response)
        count = len(result_data) if isinstance(result_data, list) else 1
        logger.info(f"Successfully retrieved data ({count} item(s)/structure).")
        return {"results": result_data} # Wrap in 'results' key
    else:
        # Unexpected data type from the helper
        logger.error(f"Unexpected data type received from API helper: {type(result_data)} - {result_data}")
        return {"error": "Unexpected API response format", "details": f"Received type: {type(result_data)}, value: {str(result_data)[:200]}..."}


# --- Masa Documentation API Tools (From server.py) ---

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
    logger.info(f"Masa Tool: Initiating Twitter search for query='{query}', max_results={max_results}")

    if not MASA_API_KEY:
         return {"error": "Configuration Error", "details": "Masa API key not found. Masa tools will not function."}

    # Ensure max_results doesn't exceed API limit
    if max_results > 100:
        logger.warning(f"Masa Tool: Requested max_results {max_results} exceeds API limit of 100. Setting to 100.")
        max_results = 100

    try:
        # 1. Initiate search
        init_payload = {"query": query, "max_results": max_results}
        init_data = await _make_masa_api_request(
            "POST",
            "/v1/search/live/twitter",
            json_data=init_payload
        )

        # Check for errors during initiation returned by _make_masa_api_request
        if isinstance(init_data, dict) and "error" in init_data:
             logger.error(f"Masa Tool: API error during job initiation: {init_data}")
             return init_data

        if not isinstance(init_data, dict) or "uuid" not in init_data:
            logger.error(f"Masa Tool: Failed to get job UUID from initiation response. Response: {init_data}")
            return {"error": "Failed to initiate job", "details": "No UUID received in response."}

        job_uuid = init_data.get("uuid")
        logger.info(f"Masa Tool: Twitter search job initiated with UUID: {job_uuid}")

        # 2. Poll for status
        attempts = 0
        max_attempts = 60
        poll_interval = 30

        while attempts < max_attempts:
            attempts += 1
            logger.info(f"Masa Tool: Checking status for job {job_uuid} (Attempt {attempts}/{max_attempts})")

            status_data = await _make_masa_api_request(
                "GET",
                f"/v1/search/live/twitter/status/{job_uuid}"
            )

            # Check for errors during status check
            if isinstance(status_data, dict) and "error" in status_data:
                logger.error(f"Masa Tool: API error during status check for job {job_uuid}: {status_data}")
                return status_data

            if not isinstance(status_data, dict) or "status" not in status_data:
                 logger.error(f"Masa Tool: Invalid status response for job {job_uuid}. Response: {status_data}")
                 await asyncio.sleep(poll_interval)
                 continue

            status = status_data.get("status", "unknown").lower()
            logger.info(f"Masa Tool: Job {job_uuid} status: {status}")

            if status == "done":
                logger.info(f"Masa Tool: Job {job_uuid} completed successfully.")
                break
            elif status == "error":
                 logger.error(f"Masa Tool: Job {job_uuid} failed permanently with status: {status}")
                 job_error_details = status_data.get("error", "No specific error message provided by API.")
                 return {"error": f"Twitter search job failed", "status": status, "details": job_error_details}
            elif status in ["processing", "pending", "queued", "error(retrying)"]:
                logger.info(f"Masa Tool: Job {job_uuid} status is '{status}'. Waiting {poll_interval}s...")
                await asyncio.sleep(poll_interval)
            else:
                logger.warning(f"Masa Tool: Job {job_uuid} has unexpected status: '{status}'. Continuing poll.")
                await asyncio.sleep(poll_interval)

        else:
            logger.error(f"Masa Tool: Twitter search job {job_uuid} timed out after {max_attempts * poll_interval} seconds.")
            return {"error": "Twitter search job timed out", "details": f"Job did not reach 'done' status after {max_attempts} attempts."}

        # 3. Get results
        logger.info(f"Masa Tool: Fetching results for completed job {job_uuid}")
        results_data = await _make_masa_api_request(
            "GET",
            f"/v1/search/live/twitter/result/{job_uuid}"
        )

        if isinstance(results_data, dict) and "error" in results_data:
             logger.error(f"Masa Tool: API error fetching results for job {job_uuid}: {results_data}")
             return results_data

        if isinstance(results_data, list):
            logger.info(f"Masa Tool: Successfully retrieved {len(results_data)} results for job {job_uuid}.")
            return {"results": results_data}
        else:
            logger.error(f"Masa Tool: Unexpected format for results of job {job_uuid}. Expected list, got {type(results_data)}. Response: {results_data}")
            return {"error": "Failed to retrieve results", "details": "Unexpected format received from results endpoint."}

    except Exception as e:
        logger.exception(f"Masa Tool: Unhandled error in twitter_search tool for query '{query}', job UUID '{job_uuid if 'job_uuid' in locals() else 'N/A'}': {e}")
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
    logger.info(f"Masa Tool: Requesting web scrape for URL='{url}', format='{format}'")
    if not MASA_API_KEY:
         return {"error": "Configuration Error", "details": "Masa API key not found. Masa tools will not function."}
    if not url:
        return {"error": "Input Error", "details": "URL cannot be empty."}
    try:
        result = await _make_masa_api_request(
            "POST",
            "/v1/search/live/web/scrape",
            json_data={"url": url, "format": format}
        )
        if isinstance(result, dict) and "error" in result:
            logger.error(f"Masa Tool: API error during web scrape for {url}: {result}")
            return result
        elif isinstance(result, dict):
             logger.info(f"Masa Tool: Web scrape successful for {url}")
             # Masa scrape returns a dict structure directly, not in a 'results' key usually
             return result
        else:
            logger.error(f"Masa Tool: Unexpected response type received from web scrape API: {type(result)} - {result}")
            return {"error": "Unexpected response format from web scrape API", "details": str(result)}

    except Exception as e:
        logger.exception(f"Masa Tool: Error in scrape_web_page tool for URL '{url}': {e}")
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
    logger.info(f"Masa Tool: Requesting search term extraction for input: '{userInput[:50]}...'")
    if not MASA_API_KEY:
         return {"error": "Configuration Error", "details": "Masa API key not found. Masa tools will not function."}
    if not userInput:
        logger.warning("Masa Tool: extract_search_terms called with empty userInput.")
        return {"error": "Bad request", "details": "userInput cannot be empty"}
    try:
        result = await _make_masa_api_request(
            "POST",
            "/v1/search/extraction",
            json_data={"userInput": userInput}
        )
        if isinstance(result, dict) and "error" in result:
            logger.error(f"Masa Tool: API error during search term extraction: {result}")
            return result
        elif isinstance(result, dict):
             logger.info(f"Masa Tool: Search term extraction successful.")
             # Masa extraction returns a dict structure directly
             return result
        else:
            logger.error(f"Masa Tool: Unexpected response type received from extraction API: {type(result)} - {result}")
            return {"error": "Unexpected response format from extraction API", "details": str(result)}

    except Exception as e:
        logger.exception(f"Masa Tool: Error in extract_search_terms tool: {e}")
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
    logger.info(f"Masa Tool: Requesting data analysis with prompt: '{prompt}' for data: '{tweets[:50]}...'")
    if not MASA_API_KEY:
         return {"error": "Configuration Error", "details": "Masa API key not found. Masa tools will not function."}
    if not tweets or not prompt:
         logger.warning("Masa Tool: analyze_data called with missing 'tweets' or 'prompt'.")
         return {"error": "Bad request", "details": "'tweets' and 'prompt' are required fields"}
    try:
        result = await _make_masa_api_request(
            "POST",
            "/v1/search/analysis",
            json_data={"tweets": tweets, "prompt": prompt}
        )
        if isinstance(result, dict) and "error" in result:
            logger.error(f"Masa Tool: API error during data analysis: {result}")
            return result
        elif isinstance(result, dict):
             logger.info(f"Masa Tool: Data analysis successful.")
             # Masa analysis returns a dict structure directly
             return result
        else:
            logger.error(f"Masa Tool: Unexpected response type received from analysis API: {type(result)} - {result}")
            return {"error": "Unexpected response format from analysis API", "details": str(result)}

    except Exception as e:
        logger.exception(f"Masa Tool: Error in analyze_data tool: {e}")
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
    logger.info(f"Masa Tool: Requesting similarity search for query='{query}', keywords={keywords}, max_results={max_results}")
    if not MASA_API_KEY:
         return {"error": "Configuration Error", "details": "Masa API key not found. Masa tools will not function."}
    if not query or not keywords:
         logger.warning("Masa Tool: search_similar_twitter called with missing 'query' or 'keywords'.")
         return {"error": "Bad request", "details": "'query' and 'keywords' are required fields"}
    if not isinstance(keywords, list) or not keywords:
         logger.warning(f"Masa Tool: search_similar_twitter called with invalid or empty keywords: {keywords}")
         return {"error": "Bad request", "details": "'keywords' must be a non-empty list of strings"}

    try:
        result = await _make_masa_api_request(
            "POST",
            "/v1/search/similarity/twitter",
            json_data={"query": query, "keywords": keywords, "max_results": max_results}
        )
        if isinstance(result, dict) and "error" in result:
            logger.error(f"Masa Tool: API error during similarity search: {result}")
            return result
        # Assuming Masa similarity returns a dict containing a 'results' key
        elif isinstance(result, dict) and "results" in result:
             logger.info(f"Masa Tool: Similarity search successful.")
             return result
        else:
            logger.error(f"Masa Tool: Unexpected response type or format received from similarity API: {type(result)} - {result}")
            return {"error": "Unexpected response format from similarity API", "details": str(result)}

    except Exception as e:
        logger.exception(f"Masa Tool: Error in search_similar_twitter tool: {e}")
        return {"error": f"An unexpected server error occurred during similarity search: {str(e)}"}

# --- Token Metrics Data API Tools (From metricmcp.py) ---

# Note: Parameter optionality/defaults based on the latest metricmcp.py provided.
# This allows flexibility (e.g., using either token_id or symbol) where the API supports it,
# even if the initial request asked to remove *all* optionality.

@mcp.tool()
async def list_tokens(
    id: Union[str, List[str]] = "", # Using default "" to allow missing, API needs at least one filter usually
    symbol: Union[str, List[str]] = "",
    category: Union[str, List[str]] = "",
    exchange: Union[str, List[str]] = ""
) -> Dict[str, Any]:
    """
    (TM) Directory of every crypto asset (ID, symbol, name).
    Args:
        id (Union[str, List[str]]): Comma-separated list of token IDs or a single ID.
        symbol (Union[str, List[str]]): Comma-separated list of symbols or a single symbol.
        category (Union[str, List[str]]): Comma-separated list of categories or a single category.
        exchange (Union[str, List[str]]): Comma-separated list of exchanges or a single exchange.
    Returns:
        Dict[str, Any]: A dictionary containing a 'results' list of tokens or an 'error' dictionary. Returns an empty list if no tokens match.
    """
    logger.info(f"TM Tool: Requesting list_tokens with id='{id}', symbol='{symbol}', category='{category}', exchange='{exchange}'")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}

    params = {
        "id": _prepare_list_param(id),
        "symbol": _prepare_list_param(symbol),
        "category": _prepare_list_param(category),
        "exchange": _prepare_list_param(exchange)
    }
    # The helper _make_tm_api_request will filter out None values created by _prepare_list_param

    result_data = await _make_tm_api_request("GET", "/tokens", params=params)
    return _wrap_results(result_data)

@mcp.tool()
async def get_token_details(token_id: int = 0, symbol: str = "") -> Dict[str, Any]:
    """
    (TM V1/V2?) Get detailed metadata for a specific token. Provide EITHER token_id OR symbol.
    Args:
        token_id (int): The token ID (provide 0 if using symbol).
        symbol (str): The token symbol (e.g., "BTC") (provide "" if using token_id).
    Returns:
        Dict[str, Any]: Contains 'results' (the token details object/list) or an 'error' dictionary.
    """
    logger.info(f"TM Tool: Requesting token details for token_id='{token_id}' or symbol='{symbol}'")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}
    if not token_id and not symbol: return {"error": "Input Error", "details": "Must provide either token_id or symbol."}

    # Assuming V2 uses uppercase parameters and TOKEN_ID takes precedence if both are non-null
    params = {
        "TOKEN_ID": token_id if token_id else None, # Use None if 0 provided
        "SYMBOL": symbol if symbol else None        # Use None if "" provided
    }
    # Verify endpoint path for V2 - Using placeholder '/token-details'. May need adjustment.
    result_data = await _make_tm_api_request("GET", "/token-details", params=params)
    return _wrap_results(result_data)


@mcp.tool()
async def get_hourly_ohlcv(
    token_id: int = 0, # Allowing 0 default to align with EITHER pattern if API supports
    symbol: str = "",    # Allowing "" default
    startDate: str = "", # Allowing "" default, though likely required by API
    endDate: str = ""    # Allowing "" default, though likely required by API
) -> Dict[str, Any]:
    """
    (TM) Hour-by-hour open/high/low/close/volume bars. Requires at least one token identifier and date range.
    Args:
        token_id (int): The token ID (provide 0 if using symbol).
        symbol (str): The token symbol (e.g., "BTC") (provide "" if using token_id).
        startDate (str): Start date for the range (YYYY-MM-DD). Required by API.
        endDate (str): End date for the range (YYYY-MM-DD). Required by API.
    Returns:
        Dict[str, Any]: A dictionary containing a 'results' list of OHLCV data or an 'error' dictionary. Returns an empty list if no data matches.
    """
    logger.info(f"TM Tool: Requesting hourly OHLCV for token_id='{token_id}', symbol='{symbol}', startDate='{startDate}', endDate='{endDate}'")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}
    # Basic input validation, API might have stricter checks
    if (not token_id and not symbol) or not startDate or not endDate:
         return {"error": "Input Error", "details": "Must provide token_id or symbol, AND startDate and endDate."}


    params = {
        "token_id": token_id if token_id else None,
        "symbol": symbol if symbol else None,
        "startDate": startDate if startDate else None,
        "endDate": endDate if endDate else None
    }

    result_data = await _make_tm_api_request("GET", "/hourly-ohlcv", params=params) # Verify endpoint V2
    return _wrap_results(result_data)

@mcp.tool()
async def get_daily_ohlcv(
    token_id: int = 0,
    symbol: str = "",
    startDate: str = "",
    endDate: str = ""
) -> Dict[str, Any]:
    """
    (TM) Daily open/high/low/close/volume bars. Requires at least one token identifier and date range.
    Args:
        token_id (int): The token ID (provide 0 if using symbol).
        symbol (str): The token symbol (e.g., "BTC") (provide "" if using token_id).
        startDate (str): Start date for the range (YYYY-MM-DD). Required by API.
        endDate (str): End date for the range (YYYY-MM-DD). Required by API.
    Returns:
        Dict[str, Any]: A dictionary containing a 'results' list of OHLCV data or an 'error' dictionary. Returns an empty list if no data matches.
    """
    logger.info(f"TM Tool: Requesting daily OHLCV for token_id='{token_id}', symbol='{symbol}', startDate='{startDate}', endDate='{endDate}'")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}
    if (not token_id and not symbol) or not startDate or not endDate:
         return {"error": "Input Error", "details": "Must provide token_id or symbol, AND startDate and endDate."}

    params = {
        "token_id": token_id if token_id else None,
        "symbol": symbol if symbol else None,
        "startDate": startDate if startDate else None,
        "endDate": endDate if endDate else None
    }

    result_data = await _make_tm_api_request("GET", "/daily-ohlcv", params=params) # Verify endpoint V2
    return _wrap_results(result_data)

@mcp.tool()
async def get_trader_grades(
    startDate: str, endDate: str, # Required by API
    token_id: int = 0,
    symbol: str = "",
    category: Union[str, List[str]] = "",
    exchange: Union[str, List[str]] = "",
    marketCap: str = "",
    volume: str = "",
    fdv: str = ""
) -> Dict[str, Any]:
    """
    (TM) Short-term composite grade + TA & Quant subgrades. Start and end dates required. Other filters optional.
    Args:
        startDate (str): Start date for the range (YYYY-MM-DD). Required.
        endDate (str): End date for the range (YYYY-MM-DD). Required.
        token_id (int): The token ID (provide 0 if not filtering).
        symbol (str): The token symbol (e.g., "BTC") (provide "" if not filtering).
        category (Union[str, List[str]]): Comma-separated list of categories or a single category ("" if not filtering).
        exchange (Union[str, List[str]]): Comma-separated list of exchanges or a single exchange ("" if not filtering).
        marketCap (str): Market Cap filter (e.g., "greaterThan:1000000") ("" if not filtering).
        volume (str): Volume filter ("" if not filtering).
        fdv (str): Fully Diluted Valuation filter ("" if not filtering).
    Returns:
        Dict[str, Any]: A dictionary containing a 'results' list of grades or an 'error' dictionary. Returns an empty list if no data matches.
    """
    logger.info(f"TM Tool: Requesting trader grades with filters: token_id='{token_id}', symbol='{symbol}', category='{category}', exchange='{exchange}', dates='{startDate}' to '{endDate}', marketCap='{marketCap}', volume='{volume}', fdv='{fdv}'")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}
    if not startDate or not endDate:
         return {"error": "Input Error", "details": "Both startDate and endDate are required."}

    params = {
        "token_id": token_id if token_id else None,
        "symbol": symbol if symbol else None,
        "category": _prepare_list_param(category),
        "exchange": _prepare_list_param(exchange),
        "startDate": startDate if startDate else None,
        "endDate": endDate if endDate else None,
        "marketCap": marketCap if marketCap else None,
        "volume": volume if volume else None,
        "fdv": fdv if fdv else None
    }

    result_data = await _make_tm_api_request("GET", "/trader-grades", params=params) # Verify endpoint V2
    return _wrap_results(result_data)

@mcp.tool()
async def get_investor_grades(
    startDate: str, endDate: str, # Required by API
    token_id: int = 0,
    symbol: str = "",
    category: Union[str, List[str]] = "",
    exchange: Union[str, List[str]] = "",
    marketCap: str = "",
    volume: str = "",
    fdv: str = ""
) -> Dict[str, Any]:
    """
    (TM) Long-term Tech / Fundamental / Valuation analysis grades. Start and end dates required. Other filters optional.
    Args:
        startDate (str): Start date for the range (YYYY-MM-DD). Required.
        endDate (str): End date for the range (YYYY-MM-DD). Required.
        token_id (int): The token ID (provide 0 if not filtering).
        symbol (str): The token symbol (e.g., "BTC") (provide "" if not filtering).
        category (Union[str, List[str]]): Comma-separated list of categories or a single category ("" if not filtering).
        exchange (Union[str, List[str]]): Comma-separated list of exchanges or a single exchange ("" if not filtering).
        marketCap (str): Market Cap filter (e.g., "greaterThan:1000000") ("" if not filtering).
        volume (str): Volume filter ("" if not filtering).
        fdv (str): Fully Diluted Valuation filter ("" if not filtering).
    Returns:
        Dict[str, Any]: A dictionary containing a 'results' list of grades or an 'error' dictionary. Returns an empty list if no data matches.
    """
    logger.info(f"TM Tool: Requesting investor grades with filters: token_id='{token_id}', symbol='{symbol}', category='{category}', exchange='{exchange}', dates='{startDate}' to '{endDate}', marketCap='{marketCap}', volume='{volume}', fdv='{fdv}'")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}
    if not startDate or not endDate:
         return {"error": "Input Error", "details": "Both startDate and endDate are required."}

    params = {
        "token_id": token_id if token_id else None,
        "symbol": symbol if symbol else None,
        "category": _prepare_list_param(category),
        "exchange": _prepare_list_param(exchange),
        "startDate": startDate if startDate else None,
        "endDate": endDate if endDate else None,
        "marketCap": marketCap if marketCap else None,
        "volume": volume if volume else None,
        "fdv": fdv if fdv else None
    }

    result_data = await _make_tm_api_request("GET", "/investor-grades", params=params) # Verify endpoint V2
    return _wrap_results(result_data)

@mcp.tool()
async def get_trader_indices(
    startDate: str,
    endDate: str
) -> Dict[str, Any]:
    """
    (TM) Daily model portfolios aimed at traders; each row shows asset weights for a specific index on a date. Requires start/end dates.
    Args:
        startDate (str): Start date for the range (YYYY-MM-DD). Required.
        endDate (str): End date for the range (YYYY-MM-DD). Required.
    Returns:
        Dict[str, Any]: A dictionary containing a 'results' list of index data or an 'error' dictionary. Returns an empty list if no data matches.
    """
    logger.info(f"TM Tool: Requesting trader indices from '{startDate}' to '{endDate}'")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}
    if not startDate or not endDate:
         return {"error": "Input Error", "details": "Both startDate and endDate are required."}

    params = {
        "startDate": startDate if startDate else None,
        "endDate": endDate if endDate else None
    }

    result_data = await _make_tm_api_request("GET", "/trader-indices", params=params) # Verify endpoint V2
    return _wrap_results(result_data)

@mcp.tool()
async def get_investor_indices(
    type: str, # 'type' is parameter name in API, mandatory for this tool
    startDate: str,
    endDate: str
) -> Dict[str, Any]:
    """
    (TM) Equivalent long-term portfolios for investors. Requires type and start/end dates.
    Args:
        type (str): The index family type (e.g., "TMVenture", "TMFundamental"). Required.
        startDate (str): Start date for the range (YYYY-MM-DD). Required.
        endDate (str): End date for the range (YYYY-MM-DD). Required.
    Returns:
        Dict[str, Any]: A dictionary containing a 'results' list of index data or an 'error' dictionary. Returns an empty list if no data matches.
    """
    logger.info(f"TM Tool: Requesting investor indices of type='{type}' from '{startDate}' to '{endDate}'")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}
    if not type or not startDate or not endDate:
         return {"error": "Input Error", "details": "type, startDate, and endDate are required."}

    params = {
        "type": type if type else None, # API parameter name is 'type'
        "startDate": startDate if startDate else None,
        "endDate": endDate if endDate else None
    }

    result_data = await _make_tm_api_request("GET", "/investor-indices", params=params) # Verify endpoint V2
    return _wrap_results(result_data)

# --- NEWLY ADDED V2 TOOLS (From metricmcp.py) ---

@mcp.tool()
async def get_market_metrics(startDate: str, endDate: str) -> Dict[str, Any]:
    """
    (TM V2) Whole-market analytics (e.g., Bull vs Bear indicator, market breadth). Requires start/end dates.
    Args:
        startDate (str): Start date for the range (YYYY-MM-DD). Required.
        endDate (str): End date for the range (YYYY-MM-DD). Required.
    Returns:
        Dict[str, Any]: Contains 'results' list of market metrics data or an 'error' dictionary.
    """
    logger.info(f"TM Tool: Requesting V2 market metrics from '{startDate}' to '{endDate}'")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}
    if not startDate or not endDate:
        return {"error": "Input Error", "details": "Both startDate and endDate are required."}

    params = {
        "START_DATE": startDate if startDate else None,
        "END_DATE": endDate if endDate else None
    }
    result_data = await _make_tm_api_request("GET", "/market-metrics", params=params)
    return _wrap_results(result_data)


@mcp.tool()
async def get_trading_signals(
    startDate: str, endDate: str, # Required by API
    token_id: int = 0, symbol: str = "",
    category: Union[str, List[str]] = "", exchange: Union[str, List[str]] = "",
    marketCap: str = "", volume: str = "", fdv: str = "", signal: str = ""
) -> Dict[str, Any]:
    """
    (TM V2) AI-generated long/short calls and cumulative ROI. Requires start/end dates. Others are optional filters.
    Args:
        startDate (str): Start date for the range (YYYY-MM-DD). Required.
        endDate (str): End date for the range (YYYY-MM-DD). Required.
        token_id (int): Filter by token ID (0 if not used).
        symbol (str): Filter by token symbol ("" if not used).
        category (Union[str, List[str]]): Filter by category/categories ("" or [] if not used).
        exchange (Union[str, List[str]]): Filter by exchange/exchanges ("" or [] if not used).
        marketCap (str): Market Cap filter string (e.g., ">1000000") ("" if not used).
        volume (str): Volume filter string ("" if not used).
        fdv (str): FDV filter string ("" if not used).
        signal (str): Filter by signal type (e.g., "long", "short") ("" if not used).
    Returns:
        Dict[str, Any]: Contains 'results' list of trading signals or an 'error' dictionary.
    """
    logger.info(f"TM Tool: Requesting V2 trading signals from '{startDate}' to '{endDate}' with filters: token_id={token_id}, symbol='{symbol}', category='{category}', exchange='{exchange}', marketCap='{marketCap}', volume='{volume}', fdv='{fdv}', signal='{signal}'")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}
    if not startDate or not endDate:
        return {"error": "Input Error", "details": "Both startDate and endDate are required."}

    params = {
        "START_DATE": startDate if startDate else None,
        "END_DATE": endDate if endDate else None,
        "TOKEN_ID": token_id if token_id else None,
        "SYMBOL": symbol if symbol else None,
        "CATEGORY": _prepare_list_param(category), # Handles "" or []
        "EXCHANGE": _prepare_list_param(exchange), # Handles "" or []
        "MARKETCAP": marketCap if marketCap else None,
        "VOLUME": volume if volume else None,
        "FDV": fdv if fdv else None,
        "SIGNAL": signal if signal else None
    }
    result_data = await _make_tm_api_request("GET", "/trading-signals", params=params)
    return _wrap_results(result_data)


@mcp.tool()
async def get_ai_report(token_id: int = 0, symbol: str = "") -> Dict[str, Any]:
    """
    (TM V2) Narrative, algorithm-written research report on a single asset. Provide EITHER token_id OR symbol.
    Args:
        token_id (int): The token ID (provide 0 if using symbol).
        symbol (str): The token symbol (provide "" if using token_id).
    Returns:
        Dict[str, Any]: Contains 'results' (the report data) or an 'error' dictionary.
    """
    logger.info(f"TM Tool: Requesting V2 AI report for token_id='{token_id}' or symbol='{symbol}'")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}
    if not token_id and not symbol:
         return {"error": "Input Error", "details": "Must provide either token_id or symbol."}
    # API doc says TOKEN_ID takes precedence if both sent, sending both non-null is okay.
    params = {
        "TOKEN_ID": token_id if token_id else None,
        "SYMBOL": symbol if symbol else None
    }
    result_data = await _make_tm_api_request("GET", "/ai-reports", params=params)
    return _wrap_results(result_data)


@mcp.tool()
async def get_crypto_investor_portfolios(limit: Optional[int] = None) -> Dict[str, Any]:
    """
    (TM V2) Snapshot of Token Metrics’ model “Investor Portfolios”.
    Args:
        limit (Optional[int]): Max rows to return (defaults to API standard page size).
    Returns:
        Dict[str, Any]: Contains 'results' list of portfolio data or an 'error' dictionary.
    """
    logger.info(f"TM Tool: Requesting V2 crypto investor portfolios with limit={limit}")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}

    params = {
        "limit": limit # API uses lowercase 'limit'
    }
    result_data = await _make_tm_api_request("GET", "/crypto-investors", params=params)
    return _wrap_results(result_data)


@mcp.tool()
async def get_top_market_cap_tokens(top_k: int) -> Dict[str, Any]:
    """
    (TM V2) The current Top-K coins by market-capitalisation. Requires top_k count.
    Args:
        top_k (int): Integer count of how many top coins to return (e.g., 50). Required.
    Returns:
        Dict[str, Any]: Contains 'results' list of top tokens or an 'error' dictionary.
    """
    logger.info(f"TM Tool: Requesting V2 top {top_k} market cap tokens")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}
    if not isinstance(top_k, int) or top_k <= 0:
        return {"error": "Input Error", "details": "top_k must be a positive integer."}

    params = {
        "TOP_K": top_k # API uses uppercase TOP_K
    }
    result_data = await _make_tm_api_request("GET", "/top-market-cap-tokens", params=params)
    return _wrap_results(result_data)


@mcp.tool()
async def get_resistance_support(token_id: int = 0, symbol: str = "") -> Dict[str, Any]:
    """
    (TM V2) Historical support & resistance price levels for one coin. Provide EITHER token_id OR symbol.
    Args:
        token_id (int): Numerical TM asset ID (provide 0 if using symbol).
        symbol (str): Ticker symbol (e.g. BTC) (provide "" if using token_id).
    Returns:
        Dict[str, Any]: Contains 'results' list/dict of S/R levels or an 'error' dictionary.
    """
    logger.info(f"TM Tool: Requesting V2 resistance/support for token_id='{token_id}' or symbol='{symbol}'")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}
    if not token_id and not symbol:
         return {"error": "Input Error", "details": "Must provide either token_id or symbol."}
    # API doc says TOKEN_ID takes precedence if both sent.
    params = {
        "TOKEN_ID": token_id if token_id else None,
        "SYMBOL": symbol if symbol else None
    }
    result_data = await _make_tm_api_request("GET", "/resistance-support", params=params)
    return _wrap_results(result_data)

@mcp.tool()
async def list_exchanges() -> Dict[str, Any]:
    """
    (TM V2) List all exchanges supported by the API.
    Args: None
    Returns:
        Dict[str, Any]: Contains 'results' list of exchanges or an 'error' dictionary.
    """
    logger.info("TM Tool: Requesting list of exchanges")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}
    result_data = await _make_tm_api_request("GET", "/exchanges") # Verify endpoint V2
    return _wrap_results(result_data)

@mcp.tool()
async def list_categories() -> Dict[str, Any]:
    """
    (TM V2) List all token categories recognized by the API.
    Args: None
    Returns:
        Dict[str, Any]: Contains 'results' list of categories or an 'error' dictionary.
    """
    logger.info("TM Tool: Requesting list of categories")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}
    result_data = await _make_tm_api_request("GET", "/categories") # Verify endpoint V2
    return _wrap_results(result_data)

@mcp.tool()
async def get_token_fundamental_data(
    startDate: str, endDate: str, # Required by API
    token_id: int = 0,
    symbol: str = ""
) -> Dict[str, Any]:
    """
    (TM V2) Get time-series fundamental data points for a token. Requires start/end dates and token identifier.
    Args:
        startDate (str): Start date for the range (YYYY-MM-DD). Required.
        endDate (str): End date for the range (YYYY-MM-DD). Required.
        token_id (int): The token ID (provide 0 if using symbol).
        symbol (str): The token symbol (e.g., "BTC") (provide "" if using token_id).
    Returns:
        Dict[str, Any]: Contains 'results' list of fundamental data points or an 'error' dictionary.
    """
    logger.info(f"TM Tool: Requesting V2 fundamental data for token_id='{token_id}' or symbol='{symbol}' from '{startDate}' to '{endDate}'")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}
    if (not token_id and not symbol) or not startDate or not endDate:
        return {"error": "Input Error", "details": "Must provide token_id or symbol, AND startDate and endDate."}

    params = {
        "START_DATE": startDate if startDate else None,
        "END_DATE": endDate if endDate else None,
        "TOKEN_ID": token_id if token_id else None,
        "SYMBOL": symbol if symbol else None
    }
    result_data = await _make_tm_api_request("GET", "/fundamental-data", params=params) # Verify endpoint V2
    return _wrap_results(result_data)

@mcp.tool()
async def get_token_onchain_data(
    startDate: str, endDate: str, # Required by API
    token_id: int = 0,
    symbol: str = ""
) -> Dict[str, Any]:
    """
    (TM V2) Get time-series on-chain data points for a token. Requires start/end dates and token identifier.
    Args:
        startDate (str): Start date for the range (YYYY-MM-DD). Required.
        endDate (str): End date for the range (YYYY-MM-DD). Required.
        token_id (int): The token ID (provide 0 if using symbol).
        symbol (str): The token symbol (e.g., "BTC") (provide "" if using token_id).
    Returns:
        Dict[str, Any]: Contains 'results' list of on-chain data points or an 'error' dictionary.
    """
    logger.info(f"TM Tool: Requesting V2 on-chain data for token_id='{token_id}' or symbol='{symbol}' from '{startDate}' to '{endDate}'")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}
    if (not token_id and not symbol) or not startDate or not endDate:
        return {"error": "Input Error", "details": "Must provide token_id or symbol, AND startDate and endDate."}

    params = {
        "START_DATE": startDate if startDate else None,
        "END_DATE": endDate if endDate else None,
        "TOKEN_ID": token_id if token_id else None,
        "SYMBOL": symbol if symbol else None
    }
    result_data = await _make_tm_api_request("GET", "/onchain-data", params=params) # Verify endpoint V2
    return _wrap_results(result_data)

@mcp.tool()
async def get_token_social_data(
    startDate: str, endDate: str, # Required by API
    token_id: int = 0,
    symbol: str = ""
) -> Dict[str, Any]:
    """
    (TM V2) Get time-series social metrics for a token. Requires start/end dates and token identifier.
    Args:
        startDate (str): Start date for the range (YYYY-MM-DD). Required.
        endDate (str): End date for the range (YYYY-MM-DD). Required.
        token_id (int): The token ID (provide 0 if using symbol).
        symbol (str): The token symbol (e.g., "BTC") (provide "" if using token_id).
    Returns:
        Dict[str, Any]: Contains 'results' list of social data points or an 'error' dictionary.
    """
    logger.info(f"TM Tool: Requesting V2 social data for token_id='{token_id}' or symbol='{symbol}' from '{startDate}' to '{endDate}'")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}
    if (not token_id and not symbol) or not startDate or not endDate:
        return {"error": "Input Error", "details": "Must provide token_id or symbol, AND startDate and endDate."}

    params = {
        "START_DATE": startDate if startDate else None,
        "END_DATE": endDate if endDate else None,
        "TOKEN_ID": token_id if token_id else None,
        "SYMBOL": symbol if symbol else None
    }
    result_data = await _make_tm_api_request("GET", "/social-data", params=params) # Verify endpoint V2
    return _wrap_results(result_data)

@mcp.tool()
async def get_market_summary(startDate: str, endDate: str) -> Dict[str, Any]:
    """
    (TM V2) Get overall market summary data over a date range. Requires start/end dates.
    Args:
        startDate (str): Start date for the range (YYYY-MM-DD). Required.
        endDate (str): End date for the range (YYYY-MM-DD). Required.
    Returns:
        Dict[str, Any]: Contains 'results' list of market summary data or an 'error' dictionary.
    """
    logger.info(f"TM Tool: Requesting V2 market summary from '{startDate}' to '{endDate}'")
    if not TM_API_KEY: return {"error": "Configuration Error", "details": "Token Metrics API key not found. TM tools will not function."}
    if not startDate or not endDate:
        return {"error": "Input Error", "details": "Both startDate and endDate are required."}

    params = {
        "START_DATE": startDate if startDate else None,
        "END_DATE": endDate if endDate else None
    }
    result_data = await _make_tm_api_request("GET", "/market-summary", params=params) # Verify endpoint V2
    return _wrap_results(result_data)


# --- Main Execution ---
if __name__ == "__main__":
    # Provide clear message about which API keys are missing
    if not MASA_API_KEY and not TM_API_KEY:
         logger.error("FastMCP server not started: Neither Masa nor Token Metrics API key found.")
         print("\n" + "="*60)
         print(" ERROR: Neither MASA_API_KEY nor TM_API_KEY found.")
         print(" Please set at least one in your environment variables or a '.env' file.")
         print(" Server cannot start without any API key.")
         print("="*60 + "\n")
         # Consider sys.exit(1) here if you absolutely require at least one key
    elif not MASA_API_KEY:
         logger.warning("Starting FastMCP server. Masa API key is missing, Masa tools will not work.")
         mcp.run()
    elif not TM_API_KEY:
         logger.warning("Starting FastMCP server. Token Metrics API key is missing, Token Metrics tools will not work.")
         mcp.run()
    else:
        logger.info(f"Starting FastMCP server for Masa API ({MASA_API_BASE_URL}) and Token Metrics API ({TM_API_BASE_URL})...")
        mcp.run()

# --- END OF FILE combined_server.py ---
# --- START OF FILE metricmcp.py ---

import fastmcp
import httpx
import os
import asyncio
import logging
from dotenv import load_dotenv
# Use Union directly for clarity where multiple simple types are allowed (str, List[str])
# Use Dict, Any, List for standard typing
from typing import Dict, Any, List, Union, Optional # Re-adding Optional for helper/optional tool args

# --- Configuration ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# !! IMPORTANT: Updated to V2 Base URL as per new endpoints.
# !! Existing V1 tools might break if their endpoints aren't available/identical in V2.
# !! Verify V1 tool endpoints against V2 documentation if needed.
TM_API_BASE_URL = os.getenv("TM_API_BASE_URL", "https://api.tokenmetrics.com/v2")
TM_API_KEY = os.getenv("TM_API_KEY")

# No exit here, let the tools handle the missing key via the helper
if not TM_API_KEY:
    logger.error("Token Metrics API key not found. Please set the TM_API_KEY environment variable in your .env file.")


# --- FastMCP Server Setup ---
# Updated instructions to include all tools (V1 placeholders + new V2 tools)
# NOTE: Assuming V1 tools like ohlcv, grades, indices might have V2 equivalents or need updating.
mcp = fastmcp.FastMCP(
    name="Token Metrics Data API Tool Server (V2 Focus)",
    instructions="""This server provides tools to interact with the Token Metrics Data API (primarily V2).
Available tools:
(V1/Potential V2 - Verify Endpoints):
- list_tokens(id: Union[str, List[str]], symbol: Union[str, List[str]], category: Union[str, List[str]], exchange: Union[str, List[str]]): Directory of crypto assets.
- get_token_details(token_id: int, symbol: str): Get detailed metadata for a specific token.
- get_hourly_ohlcv(token_id: int, symbol: str, startDate: str, endDate: str): Hourly price/volume data.
- get_daily_ohlcv(token_id: int, symbol: str, startDate: str, endDate: str): Daily price/volume data.
- get_trader_grades(token_id: int, symbol: str, category: Union[str, List[str]], exchange: Union[str, List[str]], startDate: str, endDate: str, marketCap: str, volume: str, fdv: str): Short-term trading grades.
- get_investor_grades(token_id: int, symbol: str, category: Union[str, List[str]], exchange: Union[str, List[str]], startDate: str, endDate: str, marketCap: str, volume: str, fdv: str): Long-term investing grades.
- get_trader_indices(startDate: str, endDate: str): Daily trader model portfolios.
- get_investor_indices(type: str, startDate: str, endDate: str): Long-term investor model portfolios by type.
- get_market_summary(startDate: str, endDate: str): Get overall market summary data over a date range.
- get_token_fundamental_data(token_id: int, symbol: str, startDate: str, endDate: str): Get time-series fundamental data points.
- get_token_onchain_data(token_id: int, symbol: str, startDate: str, endDate: str): Get time-series on-chain data points.
- get_token_social_data(token_id: int, symbol: str, startDate: str, endDate: str): Get time-series social metrics.
- list_exchanges(): List all exchanges supported by the API.
- list_categories(): List all token categories recognized by the API.

(New V2 Tools):
- get_market_metrics(startDate: str, endDate: str): Whole-market analytics (Bull/Bear indicator, market breadth) for a date range (YYYY-MM-DD).
- get_trading_signals(startDate: str, endDate: str, token_id: int, symbol: str, category: Union[str, List[str]], exchange: Union[str, List[str]], marketCap: str, volume: str, fdv: str, signal: str): AI-generated long/short signals and ROI. startDate and endDate are required. Other params are optional filters (use 0 or "").
- get_ai_report(token_id: int, symbol: str): Narrative, algorithm-written research report. Provide EITHER token_id (use 0 if using symbol) OR symbol (use "" if using token_id).
- get_crypto_investor_portfolios(limit: Optional[int]): Snapshot of model Investor Portfolios. limit is optional.
- get_top_market_cap_tokens(top_k: int): Current Top-K coins by market capitalization. top_k is required.
- get_resistance_support(token_id: int, symbol: str): Historical support & resistance levels. Provide EITHER token_id (use 0 if using symbol) OR symbol (use "" if using token_id).
"""
)

# --- Helper Function for API Requests ---
async def _make_tm_api_request(
    method: str,
    endpoint: str, # Endpoint should now be relative to the V2 base URL (e.g., "/market-metrics")
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None
) -> Union[Dict[str, Any], List[Any], None]:
    """
    Helper function to make authenticated Token Metrics API V2 requests using Bearer Token.
    Extracts the 'data' field OR returns the full response if 'data' is missing.
    Returns the content (list or dict), or a structured error dict, or None for empty success.
    """
    if not TM_API_KEY:
        logger.error("API Key is not set, cannot make request.")
        return {"error": "Configuration Error", "details": "Token Metrics API key not found."}

    # Updated to use Bearer Token authorization for V2
    headers = {
        "Authorization": f"Bearer {TM_API_KEY}",
        "Accept": "application/json",
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
                resp = await client.post(url, headers=headers, json=json_data)
            # Add PUT, DELETE etc. if needed later
            else:
                logger.error(f"Unsupported HTTP method requested: {method}")
                return {"error": "Internal Server Error", "details": f"Unsupported HTTP method: {method}"}

            logger.debug(f"TM API Response Status: {resp.status_code} for {method.upper()} {url}")

            resp.raise_for_status() # Raises HTTPStatusError for 4xx/5xx responses

            if resp.status_code == 204 or not resp.content:
                 logger.warning(f"Received empty response (Status {resp.status_code}) for {method.upper()} {url}")
                 return None # Indicate success with no data content

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
                 # Log more specific details if available
                 logger.error(f"HTTP Status Error Details for {method.upper()} {url}: {error_details}")
            except Exception:
                 details_to_return = error_body # Fallback to text body
                 logger.error(f"HTTP Status Error Body for {method.upper()} {url}: {error_body}")
        except Exception:
            logger.error(f"HTTP Status Error occurred for {method.upper()} {url}, but failed to read response body.")

        # Log the primary error before returning
        logger.error(f"HTTP Status Error for {method.upper()} {url}: {e.response.status_code}", exc_info=False)
        return {"error": error_message, "status_code": e.response.status_code, "details": details_to_return}

    except httpx.RequestError as e:
        logger.error(f"Request Error for {method.upper()} {url}: {e}", exc_info=True)
        return {"error": "Connection Error", "details": f"Could not connect to API: {e}"}
    except Exception as e:
        logger.exception(f"Unexpected error during API request to {method.upper()} {url}: {e}")
        return {"error": "Unexpected Server Error", "details": str(e)}

# --- Helper to prepare list parameters for API (comma-separated string) ---
def _prepare_list_param(value: Union[str, List[str], None]) -> Optional[str]:
    """Converts a list/string to a comma-separated string. Returns None if input is None or effectively empty."""
    if value is None: return None
    if isinstance(value, list):
        cleaned_list = [str(item).strip() for item in value if item and str(item).strip()]
        return ",".join(cleaned_list) if cleaned_list else None
    cleaned_str = str(value).strip()
    return cleaned_str if cleaned_str else None

# --- Standard Response Wrapper ---
def _wrap_results(result_data: Union[Dict[str, Any], List[Any], None]) -> Dict[str, Any]:
    """Wraps successful API data or handles errors/empty responses consistently."""
    if isinstance(result_data, dict) and "error" in result_data:
        # Error already logged in _make_tm_api_request or calling function
        return result_data # Pass through the error structure
    elif result_data is None:
        logger.info("API returned success with empty data.")
        return {"results": []} # Represent empty success as empty list or dict? List seems common.
    elif isinstance(result_data, (list, dict)):
        count = len(result_data) if isinstance(result_data, list) else 1
        logger.info(f"Successfully retrieved data ({count} item(s)/structure).")
        return {"results": result_data}
    else:
        logger.error(f"Unexpected data type received from API helper: {type(result_data)} - {result_data}")
        return {"error": "Unexpected API response format", "details": f"Received type: {type(result_data)}, value: {str(result_data)[:200]}..."}

# --- Token Metrics Tools (Existing - Verify against V2) ---
# These functions might need endpoint updates or parameter adjustments for V2

@mcp.tool()
async def list_tokens(
    id: Union[str, List[str]] = "", symbol: Union[str, List[str]] = "",
    category: Union[str, List[str]] = "", exchange: Union[str, List[str]] = ""
) -> Dict[str, Any]:
    """(V1/V2?) Directory of crypto assets. Filters combined."""
    logger.info(f"Requesting list_tokens (V1/V2?) with id='{id}', symbol='{symbol}', category='{category}', exchange='{exchange}'")
    # Assuming V2 uses uppercase params like others - adjust if needed
    params = {
        "ID": _prepare_list_param(id), # Check actual V2 param name
        "SYMBOL": _prepare_list_param(symbol), # Check actual V2 param name
        "CATEGORY": _prepare_list_param(category), # Check actual V2 param name
        "EXCHANGE": _prepare_list_param(exchange) # Check actual V2 param name
    }
    # Verify endpoint path for V2 - Using placeholder '/tokens'
    result_data = await _make_tm_api_request("GET", "/tokens", params=params)
    return _wrap_results(result_data)

# ... (Keep other existing V1 functions like get_hourly_ohlcv, get_daily_ohlcv, etc.) ...
# !! IMPORTANT: Review and update these V1 functions if you intend to use them with the V2 API !!
# !! They likely need endpoint and parameter name changes (e.g., startDate -> START_DATE) !!
# !! and potentially use different base URLs if V1 is still needed separately. !!

@mcp.tool()
async def get_token_details(token_id: int = 0, symbol: str = "") -> Dict[str, Any]:
    """(V1/V2?) Get detailed metadata for a specific token. Provide EITHER token_id OR symbol."""
    logger.info(f"Requesting token details (V1/V2?) for token_id='{token_id}' or symbol='{symbol}'")
    if not token_id and not symbol: return {"error": "Input Error", "details": "Must provide either token_id or symbol."}
    params = {
        "TOKEN_ID": token_id if token_id else None, # Assuming V2 uses uppercase
        "SYMBOL": symbol if symbol else None        # Assuming V2 uses uppercase
    }
    # Verify endpoint path for V2 - Using placeholder '/token-details'
    result_data = await _make_tm_api_request("GET", "/token-details", params=params)
    return _wrap_results(result_data)

# --- NEWLY ADDED V2 TOOLS ---

@mcp.tool()
async def get_market_metrics(startDate: str, endDate: str) -> Dict[str, Any]:
    """
    (V2) Whole-market analytics (e.g., Bull vs Bear indicator, market breadth). Requires start/end dates.
    Args:
        startDate (str): Start date for the range (YYYY-MM-DD).
        endDate (str): End date for the range (YYYY-MM-DD).
    Returns:
        Dict[str, Any]: Contains 'results' list of market metrics data or an 'error' dictionary.
    """
    logger.info(f"Requesting V2 market metrics from '{startDate}' to '{endDate}'")
    if not startDate or not endDate:
        return {"error": "Input Error", "details": "Both startDate and endDate are required."}

    params = {
        "START_DATE": startDate,
        "END_DATE": endDate
    }
    result_data = await _make_tm_api_request("GET", "/market-metrics", params=params)
    return _wrap_results(result_data)


@mcp.tool()
async def get_trading_signals(
    startDate: str, endDate: str,
    token_id: int = 0, symbol: str = "",
    category: Union[str, List[str]] = "", exchange: Union[str, List[str]] = "",
    marketCap: str = "", volume: str = "", fdv: str = "", signal: str = ""
) -> Dict[str, Any]:
    """
    (V2) AI-generated long/short calls and cumulative ROI. Requires start/end dates. Others are optional filters.
    Args:
        startDate (str): Start date for the range (YYYY-MM-DD). Required.
        endDate (str): End date for the range (YYYY-MM-DD). Required.
        token_id (int): Filter by token ID (0 if not used).
        symbol (str): Filter by token symbol ("" if not used).
        category (Union[str, List[str]]): Filter by category/categories.
        exchange (Union[str, List[str]]): Filter by exchange/exchanges.
        marketCap (str): Market Cap filter string (e.g., ">1000000").
        volume (str): Volume filter string.
        fdv (str): FDV filter string.
        signal (str): Filter by signal type (e.g., "long", "short").
    Returns:
        Dict[str, Any]: Contains 'results' list of trading signals or an 'error' dictionary.
    """
    logger.info(f"Requesting V2 trading signals from '{startDate}' to '{endDate}' with filters: token_id={token_id}, symbol='{symbol}', category='{category}', exchange='{exchange}', marketCap='{marketCap}', volume='{volume}', fdv='{fdv}', signal='{signal}'")
    if not startDate or not endDate:
        return {"error": "Input Error", "details": "Both startDate and endDate are required."}

    params = {
        "START_DATE": startDate,
        "END_DATE": endDate,
        "TOKEN_ID": token_id if token_id else None,
        "SYMBOL": symbol if symbol else None,
        "CATEGORY": _prepare_list_param(category),
        "EXCHANGE": _prepare_list_param(exchange),
        "MARKETCAP": marketCap if marketCap else None, # V2 uses MARKETCAP
        "VOLUME": volume if volume else None,
        "FDV": fdv if fdv else None,
        "SIGNAL": signal if signal else None
    }
    result_data = await _make_tm_api_request("GET", "/trading-signals", params=params)
    return _wrap_results(result_data)


@mcp.tool()
async def get_ai_report(token_id: int = 0, symbol: str = "") -> Dict[str, Any]:
    """
    (V2) Narrative, algorithm-written research report on a single asset. Provide EITHER token_id OR symbol.
    Args:
        token_id (int): The token ID (provide 0 if using symbol).
        symbol (str): The token symbol (provide "" if using token_id).
    Returns:
        Dict[str, Any]: Contains 'results' (the report data) or an 'error' dictionary.
    """
    logger.info(f"Requesting V2 AI report for token_id='{token_id}' or symbol='{symbol}'")
    if not token_id and not symbol:
         return {"error": "Input Error", "details": "Must provide either token_id or symbol."}
    # API doc says TOKEN_ID takes precedence if both sent, so sending both non-null is okay.
    params = {
        "TOKEN_ID": token_id if token_id else None,
        "SYMBOL": symbol if symbol else None
    }
    result_data = await _make_tm_api_request("GET", "/ai-reports", params=params)
    # AI reports might return a single complex object, _wrap_results handles dicts.
    return _wrap_results(result_data)


@mcp.tool()
async def get_crypto_investor_portfolios(limit: Optional[int] = None) -> Dict[str, Any]:
    """
    (V2) Snapshot of Token Metrics’ model “Investor Portfolios”.
    Args:
        limit (Optional[int]): Max rows to return (defaults to API standard page size).
    Returns:
        Dict[str, Any]: Contains 'results' list of portfolio data or an 'error' dictionary.
    """
    logger.info(f"Requesting V2 crypto investor portfolios with limit={limit}")
    params = {
        "limit": limit # API uses lowercase 'limit' according to example
    } # Pass None if limit is None, helper filters it.
    result_data = await _make_tm_api_request("GET", "/crypto-investors", params=params)
    return _wrap_results(result_data)


@mcp.tool()
async def get_top_market_cap_tokens(top_k: int) -> Dict[str, Any]:
    """
    (V2) The current Top-K coins by market-capitalisation. Requires top_k count.
    Args:
        top_k (int): Integer count of how many top coins to return (e.g., 50). Required.
    Returns:
        Dict[str, Any]: Contains 'results' list of top tokens or an 'error' dictionary.
    """
    logger.info(f"Requesting V2 top {top_k} market cap tokens")
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
    (V2) Historical support & resistance price levels for one coin. Provide EITHER token_id OR symbol.
    Args:
        token_id (int): Numerical TM asset ID (provide 0 if using symbol).
        symbol (str): Ticker symbol (e.g. BTC) (provide "" if using token_id).
    Returns:
        Dict[str, Any]: Contains 'results' list/dict of S/R levels or an 'error' dictionary.
    """
    logger.info(f"Requesting V2 resistance/support for token_id='{token_id}' or symbol='{symbol}'")
    if not token_id and not symbol:
         return {"error": "Input Error", "details": "Must provide either token_id or symbol."}
    # API doc says TOKEN_ID takes precedence if both sent.
    params = {
        "TOKEN_ID": token_id if token_id else None, # API uses uppercase
        "SYMBOL": symbol if symbol else None        # API uses uppercase
    }
    result_data = await _make_tm_api_request("GET", "/resistance-support", params=params)
    return _wrap_results(result_data)


# --- Main Execution ---
if __name__ == "__main__":
    if not TM_API_KEY:
        logger.error("FastMCP server not started due to missing Token Metrics API key.")
        print("\n" + "="*60)
        print(" ERROR: Token Metrics API key (TM_API_KEY) not found.")
        print(" Please set it in your environment variables or a '.env' file.")
        print(" Server cannot start without the API key.")
        print("="*60 + "\n")
        # Optional: exit(1) # Uncomment to force exit
    else:
        logger.info(f"Starting FastMCP server for Token Metrics Data API (Target: {TM_API_BASE_URL})...")
        logger.warning("Ensure that all desired tools are compatible with the targeted API version.")
        # Consider adding host/port configuration here if needed
        # mcp.run(host="0.0.0.0", port=8000)
        mcp.run()

# --- END OF FILE metricmcp.py ---
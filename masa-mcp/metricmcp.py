# --- START OF FILE tm_mcp/server.py ---

import fastmcp
import httpx
import os
import asyncio
import logging
from dotenv import load_dotenv
from typing import Dict, Any, List, Union # Removed Optional as per request

# --- Configuration ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TM_API_BASE_URL = "https://alpha.data-api.tokenmetrics.com/v1"
TM_API_KEY = os.getenv("TM_API_KEY")

# No exit here, let the tools handle the missing key via the helper
if not TM_API_KEY:
    logger.error("Token Metrics API key not found. Please set the TM_API_KEY environment variable in your .env file.")


# --- FastMCP Server Setup ---
# Updated instructions to reflect non-optional parameters
mcp = fastmcp.FastMCP(
    name="Token Metrics Data API Tool Server",
    instructions="""This server provides tools to interact with the Token Metrics Data API.
Available tools:
- list_tokens(id: Union[str, List[str]], symbol: Union[str, List[str]], category: Union[str, List[str]], exchange: Union[str, List[str]]): Directory of crypto assets.
- get_hourly_ohlcv(token_id: int, symbol: str, startDate: str, endDate: str): Hourly price/volume data.
- get_daily_ohlcv(token_id: int, symbol: str, startDate: str, endDate: str): Daily price/volume data.
- get_trader_grades(token_id: int, symbol: str, category: Union[str, List[str]], exchange: Union[str, List[str]], startDate: str, endDate: str, marketCap: str, volume: str, fdv: str): Short-term trading grades.
- get_investor_grades(token_id: int, symbol: str, category: Union[str, List[str]], exchange: Union[str, List[str]], startDate: str, endDate: str, marketCap: str, volume: str, fdv: str): Long-term investing grades.
- get_trader_indices(startDate: str, endDate: str): Daily trader model portfolios.
- get_investor_indices(type: str, startDate: str, endDate: str): Long-term investor model portfolios.
"""
)

# --- Helper Function for API Requests ---
async def _make_tm_api_request(
    method: str,
    endpoint: str,
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None
) -> Union[Dict[str, Any], List[Any], None]:
    """
    Helper function to make authenticated Token Metrics API requests.
    Extracts the 'data' field from a successful response.
    Returns the content of 'data' (can be a list or dict), or a structured error dict.
    """
    if not TM_API_KEY:
        logger.error("API Key is not set, cannot make request.")
        # Return a structured error instead of exiting the process
        return {"error": "Configuration Error", "details": "Token Metrics API key not found."}

    headers = {
        "api_key": TM_API_KEY,
        "Accept": "application/json",
        # "Content-Type": "application/json" # httpx adds this for POST when json= is used
    }
    url = f"{TM_API_BASE_URL}{endpoint}"
    timeout_seconds = 60.0 # Adjust if needed

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            # Note: Params filtering None happens at the tool level before calling this helper now
            logger.debug(f"Making TM API Request: {method.upper()} {url} with params={params} json={json_data}")

            if method.upper() == "GET":
                resp = await client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                resp = await client.post(url, headers=headers, json=json_data)
            else:
                logger.error(f"Unsupported HTTP method requested: {method}")
                return {"error": "Internal Server Error", "details": f"Unsupported HTTP method: {method}"}

            logger.debug(f"TM API Response Status: {resp.status_code} for {method.upper()} {url}")

            resp.raise_for_status() # Raises HTTPStatusError for 4xx/5xx responses

            if resp.status_code == 204 or not resp.content:
                 logger.warning(f"Received empty response (Status {resp.status_code}) for {method.upper()} {url}")
                 return None # Treat empty content as potentially empty data

            try:
                response_json = resp.json()
                logger.debug(f"TM API Full Response JSON: {response_json}")

                # Extract the 'data' field
                if isinstance(response_json, dict) and "data" in response_json:
                    logger.debug(f"Successfully extracted 'data' field.")
                    return response_json["data"]
                else:
                    logger.error(f"TM API Response JSON missing 'data' field or not a dict: {response_json}")
                    return {"error": "API Response Format Error", "details": "Expected 'data' field in response."}

            except Exception as json_e:
                 logger.error(f"Failed to parse JSON response for {method.upper()} {url}: {json_e}", exc_info=True)
                 try:
                     response_text = resp.text
                 except Exception:
                     response_text = "<unreadable response>"
                 return {"error": "API Response Parsing Error", "details": f"Invalid JSON response. Response text start: {response_text[:200]}..."}


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
            except Exception:
                 details_to_return = error_body
        except Exception:
            pass
        logger.error(f"HTTP Status Error for {method.upper()} {url}: {e.response.status_code} - Body: {error_body}", exc_info=True)
        return {"error": error_message, "status_code": e.response.status_code, "details": details_to_return}

    except httpx.RequestError as e:
        logger.error(f"Request Error for {method.upper()} {url}: {e}", exc_info=True)
        return {"error": "Connection Error", "details": f"Could not connect to API: {e}"}
    except Exception as e:
        logger.exception(f"Unexpected error during API request to {method.upper()} {url}: {e}")
        return {"error": "Unexpected Server Error", "details": str(e)}

# --- Helper to prepare list parameters for API (comma-separated string) ---
def _prepare_list_param(value: Union[str, List[str]]) -> str:
    """Converts a list of strings or a single string to a comma-separated string."""
    if isinstance(value, list):
        # Filter out None or empty strings from the list before joining
        # Assumes items in the list are convertible to string
        return ",".join([str(item).strip() for item in value if str(item).strip()])
    # If it's not a list, assume it's a single string or convertible to string
    return str(value).strip() if str(value).strip() else "" # Return empty string if value is empty/whitespace

# --- Token Metrics Tools (Parameters now non-optional as per user request) ---

@mcp.tool()
async def list_tokens(
    id: Union[str, List[str]],
    symbol: Union[str, List[str]],
    category: Union[str, List[str]],
    exchange: Union[str, List[str]]
) -> Dict[str, Any]:
    """
    Directory of every crypto asset (ID, symbol, name).
    Args:
        id (Union[str, List[str]]): Comma-separated list of token IDs or a single ID.
        symbol (Union[str, List[str]]): Comma-separated list of symbols or a single symbol.
        category (Union[str, List[str]]): Comma-separated list of categories or a single category.
        exchange (Union[str, List[str]]): Comma-separated list of exchanges or a single exchange.
    Returns:
        Dict[str, Any]: A dictionary containing a 'results' list of tokens or an 'error' dictionary. Returns an empty list if no tokens match.
    """
    logger.info(f"Requesting list_tokens with id='{id}', symbol='{symbol}', category='{category}', exchange='{exchange}'")

    params = {
        "id": _prepare_list_param(id),
        "symbol": _prepare_list_param(symbol),
        "category": _prepare_list_param(category),
        "exchange": _prepare_list_param(exchange)
    }

    # Note: Because parameters are now non-optional by tool definition,
    # we don't strictly *need* to filter None here.
    # However, the underlying API might still require at least one filter.
    # The _make_tm_api_request helper will send all provided params.
    # The API will handle cases where provided values result in no matches (HTTP 200, empty data).
    # If the API requires at least one filter to be non-empty,
    # and the client provides empty strings/lists for all, the API call might fail.
    # Let's keep the params dict creation simple as per the non-optional requirement.

    result_data = await _make_tm_api_request("GET", "/tokens", params=params)

    if isinstance(result_data, dict) and "error" in result_data:
        logger.error(f"API error in list_tokens: {result_data}")
        return result_data
    elif isinstance(result_data, list):
        logger.info(f"Successfully retrieved {len(result_data)} tokens.")
        return {"results": result_data}
    elif result_data is None:
         logger.warning("Received empty response data for list_tokens (might mean no results or API issue).")
         return {"results": []}
    else:
        logger.error(f"Unexpected data type received from list_tokens API: {type(result_data)} - {result_data}")
        return {"error": "Unexpected API response format", "details": str(result_data)}


@mcp.tool()
async def get_hourly_ohlcv(
    token_id: int,
    symbol: str,
    startDate: str,
    endDate: str
) -> Dict[str, Any]:
    """
    Hour-by-hour open/high/low/close/volume bars.
    Args:
        token_id (int): The token ID.
        symbol (str): The token symbol (e.g., "BTC").
        startDate (str): Start date for the range (YYYY-MM-DD).
        endDate (str): End date for the range (YYYY-MM-DD).
    Returns:
        Dict[str, Any]: A dictionary containing a 'results' list of OHLCV data or an 'error' dictionary. Returns an empty list if no data matches.
    """
    logger.info(f"Requesting hourly OHLCV for token_id='{token_id}', symbol='{symbol}', startDate='{startDate}', endDate='{endDate}'")

    params = {
        "token_id": token_id,
        "symbol": symbol,
        "startDate": startDate,
        "endDate": endDate
    }

    result_data = await _make_tm_api_request("GET", "/hourly-ohlcv", params=params)

    if isinstance(result_data, dict) and "error" in result_data:
        logger.error(f"API error in get_hourly_ohlcv: {result_data}")
        return result_data
    elif isinstance(result_data, list):
        logger.info(f"Successfully retrieved {len(result_data)} hourly OHLCV records.")
        return {"results": result_data}
    elif result_data is None:
         logger.warning("Received empty response data for get_hourly_ohlcv.")
         return {"results": []}
    else:
        logger.error(f"Unexpected data type received from get_hourly_ohlcv API: {type(result_data)} - {result_data}")
        return {"error": "Unexpected API response format", "details": str(result_data)}

@mcp.tool()
async def get_daily_ohlcv(
    token_id: int,
    symbol: str,
    startDate: str,
    endDate: str
) -> Dict[str, Any]:
    """
    Daily open/high/low/close/volume bars.
    Args:
        token_id (int): The token ID.
        symbol (str): The token symbol (e.g., "BTC").
        startDate (str): Start date for the range (YYYY-MM-DD).
        endDate (str): End date for the range (YYYY-MM-DD).
    Returns:
        Dict[str, Any]: A dictionary containing a 'results' list of OHLCV data or an 'error' dictionary. Returns an empty list if no data matches.
    """
    logger.info(f"Requesting daily OHLCV for token_id='{token_id}', symbol='{symbol}', startDate='{startDate}', endDate='{endDate}'")

    params = {
        "token_id": token_id,
        "symbol": symbol,
        "startDate": startDate,
        "endDate": endDate
    }

    result_data = await _make_tm_api_request("GET", "/daily-ohlcv", params=params)

    if isinstance(result_data, dict) and "error" in result_data:
        logger.error(f"API error in get_daily_ohlcv: {result_data}")
        return result_data
    elif isinstance(result_data, list):
        logger.info(f"Successfully retrieved {len(result_data)} daily OHLCV records.")
        return {"results": result_data}
    elif result_data is None:
         logger.warning("Received empty response data for get_daily_ohlcv.")
         return {"results": []}
    else:
        logger.error(f"Unexpected data type received from get_daily_ohlcv API: {type(result_data)} - {result_data}")
        return {"error": "Unexpected API response format", "details": str(result_data)}

@mcp.tool()
async def get_trader_grades(
    token_id: int,
    symbol: str,
    category: Union[str, List[str]],
    exchange: Union[str, List[str]],
    startDate: str,
    endDate: str,
    marketCap: str,
    volume: str,
    fdv: str
) -> Dict[str, Any]:
    """
    Short-term composite grade + TA & Quant subgrades.
    Args:
        token_id (int): The token ID.
        symbol (str): The token symbol (e.g., "BTC").
        category (Union[str, List[str]]): Comma-separated list of categories or a single category.
        exchange (Union[str, List[str]]): Comma-separated list of exchanges or a single exchange.
        startDate (str): Start date for the range (YYYY-MM-DD).
        endDate (str): End date for the range (YYYY-MM-DD).
        marketCap (str): Market Cap filter (e.g., "greaterThan:1000000").
        volume (str): Volume filter.
        fdv (str): Fully Diluted Valuation filter.
    Returns:
        Dict[str, Any]: A dictionary containing a 'results' list of grades or an 'error' dictionary. Returns an empty list if no data matches.
    """
    logger.info(f"Requesting trader grades with filters: token_id='{token_id}', symbol='{symbol}', category='{category}', exchange='{exchange}', dates='{startDate}' to '{endDate}', marketCap='{marketCap}', volume='{volume}', fdv='{fdv}'")

    params = {
        "token_id": token_id,
        "symbol": symbol,
        "category": _prepare_list_param(category),
        "exchange": _prepare_list_param(exchange),
        "startDate": startDate,
        "endDate": endDate,
        "marketCap": marketCap,
        "volume": volume,
        "fdv": fdv
    }

    result_data = await _make_tm_api_request("GET", "/trader-grades", params=params)

    if isinstance(result_data, dict) and "error" in result_data:
        logger.error(f"API error in get_trader_grades: {result_data}")
        return result_data
    elif isinstance(result_data, list):
        logger.info(f"Successfully retrieved {len(result_data)} trader grade records.")
        return {"results": result_data}
    elif result_data is None:
         logger.warning("Received empty response data for get_trader_grades.")
         return {"results": []}
    else:
        logger.error(f"Unexpected data type received from get_trader_grades API: {type(result_data)} - {result_data}")
        return {"error": "Unexpected API response format", "details": str(result_data)}

@mcp.tool()
async def get_investor_grades(
    token_id: int,
    symbol: str,
    category: Union[str, List[str]],
    exchange: Union[str, List[str]],
    startDate: str,
    endDate: str,
    marketCap: str,
    volume: str,
    fdv: str
) -> Dict[str, Any]:
    """
    Long-term Tech / Fundamental / Valuation analysis grades.
    Args:
        token_id (int): The token ID.
        symbol (str): The token symbol (e.g., "BTC").
        category (Union[str, List[str]]): Comma-separated list of categories or a single category.
        exchange (Union[str, List[str]]): Comma-separated list of exchanges or a single exchange.
        startDate (str): Start date for the range (YYYY-MM-DD).
        endDate (str): End date for the range (YYYY-MM-DD).
        marketCap (str): Market Cap filter (e.g., "greaterThan:1000000").
        volume (str): Volume filter.
        fdv (str): Fully Diluted Valuation filter.
    Returns:
        Dict[str, Any]: A dictionary containing a 'results' list of grades or an 'error' dictionary. Returns an empty list if no data matches.
    """
    logger.info(f"Requesting investor grades with filters: token_id='{token_id}', symbol='{symbol}', category='{category}', exchange='{exchange}', dates='{startDate}' to '{endDate}', marketCap='{marketCap}', volume='{volume}', fdv='{fdv}'")

    params = {
        "token_id": token_id,
        "symbol": symbol,
        "category": _prepare_list_param(category),
        "exchange": _prepare_list_param(exchange),
        "startDate": startDate,
        "endDate": endDate,
        "marketCap": marketCap,
        "volume": volume,
        "fdv": fdv
    }

    result_data = await _make_tm_api_request("GET", "/investor-grades", params=params)

    if isinstance(result_data, dict) and "error" in result_data:
        logger.error(f"API error in get_investor_grades: {result_data}")
        return result_data
    elif isinstance(result_data, list):
        logger.info(f"Successfully retrieved {len(result_data)} investor grade records.")
        return {"results": result_data}
    elif result_data is None:
         logger.warning("Received empty response data for get_investor_grades.")
         return {"results": []}
    else:
        logger.error(f"Unexpected data type received from get_investor_grades API: {type(result_data)} - {result_data}")
        return {"error": "Unexpected API response format", "details": str(result_data)}

@mcp.tool()
async def get_trader_indices(
    startDate: str,
    endDate: str
) -> Dict[str, Any]:
    """
    Daily model portfolios aimed at traders; each row shows asset weights for a specific index on a date.
    Args:
        startDate (str): Start date for the range (YYYY-MM-DD).
        endDate (str): End date for the range (YYYY-MM-DD).
    Returns:
        Dict[str, Any]: A dictionary containing a 'results' list of index data or an 'error' dictionary. Returns an empty list if no data matches.
    """
    logger.info(f"Requesting trader indices from '{startDate}' to '{endDate}'")

    params = {
        "startDate": startDate,
        "endDate": endDate
    }

    result_data = await _make_tm_api_request("GET", "/trader-indices", params=params)

    if isinstance(result_data, dict) and "error" in result_data:
        logger.error(f"API error in get_trader_indices: {result_data}")
        return result_data
    elif isinstance(result_data, list):
        logger.info(f"Successfully retrieved {len(result_data)} trader index records.")
        return {"results": result_data}
    elif result_data is None:
         logger.warning("Received empty response data for get_trader_indices.")
         return {"results": []}
    else:
        logger.error(f"Unexpected data type received from get_trader_indices API: {type(result_data)} - {result_data}")
        return {"error": "Unexpected API response format", "details": str(result_data)}

@mcp.tool()
async def get_investor_indices(
    type: str, # 'type' is parameter name in API, use it here.
    startDate: str,
    endDate: str
) -> Dict[str, Any]:
    """
    Equivalent long-term portfolios for investors.
    Args:
        type (str): The index family type (e.g., "TMVenture", "TMFundamental").
        startDate (str): Start date for the range (YYYY-MM-DD).
        endDate (str): End date for the range (YYYY-MM-DD).
    Returns:
        Dict[str, Any]: A dictionary containing a 'results' list of index data or an 'error' dictionary. Returns an empty list if no data matches.
    """
    logger.info(f"Requesting investor indices of type='{type}' from '{startDate}' to '{endDate}'")

    params = {
        "type": type, # API parameter name is 'type'
        "startDate": startDate,
        "endDate": endDate
    }

    result_data = await _make_tm_api_request("GET", "/investor-indices", params=params)

    if isinstance(result_data, dict) and "error" in result_data:
        logger.error(f"API error in get_investor_indices: {result_data}")
        return result_data
    elif isinstance(result_data, list):
        logger.info(f"Successfully retrieved {len(result_data)} investor index records.")
        return {"results": result_data}
    elif result_data is None:
         logger.warning("Received empty response data for get_investor_indices.")
         return {"results": []}
    else:
        logger.error(f"Unexpected data type received from get_investor_indices API: {type(result_data)} - {result_data}")
        return {"error": "Unexpected API response format", "details": str(result_data)}

# --- Main Execution ---
if __name__ == "__main__":
    if not TM_API_KEY:
        logger.error("FastMCP server not started due to missing Token Metrics API key.")
    else:
        logger.info("Starting FastMCP server for Token Metrics Data API...")
        mcp.run()

# --- END OF FILE tm_mcp/server.py ---
# --- START OF FILE test-client.py (Corrected) ---

import fastmcp
import os
import asyncio
import logging
import pprint # For pretty printing results
from typing import Union, List, Any # Needed for type hints in params/results
# Import StdioServerParameters and stdio_client specifically
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp import ClientSession # Import ClientSession

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- FastMCP Client Setup ---
# Update this path to point to your combined server file
MCP_SERVER_PATH = "combined_server.py" 

# --- Helper for printing results ---
def print_result(tool_name: str, result: Any):
    """Helper to log and pretty print results or errors."""
    logger.info(f"--- Result for {tool_name} ---")
    pprint.pprint(result)
    print("-" * 20 + "\n") # Separator

# --- Test Functions (Pass the session object) ---

async def test_twitter_search(session: ClientSession):
    logger.info("--- Testing Masa: twitter_search ---")
    query = "latest advancements in AI"
    max_res = 5
    try:
        # Call the tool directly on the session object
        result = await session.call_tool("twitter_search", {"query": query, "max_results": max_res})
        print_result("twitter_search", result)
    except Exception as e:
        logger.error(f"Error calling twitter_search: {e}", exc_info=True)

async def test_scrape_web_page(session: ClientSession):
    logger.info("--- Testing Masa: scrape_web_page ---")
    url_to_scrape = "https://example.com"
    try:
        result = await session.call_tool("scrape_web_page", {"url": url_to_scrape, "format": "text"})
        print_result("scrape_web_page", result)
    except Exception as e:
        logger.error(f"Error calling scrape_web_page: {e}", exc_info=True)

async def test_extract_search_terms(session: ClientSession):
    logger.info("--- Testing Masa: extract_search_terms ---")
    user_input = "Tell me about the economic impact of renewable energy sources."
    try:
        result = await session.call_tool("extract_search_terms", {"userInput": user_input})
        print_result("extract_search_terms", result)
    except Exception as e:
        logger.error(f"Error calling extract_search_terms: {e}", exc_info=True)

async def test_analyze_data(session: ClientSession):
    logger.info("--- Testing Masa: analyze_data ---")
    tweets_data = "The new electric car model is amazing!\nCharging infrastructure needs improvement though."
    analysis_prompt = "What is the overall sentiment and key points mentioned?"
    try:
        result = await session.call_tool("analyze_data", {"tweets": tweets_data, "prompt": analysis_prompt})
        print_result("analyze_data", result)
    except Exception as e:
        logger.error(f"Error calling analyze_data: {e}", exc_info=True)

async def test_search_similar_twitter(session: ClientSession):
    logger.info("--- Testing Masa: search_similar_twitter ---")
    similarity_query = "sustainable technology"
    similarity_keywords = ["green tech", "eco-friendly", "renewable energy", "sustainability"]
    max_sim_results = 5
    try:
        result = await session.call_tool(
            "search_similar_twitter",
            {
                "query": similarity_query,
                "keywords": similarity_keywords,
                "max_results": max_sim_results
            }
        )
        print_result("search_similar_twitter", result)
    except Exception as e:
        logger.error(f"Error calling search_similar_twitter: {e}", exc_info=True)

# --- Test Functions (Token Metrics Tools - Pass the session object) ---

async def test_list_tokens(session: ClientSession):
    logger.info("--- Testing TM: list_tokens ---")
    params = {
        "symbol": ["BTC", "ETH"],
        "category": "Layer 1,DeFi"
    }
    try:
        result = await session.call_tool("list_tokens", params)
        print_result("list_tokens", result)
    except Exception as e:
        logger.error(f"Error calling list_tokens: {e}", exc_info=True)

async def test_get_token_details(session: ClientSession):
    logger.info("--- Testing TM: get_token_details ---")
    params_symbol = {"symbol": "BTC"}
    params_id = {"token_id": 1}
    try:
        result_symbol = await session.call_tool("get_token_details", params_symbol)
        print_result("get_token_details (symbol)", result_symbol)
        result_id = await session.call_tool("get_token_details", params_id)
        print_result("get_token_details (token_id)", result_id)
    except Exception as e:
        logger.error(f"Error calling get_token_details: {e}", exc_info=True)

async def test_get_hourly_ohlcv(session: ClientSession):
    logger.info("--- Testing TM: get_hourly_ohlcv ---")
    params = {
        "symbol": "ETH",
        "startDate": "2024-01-01",
        "endDate": "2024-01-02"
    }
    try:
        result = await session.call_tool("get_hourly_ohlcv", params)
        print_result("get_hourly_ohlcv", result)
    except Exception as e:
        logger.error(f"Error calling get_hourly_ohlcv: {e}", exc_info=True)

async def test_get_daily_ohlcv(session: ClientSession):
    logger.info("--- Testing TM: get_daily_ohlcv ---")
    params = {
        "token_id": 1, # BTC
        "startDate": "2023-01-01",
        "endDate": "2023-12-31"
    }
    try:
        result = await session.call_tool("get_daily_ohlcv", params)
        print_result("get_daily_ohlcv", result)
    except Exception as e:
        logger.error(f"Error calling get_daily_ohlcv: {e}", exc_info=True)

async def test_get_trader_grades(session: ClientSession):
    logger.info("--- Testing TM: get_trader_grades ---")
    params = {
        "startDate": "2024-07-01",
        "endDate": "2024-07-10",
        "symbol": "SOL",
        "marketCap": "greaterThan:1000000000"
    }
    try:
        result = await session.call_tool("get_trader_grades", params)
        print_result("get_trader_grades", result)
    except Exception as e:
        logger.error(f"Error calling get_trader_grades: {e}", exc_info=True)

async def test_get_investor_grades(session: ClientSession):
    logger.info("--- Testing TM: get_investor_grades ---")
    params = {
        "startDate": "2024-06-01",
        "endDate": "2024-06-30",
        "category": ["Layer 2", "Scaling"],
        "exchange": "Binance"
    }
    try:
        result = await session.call_tool("get_investor_grades", params)
        print_result("get_investor_grades", result)
    except Exception as e:
        logger.error(f"Error calling get_investor_grades: {e}", exc_info=True)

async def test_get_trader_indices(session: ClientSession):
    logger.info("--- Testing TM: get_trader_indices ---")
    params = {
        "startDate": "2024-01-01",
        "endDate": "2024-01-05"
    }
    try:
        result = await session.call_tool("get_trader_indices", params)
        print_result("get_trader_indices", result)
    except Exception as e:
        logger.error(f"Error calling get_trader_indices: {e}", exc_info=True)

async def test_get_investor_indices(session: ClientSession):
    logger.info("--- Testing TM: get_investor_indices ---")
    params = {
        "type": "TMFundamental",
        "startDate": "2024-01-01",
        "endDate": "2024-01-05"
    }
    try:
        result = await session.call_tool("get_investor_indices", params)
        print_result("get_investor_indices", result)
    except Exception as e:
        logger.error(f"Error calling get_investor_indices: {e}", exc_info=True)

async def test_get_market_metrics(session: ClientSession):
    logger.info("--- Testing TM: get_market_metrics ---")
    params = {
        "startDate": "2024-01-01",
        "endDate": "2024-01-05"
    }
    try:
        result = await session.call_tool("get_market_metrics", params)
        print_result("get_market_metrics", result)
    except Exception as e:
        logger.error(f"Error calling get_market_metrics: {e}", exc_info=True)


async def test_get_trading_signals(session: ClientSession):
    logger.info("--- Testing TM: get_trading_signals ---")
    params = {
        "startDate": "2024-07-01",
        "endDate": "2024-07-10",
        "signal": "long",
        "symbol": "BTC"
    }
    try:
        result = await session.call_tool("get_trading_signals", params)
        print_result("get_trading_signals", result)
    except Exception as e:
        logger.error(f"Error calling get_trading_signals: {e}", exc_info=True)

async def test_get_ai_report(session: ClientSession):
    logger.info("--- Testing TM: get_ai_report ---")
    params_symbol = {"symbol": "SOL"}
    params_id = {"token_id": 1027}
    try:
        result_symbol = await session.call_tool("get_ai_report", params_symbol)
        print_result("get_ai_report (symbol)", result_symbol)
        result_id = await session.call_tool("get_ai_report", params_id)
        print_result("get_ai_report (token_id)", result_id)

    except Exception as e:
        logger.error(f"Error calling get_ai_report: {e}", exc_info=True)

async def test_get_crypto_investor_portfolios(session: ClientSession):
    logger.info("--- Testing TM: get_crypto_investor_portfolios ---")
    params_limited = {"limit": 5}
    params_nolimit = {}
    try:
        result_limited = await session.call_tool("get_crypto_investor_portfolios", params_limited)
        print_result("get_crypto_investor_portfolios (limited)", result_limited)
        result_nolimit = await session.call_tool("get_crypto_investor_portfolios", params_nolimit)
        print_result("get_crypto_investor_portfolios (no limit)", result_nolimit)
    except Exception as e:
        logger.error(f"Error calling get_crypto_investor_portfolios: {e}", exc_info=True)

async def test_get_top_market_cap_tokens(session: ClientSession):
    logger.info("--- Testing TM: get_top_market_cap_tokens ---")
    params = {"top_k": 10}
    try:
        result = await session.call_tool("get_top_market_cap_tokens", params)
        print_result("get_top_market_cap_tokens", result)
    except Exception as e:
        logger.error(f"Error calling get_top_market_cap_tokens: {e}", exc_info=True)

async def test_get_resistance_support(session: ClientSession):
    logger.info("--- Testing TM: get_resistance_support ---")
    params_symbol = {"symbol": "XRP"}
    params_id = {"token_id": 1} # BTC ID
    try:
        result_symbol = await session.call_tool("get_resistance_support", params_symbol)
        print_result("get_resistance_support (symbol)", result_symbol)
        result_id = await session.call_tool("get_resistance_support", params_id)
        print_result("get_resistance_support (token_id)", result_id)

    except Exception as e:
        logger.error(f"Error calling get_resistance_support: {e}", exc_info=True)

async def test_list_exchanges(session: ClientSession):
    logger.info("--- Testing TM: list_exchanges ---")
    params = {}
    try:
        result = await session.call_tool("list_exchanges", params)
        print_result("list_exchanges", result)
    except Exception as e:
        logger.error(f"Error calling list_exchanges: {e}", exc_info=True)

async def test_list_categories(session: ClientSession):
    logger.info("--- Testing TM: list_categories ---")
    params = {}
    try:
        result = await session.call_tool("list_categories", params)
        print_result("list_categories", result)
    except Exception as e:
        logger.error(f"Error calling list_categories: {e}", exc_info=True)

async def test_get_token_fundamental_data(session: ClientSession):
     logger.info("--- Testing TM: get_token_fundamental_data ---")
     params = {
        "symbol": "ADA",
        "startDate": "2024-06-01",
        "endDate": "2024-06-10"
     }
     try:
        result = await session.call_tool("get_token_fundamental_data", params)
        print_result("get_token_fundamental_data", result)
     except Exception as e:
        logger.error(f"Error calling get_token_fundamental_data: {e}", exc_info=True)

async def test_get_token_onchain_data(session: ClientSession):
     logger.info("--- Testing TM: get_token_onchain_data ---")
     params = {
        "token_id": 74, # Example ID for something like Dogecoin, verify if needed
        "startDate": "2024-06-01",
        "endDate": "2024-06-10"
     }
     try:
        result = await session.call_tool("get_token_onchain_data", params)
        print_result("get_token_onchain_data", result)
     except Exception as e:
        logger.error(f"Error calling get_token_onchain_data: {e}", exc_info=True)

async def test_get_token_social_data(session: ClientSession):
     logger.info("--- Testing TM: get_token_social_data ---")
     params = {
        "symbol": "SHIB",
        "startDate": "2024-06-01",
        "endDate": "2024-06-10"
     }
     try:
        result = await session.call_tool("get_token_social_data", params)
        print_result("get_token_social_data", result)
     except Exception as e:
        logger.error(f"Error calling get_token_social_data: {e}", exc_info=True)

async def test_get_market_summary(session: ClientSession):
     logger.info("--- Testing TM: get_market_summary ---")
     params = {
        "startDate": "2024-06-01",
        "endDate": "2024-06-10"
     }
     try:
        result = await session.call_tool("get_market_summary", params)
        print_result("get_market_summary", result)
     except Exception as e:
        logger.error(f"Error calling get_market_summary: {e}", exc_info=True)


# --- Main Execution ---
async def main():
    logger.info(f"Starting FastMCP client tests against {MCP_SERVER_PATH}...")

    # 1. Define the server parameters, explicitly using 'python3'
    server_params = StdioServerParameters(
        command="python3", # <-- Use 'python3' here
        args=[MCP_SERVER_PATH],
        env=os.environ
    )

    # 2. Start the server process and establish the client session
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # 3. Initialize the session (optional but good practice)
                await session.initialize()
                logger.info("Client session initialized. Running tests...")

                # # 4. Run tests, passing the session object
                # await test_twitter_search(session)
                # await test_scrape_web_page(session)
                # await test_extract_search_terms(session)
                # await test_analyze_data(session)
                # await test_search_similar_twitter(session)

                # await test_list_tokens(session)
                await test_get_token_details(session)
                # await test_get_hourly_ohlcv(session)
                # await test_get_daily_ohlcv(session)
                # await test_get_trader_grades(session)
                # await test_get_investor_grades(session)
                # await test_get_trader_indices(session)
                # await test_get_investor_indices(session)
                # await test_get_market_metrics(session)
                # await test_get_trading_signals(session)
                # await test_get_ai_report(session)
                # await test_get_crypto_investor_portfolios(session)
                # await test_get_top_market_cap_tokens(session)
                # await test_get_resistance_support(session)
                # await test_list_exchanges(session)
                # await test_list_categories(session)
                # await test_get_token_fundamental_data(session)
                # await test_get_token_onchain_data(session)
                # await test_get_token_social_data(session)
                # await test_get_market_summary(session)


                logger.info("FastMCP client tests completed successfully.")

    except FileNotFoundError:
        logger.error(f"Server script not found at '{MCP_SERVER_PATH}'.", exc_info=True)
        print(f"\nError: The combined server script was not found at '{MCP_SERVER_PATH}'.")
        print("Please ensure the path is correct.")
    except ConnectionRefusedError:
         logger.error(f"Could not connect to the server process.", exc_info=True)
         print(f"\nError: Could not connect to the server process.")
         print(f"Ensure 'python3 {MCP_SERVER_PATH}' can run correctly on its own and doesn't exit immediately.")
         print("Check the server's log output for errors during startup.")
    except ImportError as e:
        logger.error(f"Import Error: {e}.", exc_info=True)
        print(f"\nImport Error: {e}. Make sure all required libraries (mcp, fastmcp, httpx, python-dotenv) are installed.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during client setup or session:")
        print(f"\nAn unexpected error occurred: {e}")


if __name__ == "__main__":
    # Ensure your .env file is set up with MASA_API_KEY and TM_API_KEY
    asyncio.run(main())

# --- END OF FILE test-client.py (Corrected) ---
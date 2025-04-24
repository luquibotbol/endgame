import fastmcp
import asyncio
import logging
import pprint # For pretty printing results

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- FastMCP Client Setup ---
# Assumes server.py is in the same directory or accessible via Python path
# If server.py is running as a separate process, you'd use host/port:
# client = fastmcp.Client(host="localhost", port=8000) # Default port for mcp.run()
client = fastmcp.Client("server.py") # Use this if running client/server in same process context for testing

# --- Example Tool Calls ---

async def test_twitter_search():
    logger.info("--- Testing twitter_search ---")
    query = "latest advancements in AI"
    max_res = 5
    try:
        async with client: # Manages client connection lifecycle
            result = await client.call_tool("twitter_search", {"query": query, "max_results": max_res})
            logger.info(f"twitter_search result for '{query}':")
            pprint.pprint(result)
    except Exception as e:
        logger.error(f"Error calling twitter_search: {e}", exc_info=True)
    print("-" * 20 + "\n") # Separator

async def test_scrape_web_page():
    logger.info("--- Testing scrape_web_page ---")
    url_to_scrape = "https://example.com"
    try:
        async with client:
            result = await client.call_tool("scrape_web_page", {"url": url_to_scrape, "format": "text"})
            logger.info(f"scrape_web_page result for '{url_to_scrape}':")
            pprint.pprint(result)
    except Exception as e:
        logger.error(f"Error calling scrape_web_page: {e}", exc_info=True)
    print("-" * 20 + "\n") # Separator

async def test_extract_search_terms():
    logger.info("--- Testing extract_search_terms ---")
    user_input = "Tell me about the economic impact of renewable energy sources."
    try:
        async with client:
            result = await client.call_tool("extract_search_terms", {"userInput": user_input})
            logger.info(f"extract_search_terms result for '{user_input}':")
            pprint.pprint(result)
    except Exception as e:
        logger.error(f"Error calling extract_search_terms: {e}", exc_info=True)
    print("-" * 20 + "\n") # Separator

async def test_analyze_data():
    logger.info("--- Testing analyze_data ---")
    tweets_data = "The new electric car model is amazing!\nCharging infrastructure needs improvement though."
    analysis_prompt = "What is the overall sentiment and key points mentioned?"
    try:
        async with client:
            result = await client.call_tool("analyze_data", {"tweets": tweets_data, "prompt": analysis_prompt})
            logger.info(f"analyze_data result:")
            pprint.pprint(result)
    except Exception as e:
        logger.error(f"Error calling analyze_data: {e}", exc_info=True)
    print("-" * 20 + "\n") # Separator

async def test_search_similar_twitter():
    logger.info("--- Testing search_similar_twitter ---")
    similarity_query = "sustainable technology"
    similarity_keywords = ["green tech", "eco-friendly", "renewable energy", "sustainability"]
    max_sim_results = 5
    try:
        async with client:
            result = await client.call_tool(
                "search_similar_twitter",
                {
                    "query": similarity_query,
                    "keywords": similarity_keywords,
                    "max_results": max_sim_results
                }
            )
            logger.info(f"search_similar_twitter result for '{similarity_query}':")
            pprint.pprint(result)
    except Exception as e:
        logger.error(f"Error calling search_similar_twitter: {e}", exc_info=True)
    print("-" * 20 + "\n") # Separator


# --- Main Execution ---
async def main():
    logger.info("Starting FastMCP client tests...")
    # Run tests sequentially
    await test_twitter_search()
    await test_scrape_web_page()
    await test_extract_search_terms()
    await test_analyze_data()
    await test_search_similar_twitter()
    logger.info("Client tests completed.")

if __name__ == "__main__":
    asyncio.run(main())
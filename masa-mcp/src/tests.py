from fastmcp import Client
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

client = Client("main.py")

async def call_tool(query_input: str, max_results: int = 100):
    try:
        async with client:
            result = await client.call_tool("twitter_search", {"query": query_input, "max_results": max_results})
            print(result)
    except Exception as e:
        logging.error(f"Error calling tool: {e}")

asyncio.run(call_tool("Ford"))
from fastmcp import Client
import asyncio

client = Client("main.py")

async def call_tool(query_input: str):
    async with client:
        result = await client.call_tool("twitter_search", {"query": query_input})
        print(result)

asyncio.run(call_tool("Ford"))
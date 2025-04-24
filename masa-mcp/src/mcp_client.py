import sys
from pathlib import Path
from main import twitter_search

async def get_twitter_sentiment(query: str, max_results: int = 100) -> dict:
    """Get Twitter sentiment data using MCP."""
    try:
        results = await twitter_search(query, max_results)
        return results
    except Exception as e:
        print(f"Error getting Twitter sentiment: {e}")
        return {"tweets": [], "error": str(e)} 
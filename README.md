Combined Masa and Token Metrics Fast-MCP Server

This project implements a single Fast-MCP server that consolidates access to APIs from two different providers: Masa Documentation API and Token Metrics Data API. By using Fast-MCP, these APIs are exposed as a set of structured tools that can be easily consumed by clients, such as AI agents built with frameworks like LangChain/LangGraph.

Features

*   Consolidated API Access: A single server process provides tools for multiple external APIs.
*   Fast-MCP Integration: Leverages Fast-MCP for efficient, structured, and asynchronous tool calls.
*   Masa API Tools: Provides real-time Twitter search, web scraping, search term extraction, data analysis, and similar Twitter search.
*   Token Metrics API Tools (V2 Focus): Provides comprehensive cryptocurrency data including token lists, OHLCV (price/volume) data, trader/investor grades, market indices, market metrics, trading signals, AI reports, investor portfolios, top tokens by market cap, support/resistance levels, exchange/category lists, and fundamental/on-chain/social data.
*   LangChain/LangGraph Compatibility: Includes a client script demonstrating how to use `langchain-mcp-adapters` to easily integrate the tools with a LangGraph agent.
*   API Key Management: Securely loads API keys from a .env file.

Prerequisites

Before you begin, ensure you have the following installed:

1.  Python 3.8+: The server and clients are written in Python.
2.  Git: For cloning the repository.
3.  API Keys: You will need API keys for:
    *   Masa Documentation API: Obtain from Masa Labs.
    *   Token Metrics Data API: Obtain from Token Metrics.
    *   An LLM Provider: For the `client.py` LangGraph agent, you need access to a Language Model (e.g., OpenAI, Meta via Akash endpoint, etc.).

Setup

1.  Clone the repository:

    git clone <your_repository_url>
    cd <your_repository_directory>

2.  Create a .env file:
    Create a file named .env in the root of your project directory (the same directory as `combined_server.py`, `client.py`, and `test-client.py`). Add your API keys to this file:

    # Masa Documentation API Key
    MASA_API_KEY=your_masa_api_key_here

    # Token Metrics Data API Key (for V2 API)
    TM_API_KEY=your_tokenmetrics_api_key_here

    # Optional: Override default API base URLs
    # MASA_API_BASE_URL=https://data.dev.masalabs.ai/api
    # TM_API_BASE_URL=https://api.tokenmetrics.com/v2

    # Optional: LLM API Configuration for client.py (if not using default hardcoded values)
    # LLM_API_KEY=your_llm_api_key_here
    # LLM_API_BASE=your_llm_api_base_url_here

    Replace the placeholder values with your actual API keys.

3.  Install dependencies:
    Install the required Python packages using pip:

    pip install fastmcp mcp httpx python-dotenv langchain langchain-openai langgraph langchain-mcp-adapters

    (Note: `mcp` is a dependency of `fastmcp`, but explicitly listing key libraries is helpful).

Running the Server

The `combined_server.py` script acts as a Fast-MCP server. When you use a Fast-MCP client in `stdio` mode (as `client.py` and `test-client.py` do), the client is responsible for launching and managing the server process automatically.

You do not typically need to run `python combined_server.py` directly yourself when using the client scripts. The client will handle it.

However, you can run it directly for debugging purposes:

python3 combined_server.py

(Use `python` instead of `python3` if that is the command for your Python 3 installation).

When the server starts, it will print warnings if either `MASA_API_KEY` or `TM_API_KEY` is not found in its environment. This indicates that tools relying on the missing key will not function.

Running the Clients

Two client scripts are provided to demonstrate how to interact with the server. Both clients automatically start the `combined_server.py` process using `stdio` mode and communicate with it. They also ensure that your environment variables (including API keys from the .env file) are passed to the server subprocess.

1.  Running the Test Client (`test-client.py`)

    The `test-client.py` script makes direct calls to each tool defined in the server. This is useful for verifying that individual tools work as expected and for inspecting the raw output from the tools.

    python3 test-client.py

    This script will:
    *   Launch the `combined_server.py` process.
    *   Initialize an MCP client session.
    *   Sequentially call each tool with example parameters.
    *   Print the parameters used and the `CallToolResult` received from the server for each call.

    Look for `--- Result for <tool_name> ---` followed by the printed output. For Token Metrics tools, successful results will typically contain `{"results": [...]}` or `{"results": {...}}`. For Masa tools, the structure might vary based on the API endpoint. Configuration errors will be explicitly shown if an API key is missing.

2.  Running the LangGraph Agent Client (`client.py`)

    The `client.py` script demonstrates how to use `langchain-mcp-adapters` to load the tools from the server and integrate them with a LangGraph agent (`create_react_agent`). This allows a Language Model to decide which tools to call based on a natural language question and attempt to formulate a human-readable answer.

    python3 client.py

    This script will:
    *   Load your LLM API key (from .env or hardcoded if not in .env).
    *   Launch the `combined_server.py` process.
    *   Initialize an MCP client session.
    *   Load all tools using `langchain_mcp_adapters.load_mcp_tools`.
    *   Create a LangGraph agent using `create_react_agent` with a custom prompt designed to guide the LLM in interpreting tool outputs (especially JSON).
    *   Invoke the agent with a predefined question designed to trigger specific tool calls (e.g., requesting Bitcoin price data).
    *   Print the full agent response (including intermediate tool calls and results) and the final generated answer.

    Observe the agent's thought process in the printed output. You should see `AIMessage` objects with `tool_calls`, followed by `ToolMessage` objects containing the results from the server, and finally an `AIMessage` with the agent's synthesized answer based on the tool outputs.

Understanding API Keys and Environment Variables

It is crucial that the server process (`combined_server.py`) has access to the `MASA_API_KEY` and `TM_API_KEY` environment variables.

*   The .env file stores your keys securely.
*   `load_dotenv()` reads this file and populates `os.environ` in the Python process where it's executed.
*   In `client.py` and `test-client.py`, `load_dotenv()` runs, setting keys in the client's environment.
*   When the client uses `StdioServerParameters(..., env=os.environ)` to launch the server subprocess, it explicitly passes the client's current environment variables to the new server process.
*   The server script `combined_server.py` also calls `load_dotenv()`, but the keys passed via `env=os.environ` are typically available in its environment before its own `load_dotenv` fully completes, ensuring `os.getenv` can find them within the tool functions.

This setup ensures the keys are available to the server subprocess where the API calls are actually made.

Project Structure

.
├── .env                  # Your API keys (create this file)
├── combined_server.py    # The main Fast-MCP server script hosting all tools
├── client.py             # LangGraph agent client using the server
└── test-client.py        # Direct tool call client for testing

Troubleshooting

*   `FileNotFoundError: [Errno 2] No such file or directory: 'python'`:
    *   Issue: The client is trying to start the server using the command `python`, but this command is not found in your system's PATH, or it points to an incompatible Python version (like Python 2).
    *   Solution: Ensure you are using `command="python3"` in the `StdioServerParameters` initialization in both `client.py` and `test-client.py` if `python3` is the correct command on your system. (This should be fixed in the provided code, but double-check).
*   `ConnectionError: Failed to connect...` related to subprocess:
    *   Issue: The client could start the server process, but couldn't establish the Fast-MCP communication session.
    *   Solution: Run the `combined_server.py` script directly (`python3 combined_server.py`) to see if it starts without errors. Look for any Python exceptions printed by the server during its startup. Ensure necessary libraries are installed and API keys are present (as warnings/errors about missing keys will be printed).
*   Tool Call Results show `{"error": "Configuration Error", "details": "API key not found..."}`:
    *   Issue: The server process did not find the necessary API key(s) in its environment when a tool was called.
    *   Solution:
        *   Verify that your .env file exists in the same directory as the scripts.
        *   Verify that the keys (`MASA_API_KEY`, `TM_API_KEY`) are correctly named and have values in the .env file.
        *   Ensure `load_dotenv()` is called early in both the client script and the server script.
        *   Confirm that `env=os.environ` is correctly set in the `StdioServerParameters` in your client script.
*   LLM provides generic description of JSON or fails after tool call:
    *   Issue: The Language Model received the tool output (e.g., JSON) but struggled to parse or summarize it effectively, or the LLM provider endpoint had an internal error.
    *   Solution:
        *   Run `test-client.py` to verify the raw tool output is correct and not excessively large/complex for the LLM.
        *   Ensure the custom prompt in `client.py` is correctly structured with `MessagesPlaceholder(variable_name="messages")` and strong instructions on processing tool outputs.
        *   Consider using a more capable LLM model if possible.
        *   If the LLM endpoint is unreliable (like the previous 500 error), consider using a different provider or model.

Contributing

Feel free to fork this repository and submit pull requests.

MIT License

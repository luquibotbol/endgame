import asyncio
import os # Recommended for API keys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage # Import needed for standard input format

# --- Configuration ---

# 1. IMPORTANT: Update this to the full *absolute* path to your math_server.py file
#    Example Linux/macOS: "/home/user/projects/my_mcp_server/math_server.py"
#    Example Windows: "C:/Users/user/projects/my_mcp_server/math_server.py"
MATH_SERVER_PATH = r"/Users/shreybirmiwal/projects/endgame/masa-mcp/src/server.py" # <<< CHANGE THIS

# 2. Custom LLM Configuration
# It's best practice to load keys from environment variables, but direct assignment is shown here.
CUSTOM_API_KEY = "sk-lTDIFvqqhJRPJWah-C5FWA" # <<< Replace with your actual API key or use os.getenv("CUSTOM_API_KEY")
CUSTOM_BASE_URL = "https://chatapi.akash.network/api/v1"
CUSTOM_MODEL_NAME = "Meta-Llama-3-1-8B-Instruct-FP8" # The specific model available at your custom endpoint

# --- Main Asynchronous Function ---
async def run_agent():
    """Runs the MCP client and LangGraph agent."""

    print("Configuring LLM...")
    # Initialize ChatOpenAI with custom parameters
    model = ChatOpenAI(
        model=CUSTOM_MODEL_NAME,
        openai_api_key=CUSTOM_API_KEY,
        openai_api_base=CUSTOM_BASE_URL,
        # You might need to adjust other parameters like temperature=0 if needed
    )
    print(f"Using model '{CUSTOM_MODEL_NAME}' via endpoint '{CUSTOM_BASE_URL}'")

    # Server parameters for stdio connection
    server_params = StdioServerParameters(
        command="python3", # Make sure 'python' is in your PATH or use the full path to the python executable
        args=[MATH_SERVER_PATH],
    )
    print(f"Preparing to connect to stdio server: python {MATH_SERVER_PATH}")

    try:
        async with stdio_client(server_params) as (read, write):
            print("Stdio connection established. Initializing MCP session...")
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                print("MCP session initialized.")

                # Get tools from the MCP server
                print("Loading tools via MCP...")
                tools = await load_mcp_tools(session)
                tool_names = [tool.name for tool in tools]
                print(f"Loaded tools: {tool_names}")
                if not tools:
                    print("Warning: No tools loaded from the MCP server.")
                    # Decide how to proceed - maybe exit or continue without tools
                    # For this example, we'll continue, but the agent might fail if it needs tools.

                # Create the ReAct agent
                print("Creating ReAct agent...")
                agent = create_react_agent(model, tools)

                # Define the question
                question = "what's (3 + 5) x 12?"
                print(f"Invoking agent with question: '{question}'")

                # Define the input for the agent using the standard LangGraph format
                # Typically a dictionary with a 'messages' key containing a list of messages
                agent_input = {"messages": [HumanMessage(content=question)]}

                # Run the agent
                agent_response = await agent.ainvoke(agent_input)

                print("\n--- Agent Response ---")
                # The structure of agent_response depends on the agent executor.
                # For create_react_agent, the final answer is often in the 'messages' list.
                print(agent_response)

                # Attempt to extract and print the final answer clearly
                if isinstance(agent_response, dict) and "messages" in agent_response:
                    final_message = agent_response["messages"][-1]
                    print(f"\nFinal Answer Content: {final_message.content}")
                else:
                    print("\nCould not extract final answer from the response structure.")

    except FileNotFoundError:
        print(f"\nError: The math server script was not found at '{MATH_SERVER_PATH}'.")
        print("Please update the MATH_SERVER_PATH variable in the script to the correct absolute path.")
    except ConnectionRefusedError:
         print(f"\nError: Could not connect to the server process. Ensure 'python {MATH_SERVER_PATH}' can run correctly and doesn't exit immediately.")
    except ImportError as e:
        print(f"\nImport Error: {e}. Make sure all required libraries (mcp, langchain, etc.) are installed.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

# --- Script Entry Point ---
if __name__ == "__main__":
    # Basic check for the placeholder path
    if MATH_SERVER_PATH == "/path/to/your/math_server.py":
         print("Error: Please update the 'MATH_SERVER_PATH' variable in the script")
         print("with the actual absolute path to your math_server.py file before running.")
    elif CUSTOM_API_KEY == "sk-xxxxxxxx":
         print("Warning: API Key is set to the placeholder 'sk-xxxxxxxx'.")
         print("Please update 'CUSTOM_API_KEY' with your actual key.")
         # Decide if you want to proceed with a placeholder key or exit
         # For now, we'll proceed, but API calls will likely fail.
         print("Running async main function...")
         asyncio.run(run_agent())
    else:
         print("Starting agent execution...")
         # Run the main async function using asyncio's event loop
         asyncio.run(run_agent())
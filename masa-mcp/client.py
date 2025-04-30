# --- START OF FILE client.py ---

import asyncio
import os
# Import necessary components from mcp and langchain
from mcp import ClientSession
# For stdio client, need StdioServerParameters and stdio_client
from mcp.client.stdio import StdioServerParameters, stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI # Or your specific LLM class
from langchain_core.messages import HumanMessage
import logging # Ensure logging is imported if used

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- Configuration ---
# Update this path to point to your combined server file
MCP_SERVER_PATH = "combined_server.py" 

# Your API key and base URL for the LLM (assuming you want to keep the Akash setup)
LLM_API_KEY = "sk-lTDIFvqqhJRPJWah-C5FWA" 
LLM_API_BASE = "https://chatapi.akash.network/api/v1"

async def setup_agent():
    """Runs the MCP client and LangGraph agent."""

    # Ensure the LLM API key is available
    if not LLM_API_KEY:
        logger.error("LLM API key not set. Cannot initialize ChatOpenAI.")
        print("Please set your LLM API key.")
        return

    try:
        # 1. Initialize the Language Model
        logger.info("Initializing Language Model...")
        model = ChatOpenAI(
            model="Meta-Llama-3-1-8B-Instruct-FP8" ,
            openai_api_key=LLM_API_KEY,
            openai_api_base=LLM_API_BASE,
            temperature=0, # Lower temp for more predictable tool use
        )
        logger.info("Language Model initialized.")

        # 2. Set up the MCP server parameters for stdio
        # This tells the client how to start the server script
        logger.info(f"Setting up MCP server parameters for {MCP_SERVER_PATH}")
        server_params = StdioServerParameters(
            command="python3", # Or "python" depending on your system
            args=[MCP_SERVER_PATH],
            env=os.environ
        )
        logger.info("MCP server parameters configured.")


        # 3. Start the MCP client session
        logger.info("Starting MCP client session...")
        # The stdio_client context manager handles starting/stopping the server process
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:

                # 4. Initialize the MCP session and load tools
                logger.info("Initializing MCP session and loading tools...")
                await session.initialize()
                logger.info("MCP session initialized.")

                # Load tools using the langchain adapter - it discovers tools from the server
                tools = await load_mcp_tools(session)
                tool_names = [tool.name for tool in tools]
                logger.info(f"Loaded tools: {tool_names}")
                
                if not tools:
                    logger.error("No tools loaded from the MCP server. Check server logs for errors.")
                    print("No tools were loaded. Check if the server started correctly and registered tools.")
                    return

                # 5. Create the LangGraph agent
                logger.info("Creating LangGraph ReAct agent...")
                agent = create_react_agent(model, tools)

                question = input ("Ask the agent a question: ")
                if not question:
                    print("No question provided. Exiting.")
                    return
                
                print(f"Invoking agent with question: '{question}'")

                agent_input = {"messages": [HumanMessage(content=question)]}

                # Agent invocation loop (basic example, can be expanded for multi-turn)
                try:
                    agent_response = await agent.ainvoke(agent_input)

                print("\n--- Agent Response ---")
                print(agent_response["messages"][2])
                print("\n\n")

                #if isinstance(agent_response, dict) and "messages" in agent_response:
                    #final_message = agent_response["ToolMessage"]
                    #print(f"\n>>>Response: \n\n{final_message}")
                #else:
                    #print("\nCould not extract final answer from the response structure.")

                except Exception as agent_e:
                    logger.error(f"Error during agent invocation: {agent_e}", exc_info=True)
                    print(f"\nAn error occurred during agent processing: {agent_e}")


    # 7. Error Handling for MCP/Server Startup
    except FileNotFoundError:
        logger.error(f"Server script not found at '{MCP_SERVER_PATH}'.", exc_info=True)
        print(f"\nError: The combined server script was not found at '{MCP_SERVER_PATH}'.")
        print("Please update the MCP_SERVER_PATH variable in this script to the correct relative or absolute path.")
    except ConnectionRefusedError:
         logger.error(f"Could not connect to the server process.", exc_info=True)
         print(f"\nError: Could not connect to the server process.")
         print(f"Ensure 'python {MCP_SERVER_PATH}' can run correctly on its own and doesn't exit immediately.")
         print("Check the server's log output for errors during startup.")
    except ImportError as e:
        logger.error(f"Import Error: {e}.", exc_info=True)
        print(f"\nImport Error: {e}. Make sure all required libraries (mcp, langchain, langchain-openai, langchain-mcp-adapters, httpx, python-dotenv) are installed.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred during client setup or session:")
        print(f"\nAn unexpected error occurred: {e}")
        # traceback is included in logger.exception, but can be printed separately too if needed
        # import traceback
        # traceback.print_exc()


if __name__ == "__main__":
    # Need to set API keys as environment variables or in a .env file
    # export MASA_API_KEY='your_masa_key'
    # export TM_API_KEY='your_tm_key'
    # export OPENAI_API_KEY='your_llm_key' # Or LLM_API_KEY if using env var setup above
    
    # Example of setting env vars if not using .env file (replace with your actual keys)
    # os.environ['MASA_API_KEY'] = 'YOUR_MASA_API_KEY' 
    # os.environ['TM_API_KEY'] = 'YOUR_TM_API_KEY'
    # os.environ['LLM_API_KEY'] = LLM_API_KEY # Using the hardcoded key above

    asyncio.run(setup_agent())

# --- END OF FILE client.py ---
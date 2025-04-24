import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage 

MCP_SERVER_PATH = r"C:\Users\shrey\projects\endgame\masa-mcp\server.py"

async def setup_agent():
    """Runs the MCP client and LangGraph agent."""

    model = ChatOpenAI(
        model="Meta-Llama-3-1-8B-Instruct-FP8" ,
        openai_api_key="sk-lTDIFvqqhJRPJWah-C5FWA",
        openai_api_base="https://chatapi.akash.network/api/v1",
    )


    server_params = StdioServerParameters(
        command="python",
        args=[MCP_SERVER_PATH],
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:

                await session.initialize()
                print("MCP session initialized.")

                tools = await load_mcp_tools(session)
                tool_names = [tool.name for tool in tools]
                print(f"Loaded tools: {tool_names}")
                agent = create_react_agent(model, tools)

                question = "Whats the twitter sentiment for the TAO bittensor token?"
                print(f"Invoking agent with question: '{question}'")

                agent_input = {"messages": [HumanMessage(content=question)]}
                agent_response = await agent.ainvoke(agent_input)

                print("\n--- Agent Response ---")
                print(agent_response)

                if isinstance(agent_response, dict) and "messages" in agent_response:
                    final_message = agent_response["messages"][-1]
                    print(f"\nFinal Answer Content: {final_message.content}")
                else:
                    print("\nCould not extract final answer from the response structure.")



    except FileNotFoundError:
        print(f"\nError: The math server script was not found at '{MCP_SERVER_PATH}'.")
        print("Please update the MATH_SERVER_PATH variable in the script to the correct absolute path.")
    except ConnectionRefusedError:
         print(f"\nError: Could not connect to the server process. Ensure 'python {MCP_SERVER_PATH}' can run correctly and doesn't exit immediately.")
    except ImportError as e:
        print(f"\nImport Error: {e}. Make sure all required libraries (mcp, langchain, etc.) are installed.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(setup_agent())
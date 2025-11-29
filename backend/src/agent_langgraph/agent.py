"""
LangGraph Agent with Idealista Scraper Tool

A simple test agent that uses ApifyIdealistaScraper as a tool to scrape property data.
"""

import os
from typing import Annotated, TypedDict, List
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from src.idealista_scraper.apify_idealista_scraper import ApifyIdealistaScraper


# Load environment variables
load_dotenv()


# Initialize the scraper instance (shared across tool calls)
scraper = ApifyIdealistaScraper()


@tool
def scrape_idealista_listing(url: str, save_data: bool = True) -> dict:
    """
    Scrape property data from an Idealista listing URL.
    
    Args:
        url: The Idealista listing URL to scrape (e.g., "https://www.idealista.pt/imovel/34458598/")
        save_data: Whether to save the scraped data to a JSON file (default: True)
    
    Returns:
        dict: Property data from the listing, or None if scraping failed
    """
    try:
        result = scraper.scrape_single(url_listing=url, save_data=save_data)
        if result:
            return {
                "success": True,
                "data": result,
                "message": f"Successfully scraped property data from {url}"
            }
        else:
            return {
                "success": False,
                "data": None,
                "message": f"Failed to scrape property data from {url}"
            }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"Error scraping {url}: {str(e)}"
        }

# Define the agent state
class AgentState(TypedDict):
    messages: Annotated[list, lambda x, y: x + y]


def create_agent():
    """
    Create a LangGraph agent with Idealista scraping tools.
    
    Returns:
        StateGraph: The compiled agent graph
    """
    # Initialize the LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",  # Using a cheaper model for testing
        temperature=0
    )
    
    # Bind tools to the LLM
    tools = [scrape_idealista_listing]
    llm_with_tools = llm.bind_tools(tools)
    
    # Define the agent node
    def agent_node(state: AgentState):
        """Agent node that processes messages and decides on actions"""
        messages = state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    # Add conditional edges
    def should_continue(state: AgentState):
        """Determine if we should continue to tools or end"""
        messages = state["messages"]
        last_message = messages[-1]
        
        # If there are tool calls, route to tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        # Otherwise, end
        return END
    
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )
    
    # After tools, go back to agent
    workflow.add_edge("tools", "agent")
    
    # Compile the graph
    app = workflow.compile()
    
    return app


def run_agent_test(query: str):
    """
    Run a test query with the agent.
    
    Args:
        query: The user query to process
    
    Returns:
        The agent's response
    """
    agent = create_agent()
    
    # Create initial state
    initial_state = {
        "messages": [HumanMessage(content=query)]
    }
    
    # Run the agent
    result = agent.invoke(initial_state)
    
    return result


if __name__ == "__main__":
    # Test the agent
    print("=" * 60)
    print("LangGraph Agent with Idealista Scraper Tool")
    print("=" * 60)
    print()
    
    # Test query
    test_query = "Can you scrape the property data from https://www.idealista.pt/imovel/34458598/?"
    
    print(f"Query: {test_query}")
    print()
    print("Running agent...")
    print()
    
    result = run_agent_test(test_query)
    
    # Print the result
    print("Agent Response:")
    print("-" * 60)
    for message in result["messages"]:
        if isinstance(message, HumanMessage):
            print(f"Human: {message.content}")
        elif isinstance(message, AIMessage):
            print(f"AI: {message.content}")
            if hasattr(message, "tool_calls") and message.tool_calls:
                print(f"Tool Calls: {message.tool_calls}")
        print()
    
    print("=" * 60)


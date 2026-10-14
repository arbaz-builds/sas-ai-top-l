from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agent1 import agent1
from agent_state import State
from combion_agentm import combine_agent
from Final_agent import final_score
from image_analyzer import image_analyzer
from text_analyzer import text_analyzer
from tool import tools


def build_graph():
    g = StateGraph(State)

    g.add_node("agent1", agent1)
    g.add_node("tools", ToolNode(tools))
    g.add_node("text_analyzer", text_analyzer)
    g.add_node("image_analyzer", image_analyzer)
    g.add_node("combine_agent", combine_agent)
    g.add_node("final_score", final_score)

    g.add_edge(START, "agent1")

    # agent1 chats with the client. If it needs a tool (RAG / API) it calls it, and then the analysis starts.
    # If it needs no tool, it is a normal chat reply and the graph ends.
    g.add_conditional_edges("agent1", tools_condition, {"tools": "tools", END: END})

    # text and image are analyzed in parallel
    g.add_edge("tools", "text_analyzer")
    g.add_edge("tools", "image_analyzer")

    # combine waits for BOTH analyzers, then the final agent gives score + reasons
    g.add_edge(["text_analyzer", "image_analyzer"], "combine_agent")
    g.add_edge("combine_agent", "final_score")
    g.add_edge("final_score", END)

    return g.compile()


graph = build_graph()


if __name__ == "__main__":
    result = graph.invoke({"messages": [HumanMessage(content=input("You: "))]})
    print(result.get("Finaloutput") or result["messages"][-1].content)

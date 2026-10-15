from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agent1 import IntroDecision_LLM
from TOOL_node import Tool_node_LLM
from agent_state import State
from combion_agentm import combine_agent
from Final_agent import final_score
from image_analyzer import image_analyzer
from text_analyzer import text_analyzer
from tool import tools


def intro_route(state: State):
    # IntroDecision_LLM must write its decision to state["decision"].
    # "unclear" (greeting, casual chat, details missing) -> its reply is the answer, graph ends.
    # any other decision (client asked for analysis and gave enough details) -> start the analysis flow.
    decision = state.get("decision")
    if not decision or decision == "unclear":
        return END
    return "LLM_ToolNode"


def tool_route(state: State):
    # LLM_ToolNode wants a tool -> run it (result comes back to LLM_ToolNode).
    # No more tools needed -> text and image analysis start (in parallel).
    if getattr(state["messages"][-1], "tool_calls", None):
        return "tools"
    return ["text_analyzer", "image_analyzer"]


def build_graph():
    g = StateGraph(State)

    g.add_node("IntroDecision", IntroDecision_LLM)
    g.add_node("LLM_ToolNode", Tool_node_LLM)
    g.add_node("tools", ToolNode(tools))
    g.add_node("text_analyzer", text_analyzer)
    g.add_node("image_analyzer", image_analyzer)
    g.add_node("combine_agent", combine_agent)
    g.add_node("final_score", final_score)

    g.add_edge(START, "IntroDecision")

    # IntroDecision: chat reply and stop, or start the flow
    g.add_conditional_edges("IntroDecision", intro_route, ["LLM_ToolNode", END])

    # LLM_ToolNode <-> tools loop; when no tool is needed, go to the analyzers
    g.add_conditional_edges("LLM_ToolNode", tool_route, ["tools", "text_analyzer", "image_analyzer"])
    g.add_edge("tools", "LLM_ToolNode")

    # combine waits for BOTH analyzers, then the final agent gives score + reasons
    g.add_edge(["text_analyzer", "image_analyzer"], "combine_agent")
    g.add_edge("combine_agent", "final_score")
    g.add_edge("final_score", END)

    return g.compile()


graph = build_graph()


if __name__ == "__main__":
    result = graph.invoke({"messages": [HumanMessage(content=input("You: "))]})
    print(result.get("Finaloutput") or result["messages"][-1].content)

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agent1 import agent1
from agent_state import State
from combion_agentm import combine_agent
from Final_agent import final_score
from image_analyzer import image_analyzer
from text_analyzer import text_analyzer
from tool import tools


def _has_image(msg):
    return isinstance(msg.content, list) and any(
        isinstance(p, dict) and p.get("type") == "image_url" for p in msg.content
    )


def _this_turn(messages):
    # everything from the client's latest message onwards = the current turn
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            return messages[i:]
    return []


def route_after_agent1(state: State):
    messages = state["messages"]

    # 1) agent1 wants a tool -> run it (the result comes back to agent1)
    if getattr(messages[-1], "tool_calls", None):
        return "tools"

    # 2) agent1 is done. If this turn brought claim data (a tool result or an image) -> analyze it
    turn = _this_turn(messages)
    has_tool_result = any(isinstance(m, ToolMessage) for m in turn)
    has_image = any(isinstance(m, HumanMessage) and _has_image(m) for m in turn)
    if has_tool_result or has_image:
        return ["text_analyzer", "image_analyzer"]

    # 3) normal chat -> reply and stop
    return END


def build_graph():
    g = StateGraph(State)

    g.add_node("agent1", agent1)
    g.add_node("tools", ToolNode(tools))
    g.add_node("text_analyzer", text_analyzer)
    g.add_node("image_analyzer", image_analyzer)
    g.add_node("combine_agent", combine_agent)
    g.add_node("final_score", final_score)

    g.add_edge(START, "agent1")

    # agent1 -> tools, or analysis, or END
    g.add_conditional_edges("agent1", route_after_agent1, ["tools", "text_analyzer", "image_analyzer", END])

    # the tool result goes back to agent1 (it can call another tool or answer)
    g.add_edge("tools", "agent1")

    # combine waits for BOTH analyzers, then the final agent gives score + reasons
    g.add_edge(["text_analyzer", "image_analyzer"], "combine_agent")
    g.add_edge("combine_agent", "final_score")
    g.add_edge("final_score", END)

    return g.compile()


graph = build_graph()


if __name__ == "__main__":
    result = graph.invoke({"messages": [HumanMessage(content=input("You: "))]})
    print(result.get("Finaloutput") or result["messages"][-1].content)

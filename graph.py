from langgraph.graph import StateGraph, START, END
from auth_node import auth_node
from permission_node import permission_node
from s3_inspector_node import s3_inspector_node
from report_node import report_node

graph = StateGraph(dict)  

graph.add_node("auth", auth_node)
graph.add_node("perm", permission_node)
graph.add_node("inspect", s3_inspector_node)
graph.add_node("report", report_node)

graph.add_edge(START, "auth")
graph.add_edge("auth", "perm")
graph.add_edge("perm", "inspect")
graph.add_edge("inspect", "report")
graph.add_edge("report", END)

app = graph.compile()

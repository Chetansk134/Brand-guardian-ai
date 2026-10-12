from langgraph.graph import StateGraph, END

from backend.src.graph.state import VideoAuditState

from backend.src.graph.nodes import (index_video_node, audit_content_node)


def create_graph():
            """
            Creates a StateGraph for the video audit workflow.
            The graph consists of two nodes:
            1. index_video_node: Ingests and extracts data from the video.
            2. audit_content_node: Analyzes the extracted data for compliance issues.
            """
            # 1. Initialize the StateGraph with the VideoAuditState schema
            workflow = StateGraph(VideoAuditState)
            # 2. Add nodes to the graph

            workflow.add_node("indexer", index_video_node)
            workflow.add_node("auditor", audit_content_node)
            # 3. Define Edges to establish the flow of execution
            workflow.set_entry_point("indexer")
            workflow.add_edge("indexer", "auditor")
            # connect the auditor node to the END state to signify completion
            workflow.add_edge("auditor", END)

            # compile the graph
            app = workflow.compile()
            return app

# Expose the runnable app for import by the API or CLI
app = create_graph()
# Step 1 - Video Indexer
# Step 2 - Compliance Auditor
# Final Compliance report Generation

import os
import json
import logging
import re # adding regex for cleaning
from typing import Dict, Any, List
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

# Import the state schema for the graph
from backend.src.graph.state import VideoAuditState, ComplianceIssue

# import the service for video ingestion and analysis
from backend.src.services.video_indexer import VideoIndexerService

# Configure logging
logger = logging.getLogger("brand-guardian")
logging.basicConfig(level=logging.INFO)


# ----NODE 1 : The Indexer -----

def index_video_node(state: VideoAuditState) -> Dict[str, Any]:
    """
    Node 1: Video Indexer
    This node is responsible for ingesting the video, extracting metadata, transcript, and OCR text.
    It updates the state with the extracted data.
    """
    video_url = state.get("video_url")
    video_id_input = state.get("video_id", "vid_demo")
    logger.info(f"---[Node: Indexer] Processing: {video_url} ----")
    local_filename = "temp_audit_video.mp4"
    try:
        vi_service = VideoIndexerService()

        # 1. Download the video and save it locally
        if "youtube.com" in video_url or "youtu.be" in video_url:
            local_path = vi_service.download_youtube_video(video_url, output_path=local_filename)
        else:
            raise Exception("Please provide a valid YouTube URL for video ingestion.")
        
        # 2. Upload
        azure_video_id = vi_service.upload_video(local_path, video_name=video_id_input)
        logger.info(f"Video uploaded to Azure Video Indexer with ID: {azure_video_id}")
        # 3. CLEANUP: Remove the local file after upload
        if os.path.exists(local_path):
            os.remove(local_path)
        # WAIT
        raw_insights = vi_service.wait_for_processing(azure_video_id)
        # EXTRACT
        cleaned_data = vi_service.extract_data(raw_insights)
        logger.info(f"---[Node: Indexer] Extraction Complete ----")
        return cleaned_data
    except Exception as e:
        logger.error(f"Error in index_video_node: {str(e)}")
        return {"error": str(e), "video_id": video_id_input, "video_url": video_url,
                "final_status": "failed", "final_report": "", "compliance_results": [], "errors": [str(e)]}
    

#----NODE 2: The Compliance Auditor -----


def audit_content_node(state: VideoAuditState) -> Dict[str, Any]:
    """
    Node 2: Compliance Auditor
    This node is responsible for analyzing the extracted data for compliance issues.
    It updates the state with the compliance results.
    """
    logger.info(f"---[Node: Auditor] querying knowledge base and LLM ----")
    transcript = state.get("transcript", "")
    if not transcript:
        logger.warning("No Transcript available for analysis. Skipping compliance check.")
        return {"final_status": "FAIL",
                "final_report": "Audit skipped because video procssing nailed (No Transcript}."}
    # Initialize the LLM and embeddings
    llm = AzureChatOpenAI(
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        temperature=0.0        
    )
    
    embeddings = AzureOpenAIEmbeddings(
        azure_deployment="text-embedding-3-small",
        openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"))
    
    vector_store = AzureSearch(
        azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        azure_search_key=os.getenv("AZURE_SEARCH_API_KEY"),
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
        embedding_function=embeddings.embed_query
    )
    # RAG - Retrieval Augmented Generation - Retrieval Step
    # 1. Retrieve relevant documents from the vector store based on the transcript
    ocr_text = state.get("ocr_text", [])
    query_text = f"{transcript} {' '.join(ocr_text)}"
    docs = vector_store.similarity_search(query_text, k=3)
    retrieved_rules = "\n\n".join([doc.page_content for doc in docs])

    # UPDATED Prompt Template for Compliance Check - Augmentation step (Enhanced Prompt)
    
    system_prompt = f"""
            You are a Compliance Auditor.

            Your task is to review the provided video transcript and OCR text against the official compliance rules and identify any violations.

            OFFICIAL COMPLIANCE RULES:
            {retrieved_rules}

            Instructions:
            1. Compare the transcript and OCR text with the compliance rules.
            2. Identify every compliance violation.
            3. For each violation, return:
            - category: Compliance category
            - description: Brief explanation of the violation
            - severity: One of "low", "medium", or "high"
            - timestamp: Video timestamp where the violation occurs (if available)
            4. If no violations are found, return an empty JSON array: [].
            5. Return only valid JSON. Do not include markdown, comments, explanations, or any extra text.

            Expected JSON format:
            [
            {{
            "category": "<category>",
            "description": "<description>",
            "severity": "<low|medium|high>",
            "timestamp": "<timestamp or null>"
            }}
            ]
            """
    user_message = f"""
            Video METADATA:{state.get("video_metadata", {})}
            Transcript:
            {transcript}
            ON-SCREEN TEXT (OCR): {ocr_text}
            """
    try:
        response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_message)])

            # FIX ---- Clean Markdown if present ('''---json....''')
        content = response.content
        match = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
        if match:
            content = match.group(1)
        audit_data = json.loads(content.strip())
        return {
            "compliance_results": audit_data,
            "final_status": "success",
            "final_report": "Compliance audit completed successfully."
        }

    except Exception as e:
        logger.error(f"Error in audit_content_node: {str(e)}")
        # Log the raw response to see what went wrong
        logger.error(f"Raw LLM response: {response.content if 'response' in locals() else 'No response'}")
        return {
            "error": str(e), 
            "final_status": "failed", 
            "final_report": "Compliance audit failed due to an error.", 
            "compliance_results": [], 
            "errors": [str(e)]
            }
 
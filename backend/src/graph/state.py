### Central Memory (Graph State)
import operator
from typing import Any, Dict, List, Optional, Annotated, TypedDict
# 1. Define the schema for a single compliance result
# This ensures structral consistancy for every issue dectected by the AI

class ComplianceIssue(TypedDict):
    category: str
    description: str
    severity: str
    timestamp: Optional[str]


# Define the Global Graph state
class VideoAuditState(TypedDict):
    """
    Defines the data schema for the langGraph
    execution context.
    """
    # input parameters
    video_url: str
    video_id: str

    # Ingestion and Extraction Data
    local_file_path: Optional[str]
    video_metadata: Optional[Dict[str, Any]]
    transcript: Optional[str]
    ocr_text: List[str]

    # Analysis outputs

    compliance_results: Annotated[List[ComplianceIssue], operator.add]

    # Final Deliverables
    final_status: str
    final_report: str

    # ---System Observalibility---

    # appends system-level error 

    errors: Annotated[List[str], operator.add]
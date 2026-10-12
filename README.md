# Brand Guardian AI — Video Compliance Audit

A Python-based video compliance auditing prototype that uses **LangGraph**, **Azure Video Indexer**, **Azure OpenAI**, and **Azure AI Search** to compare a video's transcript and on-screen text with a compliance knowledge base. The project exposes both a command-line entry point and a FastAPI endpoint.

> **Project status:** Prototype. It requires Azure resources, credentials, and a configured Azure AI Search index. AI findings are assistive and should be reviewed by a human.

## What it does

1. Accepts a YouTube video URL.
2. Downloads the video locally using `yt-dlp`.
3. Uploads it to Azure Video Indexer and waits for processing.
4. Extracts transcript text, on-screen OCR text, and video metadata.
5. Retrieves relevant compliance guidance from Azure AI Search.
6. Uses an Azure OpenAI chat deployment to identify possible compliance issues.
7. Returns a status, summary, and structured findings.

## Tech stack

- Python 3.12+
- LangGraph and LangChain
- FastAPI and Pydantic
- Azure OpenAI (chat + embeddings)
- Azure AI Search (vector retrieval)
- Azure Video Indexer and Azure Identity
- `yt-dlp`, `requests`, `python-dotenv`
- Azure Monitor OpenTelemetry (optional application telemetry)

## Project structure

```text
GenAIPipeline/
├── main.py                              # CLI workflow entry point
├── pyproject.toml                       # Python project metadata
├── uv.lock                              # uv lock file
├── backend/
│   ├── data/                            # Compliance reference PDFs
│   ├── scripts/
│   │   └── index_documents.py            # Chunks PDFs and indexes them in Azure AI Search
│   └── src/
│       ├── api/
│       │   ├── server.py                 # FastAPI endpoint: POST /audit
│       │   └── telemetry.py              # Azure Monitor telemetry setup
│       ├── graph/
│       │   ├── nodes.py                  # Video indexing and compliance analysis nodes
│       │   ├── state.py                  # Shared LangGraph state schema
│       │   └── workflow.py               # LangGraph workflow definition
│       └── services/
│           └── video_indexer.py           # YouTube download + Azure Video Indexer integration
└── README.md
```

## Prerequisites

- Python 3.12 or newer
- An Azure subscription with configured Azure OpenAI, Azure AI Search, and Azure Video Indexer resources
- An Azure AI Search index compatible with the embedding model and populated with compliance reference material
- Azure authentication configured for `DefaultAzureCredential` (for example, Azure CLI login or an appropriately configured managed identity)

## Setup

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd GenAIPipeline
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

The current `pyproject.toml` does not yet declare the application's runtime dependencies. Until that file is updated, install the packages explicitly:

```bash
python -m pip install --upgrade pip
python -m pip install langgraph langchain-core langchain-openai langchain-community langchain-text-splitters fastapi uvicorn pydantic python-dotenv requests yt-dlp azure-identity azure-monitor-opentelemetry azure-search-documents pypdf
```

For reproducible installs, add and pin the dependencies in `pyproject.toml` and regenerate `uv.lock` before relying on `uv sync`.

### 4. Configure environment variables

Copy `.env.example` to `.env` and replace placeholders with your own values. **Never commit `.env` or real credentials.**

Required settings may include:

```dotenv
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-azure-openai-key>
AZURE_OPENAI_API_VERSION=<your-api-version>
AZURE_OPENAI_CHAT_DEPLOYMENT=<your-chat-deployment-name>
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small

AZURE_SEARCH_ENDPOINT=https://<your-search-service>.search.windows.net
AZURE_SEARCH_API_KEY=<your-search-key>
AZURE_SEARCH_INDEX_NAME=<your-index-name>

AZURE_SUBSCRIPTION_ID=<your-subscription-id>
AZURE_RESOURCE_GROUP=<your-resource-group>
AZURE_VI_ACCOUNT_ID=<your-video-indexer-account-id>
AZURE_VI_LOCATION=<your-video-indexer-location>
AZURE_VI_NAME=<your-video-indexer-resource-name>

# Optional; needed only if Azure Monitor telemetry is enabled
APPLICATIONINSIGHTS_CONNECTION_STRING=<your-connection-string>

# Optional LangSmith tracing, if you add/enable it in the code
LANGCHAIN_API_KEY=<your-langsmith-key>
LANGCHAIN_PROJECT=<your-project-name>
```

The exact required variables depend on the Azure resources and code configuration. The Video Indexer service uses `DefaultAzureCredential`; configure an Azure identity with permission to access the relevant resource. Do not paste credentials into issue reports or commit history.

## Prepare the compliance knowledge base

Place approved PDF reference documents in `backend/data/`. Then run the indexing script from the repository root:

```bash
python -m backend.scripts.index_documents
```

The script loads PDFs, splits their text into overlapping chunks, generates embeddings, and uploads the chunks to Azure AI Search. Verify that the configured index and embedding dimensions match the embedding deployment.

## Run the project

### Command-line workflow

From the repository root:

```bash
python main.py
```

The current CLI entry point includes a sample YouTube URL. Change it to a video you are authorized to process before running it.

### FastAPI service

From the repository root:

```bash
uvicorn backend.src.api.server:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API documentation.

Endpoint: `POST /audit`

Example request:

```json
{
  "video_url": "https://www.youtube.com/watch?v=<video-id>"
}
```

The API returns a session ID, video ID, status, report text, and compliance findings. A full run depends on valid Azure configuration and may take time while the video is downloaded and indexed.

## Workflow architecture

```text
YouTube URL
    |
    v
Indexer node
    |-- Download video with yt-dlp
    |-- Upload and process with Azure Video Indexer
    |-- Extract transcript + OCR + metadata
    v
Auditor node
    |-- Embed/search extracted content in Azure AI Search
    |-- Retrieve relevant compliance rules
    |-- Analyze with Azure OpenAI
    v
Compliance findings + final report
```

The LangGraph is defined in `backend/src/graph/workflow.py`; the state schema is in `backend/src/graph/state.py`; node logic is in `backend/src/graph/nodes.py`.

## Troubleshooting

- **Azure authentication fails:** sign in with the Azure CLI or configure an identity supported by `DefaultAzureCredential`, and verify resource permissions.
- **Missing environment variables:** check the variable names in `.env.example` against the code and ensure `.env` is in the repository root where the process is launched.
- **No compliance rules are retrieved:** verify the Azure AI Search endpoint, index name, API key, indexed documents, and embedding model compatibility.
- **Video Indexer processing fails:** verify the account/resource identifiers, location, RBAC permissions, video URL, network access, and service limits.
- **Import/dependency errors:** activate the virtual environment and install the dependencies listed above.
- **API docs do not load:** ensure the server started successfully and visit `http://127.0.0.1:8000/docs`.

## Security and responsible use

- Keep `.env`, keys, connection strings, and tokens out of Git.
- Review reference PDFs and other assets for licensing or confidential content before publishing.
- Only process videos you have permission to access and analyze.
- Treat generated compliance findings as suggestions, not definitive legal advice; have a qualified person review important decisions.

## Future improvements

- Declare and pin all dependencies in `pyproject.toml`.
- Add automated tests and sample non-sensitive fixtures.
- Make the sample video URL configurable through CLI/API input only.
- Add timeouts/retries and cleanup handling around downloads and Video Indexer polling.
- Improve structured output validation and report formatting.

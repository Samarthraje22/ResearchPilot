import json
import os
import sys
import time
import re
import asyncio
import tempfile
from typing import AsyncGenerator, List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Ensure repository root is in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.rag.pipeline import ResearchRAG
from core.workflow.engine import ResearchWorkflow
from core.sources.user_source_manager import UserSourceManager
from core.sources.topic_discovery import TopicDiscoveryEngine
from core.sources.arxiv_source import ArxivSource
from api.schemas import (
    ResearchQueryRequest,
    ResearchWorkflowResponse,
    PDFUploadResponse,
    DocumentMetadataSchema,
    DocumentListResponse,
    DocumentSelectRequest,
    SuggestedQuestionsResponse,
    RelatedPapersResponse,
    APIErrorResponse,
    FollowUpRequest,
    FollowUpResponse
)
from core.llm.router import LLMRouter

# Directory Setup (Use /tmp on Vercel/serverless where root filesystem is read-only)
IS_SERVERLESS = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
if IS_SERVERLESS:
    UPLOADS_DIR = os.path.join(tempfile.gettempdir(), "researchpilot", "uploads")
    PAPERS_DIR = os.path.join(tempfile.gettempdir(), "researchpilot", "papers")
else:
    UPLOADS_DIR = os.path.join(REPO_ROOT, "data", "uploads")
    PAPERS_DIR = os.path.join(REPO_ROOT, "data", "papers")

FRONTEND_DIR = os.path.join(REPO_ROOT, "frontend")

try:
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    os.makedirs(PAPERS_DIR, exist_ok=True)
except Exception:
    UPLOADS_DIR = os.path.join(tempfile.gettempdir(), "researchpilot", "uploads")
    PAPERS_DIR = os.path.join(tempfile.gettempdir(), "researchpilot", "papers")
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    os.makedirs(PAPERS_DIR, exist_ok=True)

user_source_manager = UserSourceManager(uploads_dir=UPLOADS_DIR)
topic_discovery_engine = TopicDiscoveryEngine()

# Initialize FastAPI App
app = FastAPI(
    title="ResearchPilot API",
    description="Bounded Multi-Step Autonomous AI Research Platform",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy RAG Singleton Instance
rag_instance = None


def get_rag_instance() -> ResearchRAG:
    global rag_instance
    if rag_instance is None:
        print("[API] Initializing ResearchRAG engine and embedding models...", flush=True)
        rag_instance = ResearchRAG()

        # Ingest any existing user uploaded PDFs
        for pdf_path in user_source_manager.get_selected_filepaths():
            try:
                rag_instance.ingest_pdf(pdf_path)
            except Exception as e:
                print(f"[API Warning] Could not ingest {pdf_path}: {e}")
    return rag_instance


def get_workflow_instance(sufficiency_threshold: float = 0.35) -> ResearchWorkflow:
    rag = get_rag_instance()
    return ResearchWorkflow(
        rag=rag,
        max_sub_questions=3,
        max_searches_per_sq=2,
        max_docs_per_sq=2,
        max_synthesis_chunks=8,
        recent_years_window=3,
        current_year=2026,
        sufficiency_threshold=sufficiency_threshold
    )


def sanitize_claim_status(status_str: str) -> str:
    """Sanitize claim statuses to professional uppercase text badges without emojis"""
    s_lower = status_str.lower()
    if "partially" in s_lower:
        return "PARTIALLY SUPPORTED"
    elif "unsupported" in s_lower:
        return "UNSUPPORTED"
    elif "supported" in s_lower:
        return "SUPPORTED"
    return "UNSUPPORTED"


def sanitize_workflow_result(res: dict) -> dict:
    """Format workflow output dictionary into strict schema compliant dictionary"""
    if not isinstance(res, dict):
        res = {}

    ver_rep = res.get("verification_report") or {}
    sanitized_claims = []
    for c in (ver_rep.get("claims") or []):
        if isinstance(c, dict):
            sanitized_claims.append({
                "claim": str(c.get("claim") or ""),
                "status": sanitize_claim_status(c.get("status") or ""),
                "matched_citation_id": c.get("matched_citation_id"),
                "best_overlap": float(c.get("best_overlap") or 0.0)
            })

    sanitized_evidence = []
    for e in (res.get("evidence") or []):
        if isinstance(e, dict):
            sanitized_evidence.append({
                "source": str(e.get("source") or "Unknown Source"),
                "published_year": e.get("published_year"),
                "page": int(e.get("page")) if e.get("page") is not None else 1,
                "section": str(e.get("section") or "Abstract"),
                "chunk_id": str(e.get("chunk_id") or ""),
                "content": str(e.get("content") or ""),
                "score": float(e.get("score") or 0.0),
                "citation_id": int(e.get("citation_id") or 1)
            })

    sources = []
    for s in (res.get("sources") or []):
        if isinstance(s, str):
            sources.append(s)
        elif hasattr(s, "source"):
            sources.append(str(getattr(s, "source")))

    return {
        "topic": str(res.get("topic") or ""),
        "execution_time_sec": float(res.get("execution_time_sec") or 0.0),
        "is_evidence_sufficient": bool(res.get("is_evidence_sufficient", True)),
        "sufficiency_details": res.get("sufficiency_details") or {},
        "report": str(res.get("report") or ""),
        "verification_report": {
            "total_claims": int(ver_rep.get("total_claims") or 0),
            "supported_count": int(ver_rep.get("supported_count") or 0),
            "partially_supported_count": int(ver_rep.get("partially_supported_count") or 0),
            "unsupported_count": int(ver_rep.get("unsupported_count") or 0),
            "groundedness_score": float(ver_rep.get("groundedness_score") or 1.0),
            "claims": sanitized_claims
        },
        "evidence": sanitized_evidence,
        "sources": sources,
        "total_llm_calls": int(res.get("total_llm_calls") or 1),
        "llm_calls_by_stage": res.get("llm_calls_by_stage") or {},
        "stage_latencies_sec": res.get("stage_latencies_sec") or {}
    }


def validate_research_request(query: str, selected_sources: List[str]):
    clean_q = query.strip() if query else ""
    has_pdf = len(selected_sources) > 0
    has_q = len(clean_q) >= 3

    if not has_pdf and not has_q:
        raise HTTPException(status_code=400, detail="A research document and research question are required.")
    if not has_pdf:
        raise HTTPException(status_code=400, detail="Please upload a research document before starting the analysis.")
    if not has_q:
        raise HTTPException(status_code=400, detail="Please enter a research question before starting the analysis.")


@app.get("/api/health", tags=["System"])
def health_check():
    return {"status": "ok", "service": "ResearchPilot API", "version": "1.0.0"}


@app.get("/api/sources", response_model=DocumentListResponse, tags=["Sources"])
def list_user_sources():
    """List all uploaded user documents and their selection status"""
    docs = user_source_manager.list_documents()
    return {"documents": docs}


@app.get("/api/sources/{document_id}/suggested-questions", response_model=SuggestedQuestionsResponse, tags=["Sources"])
def get_suggested_questions(document_id: str):
    """Generate 3-4 document-aware suggested questions for a specific uploaded document"""
    docs = user_source_manager.list_documents()
    match_doc = next((d for d in docs if d["id"] == document_id), None)
    if not match_doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    questions = user_source_manager.get_suggested_questions(document_id)
    return {
        "document_id": document_id,
        "filename": match_doc["filename"],
        "suggested_questions": questions
    }


@app.get("/api/sources/{document_id}/related-papers", response_model=RelatedPapersResponse, tags=["Sources"])
def get_related_papers(document_id: str):
    """Discover real academic papers from arXiv relevant to the uploaded document's topic profile."""
    docs = user_source_manager.list_documents()
    match_doc = next((d for d in docs if d["id"] == document_id), None)
    if not match_doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    filepath = match_doc["filepath"]
    profile = topic_discovery_engine.extract_topic_profile(filepath)
    related = topic_discovery_engine.discover_related_papers(filepath, min_relevance=0.15, max_results=5)

    return {
        "document_id": document_id,
        "document_title": profile["title"],
        "topic_profile": profile,
        "related_papers": related
    }


@app.post("/api/sources/ingest-related", tags=["Sources"])
def ingest_selected_related_papers(arxiv_ids: List[str]):
    """Ingest selected related arXiv papers into the active RAG vector index."""
    rag = get_rag_instance()
    arxiv_source = ArxivSource()
    total_ingested = 0

    for aid in arxiv_ids:
        docs = arxiv_source.fetch(aid, max_results=1)
        if docs:
            rag._index_documents(docs, source_key=aid)
            total_ingested += len(docs)

    return {"status": "ok", "ingested_count": total_ingested}


@app.post("/api/sources/select", tags=["Sources"])
def update_selected_sources(req: DocumentSelectRequest):
    """Update active user document selections"""
    user_source_manager.set_selection(req.selected_ids)
    return {"status": "ok", "selected_ids": req.selected_ids}


@app.delete("/api/sources/{document_id}", tags=["Sources"])
def delete_user_source(document_id: str):
    """Delete uploaded PDF document and remove from active corpus"""
    success = user_source_manager.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"status": "ok", "message": "Document successfully deleted."}


@app.post("/api/sources/reset", tags=["Sources"])
def reset_user_sources():
    """Reset session state and clear all uploaded user documents"""
    user_source_manager.reset_all()
    global rag_instance
    rag_instance = None
    return {"status": "ok", "message": "All uploaded documents and session data cleared."}


@app.post("/api/research/query", response_model=ResearchWorkflowResponse, tags=["Research"])
def execute_research_query(req: ResearchQueryRequest):
    """
    Synchronously execute a bounded multi-step research workflow on selected user documents.
    """
    selected_filepaths = user_source_manager.get_selected_filepaths()
    validate_research_request(req.query, selected_filepaths)

    query_text = req.query.strip()
    if len(query_text) > 1000:
        raise HTTPException(status_code=400, detail="Research query exceeds maximum length of 1000 characters.")

    try:
        wf = get_workflow_instance(sufficiency_threshold=req.sufficiency_threshold)
        raw_res = wf.run(query_text, auto_ingest_arxiv=req.auto_ingest_arxiv, selected_sources=selected_filepaths)
        return sanitize_workflow_result(raw_res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research workflow execution failed: {str(e)}")


@app.post("/api/research/follow-up", response_model=FollowUpResponse, tags=["Research"])
def execute_follow_up_query(req: FollowUpRequest):
    """
    Execute an interactive follow-up question on an existing research report and evidence context.
    """
    query_text = req.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Follow-up query cannot be empty.")

    start_t = time.time()
    
    # Build Evidence Snippet
    evidence_lines = []
    if req.evidence:
        for ev in req.evidence[:8]:
            cid = ev.get("citation_id", "?")
            src = ev.get("source", "Doc")
            pg = ev.get("page", 1)
            content = ev.get("content", "")[:350]
            evidence_lines.append(f"[{cid}] ({src}, p.{pg}): {content}")
    
    evidence_text = "\n".join(evidence_lines) if evidence_lines else "No specific chunk metadata provided."

    # Build Chat History
    history_lines = []
    if req.chat_history:
        for msg in req.chat_history[-6:]:
            role = "User" if msg.role == "user" else "Assistant"
            history_lines.append(f"{role}: {msg.content}")
    history_context = "\n--- CONVERSATION HISTORY ---\n" + "\n".join(history_lines) + "\n--- END HISTORY ---\n" if history_lines else ""

    prompt = (
        f"You are ResearchPilot, an expert AI scientific research assistant.\n"
        f"You are answering a specific follow-up question regarding a synthesized research report.\n\n"
        f"--- RESEARCH REPORT CONTEXT ---\n{req.current_report[:2500]}\n--- END REPORT ---\n\n"
        f"--- AVAILABLE EVIDENCE CONTEXT ---\n{evidence_text}\n--- END EVIDENCE ---\n"
        f"{history_context}\n"
        f"Follow-up Question: {query_text}\n\n"
        f"Instructions:\n"
        f"1. Provide a direct, concise, factual, and helpful answer in 2-4 well-structured paragraphs.\n"
        f"2. Cite evidence using standard notation like [1], [2] when referencing facts from the evidence context.\n"
        f"3. Do NOT make ungrounded claims outside the provided context."
    )

    try:
        llm = LLMRouter()
        answer = llm.generate(prompt)
        if not answer:
            answer = "I was unable to generate a response for this follow-up question based on the provided context."

        # Extract citation numbers
        citations_found = [int(m) for m in re.findall(r'\[(\d+)\]', answer)]
        unique_citations = sorted(list(set(citations_found)))

        return {
            "answer": answer,
            "citations_used": unique_citations,
            "execution_time_sec": round(time.time() - start_t, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Follow-up generation failed: {str(e)}")


@app.get("/api/research/stream", tags=["Research"])
async def stream_research_query(
    query: str = Query(""),
    auto_ingest_arxiv: bool = Query(True),
    sufficiency_threshold: float = Query(0.35)
):
    """
    Stream stage-by-stage progress events via Server-Sent Events (SSE).
    """
    selected_filepaths = user_source_manager.get_selected_filepaths()
    validate_research_request(query, selected_filepaths)

    async def event_generator() -> AsyncGenerator[str, None]:
        def send_sse(event_type: str, data: dict) -> str:
            return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

        try:
            yield send_sse("stage", {"stage": "planning", "message": "Decomposing research topic into sub-questions..."})
            await asyncio.sleep(0.1)

            yield send_sse("stage", {"stage": "discovery", "message": "Discovering primary sources across arXiv & selected documents..."})
            await asyncio.sleep(0.1)

            yield send_sse("stage", {"stage": "retrieval", "message": "Collecting and deduplicating sub-question evidence chunks..."})
            await asyncio.sleep(0.1)

            yield send_sse("stage", {"stage": "gate", "message": "Evaluating evidence check..."})
            await asyncio.sleep(0.1)

            loop = asyncio.get_event_loop()
            wf = get_workflow_instance(sufficiency_threshold=sufficiency_threshold)
            raw_res = await loop.run_in_executor(
                None, wf.run, query.strip(), auto_ingest_arxiv, selected_filepaths
            )
            sanitized = sanitize_workflow_result(raw_res)

            if not sanitized["is_evidence_sufficient"]:
                yield send_sse("stage", {"stage": "gated", "message": "Not enough evidence detected. Skipping speculative synthesis."})
            else:
                yield send_sse("stage", {"stage": "synthesis", "message": "Synthesizing evidence-first research report..."})
                yield send_sse("stage", {"stage": "verification", "message": "Auditing and verifying claim groundedness..."})

            yield send_sse("completed", sanitized)

        except asyncio.CancelledError:
            print("[SSE] Client disconnected from research stream.")
        except Exception as e:
            import traceback
            print(f"[SSE Error Traceback]\n{traceback.format_exc()}")
            yield send_sse("workflow_error", {"error": "Workflow Execution Failed", "detail": str(e)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/sources/upload", response_model=PDFUploadResponse, tags=["Sources"])
async def upload_pdf_source(file: UploadFile = File(...)):
    """
    Upload custom PDF document into isolated data/uploads/ directory and ingest into vector index.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files (.pdf) are supported.")

    file_bytes = await file.read()
    if len(file_bytes) > 15 * 1024 * 1024:  # 15MB max limit
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed limit of 15MB.")

    filename = os.path.basename(file.filename)
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    target_path = os.path.join(UPLOADS_DIR, filename)

    try:
        with open(target_path, "wb") as f:
            f.write(file_bytes)

        # Ingest PDF into RAG engine
        chunks_created = get_rag_instance().ingest_pdf(target_path)
        doc_id = user_source_manager.get_document_id(target_path)
        user_source_manager.selection_state[doc_id] = True

        return {
            "filename": filename,
            "file_path": target_path,
            "chunks_created": chunks_created,
            "message": f"Successfully uploaded and indexed {filename}."
        }
    except Exception as e:
        import traceback
        print(f"[Upload Error] {traceback.format_exc()}", flush=True)
        raise HTTPException(status_code=500, detail=f"Failed to process PDF upload: {str(e)}")


@app.get("/api/eval/benchmark", tags=["Benchmark"])
def get_benchmark_results():
    """
    Read-only endpoint returning current quantitative evaluation results.
    """
    results_path = os.path.join(REPO_ROOT, "eval", "results.json")
    if not os.path.exists(results_path):
        raise HTTPException(status_code=404, detail="Benchmark results file (eval/results.json) not found.")

    try:
        with open(results_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read benchmark results: {str(e)}")


# Serve static web frontend
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def serve_index():
        index_file = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return JSONResponse({"message": "ResearchPilot Backend Ready. Static index.html not found."})

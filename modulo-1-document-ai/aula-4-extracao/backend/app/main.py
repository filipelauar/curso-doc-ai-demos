import asyncio
import logging
from datetime import datetime
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

# O .env fica na raiz do repositorio (o mesmo de todas as demos)
load_dotenv(find_dotenv(), override=False)

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .models import (
    SchemaConfig,
    SchemaCreate,
    SchemaUpdate,
    DocumentMeta,
    ExtractionResult,
    TextDocumentInput,
    generate_id,
)
from .storage import (
    list_schemas,
    get_schema,
    save_schema,
    delete_schema as delete_schema_storage,
    list_documents,
    get_document_meta,
    save_document_meta,
    get_document_path,
    delete_document as delete_document_storage,
    get_extraction,
    save_extraction,
    list_extractions,
    clear_extractions,
    ensure_dirs,
)
from .extraction import extract_document
from .pdf_utils import text_to_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Document Extractor MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    ensure_dirs()


# --- Schema Endpoints ---


@app.get("/api/schemas")
async def api_list_schemas():
    schemas = list_schemas()
    return [s.model_dump() for s in schemas]


@app.post("/api/schemas")
async def api_create_schema(data: SchemaCreate):
    defaults = SchemaConfig(name=data.name)
    if data.json_schema is not None:
        defaults.json_schema = data.json_schema
    if data.system_prompt is not None:
        defaults.system_prompt = data.system_prompt
    if data.prompt is not None:
        defaults.prompt = data.prompt
    if data.model is not None:
        defaults.model = data.model
    if data.reasoning_effort is not None:
        defaults.reasoning_effort = data.reasoning_effort
    schema = save_schema(defaults)
    return schema.model_dump()


@app.get("/api/schemas/{schema_id}")
async def api_get_schema(schema_id: str):
    schema = get_schema(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
    return schema.model_dump()


@app.put("/api/schemas/{schema_id}")
async def api_update_schema(schema_id: str, data: SchemaUpdate):
    schema = get_schema(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    if data.name is not None:
        schema.name = data.name
    if data.json_schema is not None:
        schema.json_schema = data.json_schema
    if data.system_prompt is not None:
        schema.system_prompt = data.system_prompt
    if data.prompt is not None:
        schema.prompt = data.prompt
    if data.model is not None:
        schema.model = data.model
    if data.reasoning_effort is not None:
        schema.reasoning_effort = data.reasoning_effort

    schema.updated_at = datetime.now().isoformat()
    save_schema(schema)
    return schema.model_dump()


@app.delete("/api/schemas/{schema_id}")
async def api_delete_schema(schema_id: str):
    deleted = delete_schema_storage(schema_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Schema not found")
    return {"ok": True}


# --- Document Endpoints ---


@app.get("/api/schemas/{schema_id}/documents")
async def api_list_documents(schema_id: str):
    schema = get_schema(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
    docs = list_documents(schema_id)
    return [d.model_dump() for d in docs]


@app.post("/api/schemas/{schema_id}/documents")
async def api_upload_document(
    schema_id: str,
    file: UploadFile = File(...),
    name: str = Form(None),
):
    schema = get_schema(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    doc_id = generate_id()
    doc_name = name or file.filename or f"document_{doc_id}"

    # Save the PDF file
    pdf_path = get_document_path(schema_id, doc_id)
    content = await file.read()
    pdf_path.write_bytes(content)

    # Save metadata
    meta = DocumentMeta(id=doc_id, name=doc_name, original_type="pdf")
    save_document_meta(schema_id, meta)

    return meta.model_dump()


@app.post("/api/schemas/{schema_id}/documents/text")
async def api_add_text_document(schema_id: str, data: TextDocumentInput):
    schema = get_schema(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    doc_id = generate_id()
    pdf_path = get_document_path(schema_id, doc_id)

    # Convert text to PDF
    text_to_pdf(data.text, str(pdf_path))

    # Save metadata
    meta = DocumentMeta(id=doc_id, name=data.name, original_type="text")
    save_document_meta(schema_id, meta)

    return meta.model_dump()


@app.get("/api/schemas/{schema_id}/documents/{doc_id}/file")
async def api_get_document_file(schema_id: str, doc_id: str):
    pdf_path = get_document_path(schema_id, doc_id)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found")
    return FileResponse(str(pdf_path), media_type="application/pdf")


@app.delete("/api/schemas/{schema_id}/documents/{doc_id}")
async def api_delete_document(schema_id: str, doc_id: str):
    deleted = delete_document_storage(schema_id, doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"ok": True}


# --- Extraction Endpoints ---


@app.post("/api/schemas/{schema_id}/extract")
async def api_run_extraction(schema_id: str):
    schema = get_schema(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")

    docs = list_documents(schema_id)
    if not docs:
        raise HTTPException(status_code=400, detail="No documents to extract from")

    # Validate JSON schema has properties
    if not schema.json_schema.get("properties"):
        raise HTTPException(
            status_code=400,
            detail="JSON schema must have at least one property defined",
        )

    # Clear old extractions
    clear_extractions(schema_id)

    # Extract from all documents concurrently
    results = []

    async def process_doc(doc: DocumentMeta):
        pdf_path = str(get_document_path(schema_id, doc.id))
        try:
            result = await extract_document(
                pdf_path=pdf_path,
                json_schema=schema.json_schema,
                system_prompt=schema.system_prompt,
                prompt=schema.prompt,
                model=schema.model,
                reasoning_effort=schema.reasoning_effort,
            )
            extraction = ExtractionResult(
                document_id=doc.id,
                result=result,
                status="success",
            )
        except Exception as e:
            logger.error(f"Extraction failed for doc {doc.id}: {e}")
            extraction = ExtractionResult(
                document_id=doc.id,
                result=None,
                status="error",
                error=str(e),
            )
        save_extraction(schema_id, extraction)
        return extraction

    tasks = [process_doc(doc) for doc in docs]
    extractions = await asyncio.gather(*tasks)

    return [e.model_dump() for e in extractions]


@app.get("/api/schemas/{schema_id}/extractions")
async def api_list_extractions(schema_id: str):
    schema = get_schema(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
    extractions = list_extractions(schema_id)
    return [e.model_dump() for e in extractions]


@app.get("/api/schemas/{schema_id}/extractions/{doc_id}")
async def api_get_extraction(schema_id: str, doc_id: str):
    extraction = get_extraction(schema_id, doc_id)
    if not extraction:
        raise HTTPException(status_code=404, detail="Extraction not found")
    return extraction.model_dump()

import json
import os
import shutil
from pathlib import Path
from .models import SchemaConfig, DocumentMeta, ExtractionResult

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def ensure_dirs():
    """Ensure the data directory structure exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "schemas").mkdir(exist_ok=True)


def schema_dir(schema_id: str) -> Path:
    return DATA_DIR / "schemas" / schema_id


def documents_dir(schema_id: str) -> Path:
    d = schema_dir(schema_id) / "documents"
    d.mkdir(parents=True, exist_ok=True)
    return d


def extractions_dir(schema_id: str) -> Path:
    d = schema_dir(schema_id) / "extractions"
    d.mkdir(parents=True, exist_ok=True)
    return d


# --- Schema CRUD ---

def list_schemas() -> list[SchemaConfig]:
    ensure_dirs()
    schemas = []
    schemas_root = DATA_DIR / "schemas"
    if not schemas_root.exists():
        return schemas
    for d in sorted(schemas_root.iterdir()):
        config_path = d / "config.json"
        if config_path.exists():
            data = json.loads(config_path.read_text(encoding="utf-8"))
            schemas.append(SchemaConfig(**data))
    return schemas


def get_schema(schema_id: str) -> SchemaConfig | None:
    config_path = schema_dir(schema_id) / "config.json"
    if not config_path.exists():
        return None
    data = json.loads(config_path.read_text(encoding="utf-8"))
    return SchemaConfig(**data)


def save_schema(schema: SchemaConfig) -> SchemaConfig:
    d = schema_dir(schema.id)
    d.mkdir(parents=True, exist_ok=True)
    config_path = d / "config.json"
    config_path.write_text(schema.model_dump_json(indent=2), encoding="utf-8")
    return schema


def delete_schema(schema_id: str) -> bool:
    d = schema_dir(schema_id)
    if d.exists():
        shutil.rmtree(d)
        return True
    return False


# --- Document CRUD ---

def list_documents(schema_id: str) -> list[DocumentMeta]:
    docs = []
    d = documents_dir(schema_id)
    for f in sorted(d.iterdir()):
        if f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            docs.append(DocumentMeta(**data))
    return docs


def get_document_meta(schema_id: str, doc_id: str) -> DocumentMeta | None:
    meta_path = documents_dir(schema_id) / f"{doc_id}.json"
    if not meta_path.exists():
        return None
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    return DocumentMeta(**data)


def save_document_meta(schema_id: str, meta: DocumentMeta):
    meta_path = documents_dir(schema_id) / f"{meta.id}.json"
    meta_path.write_text(meta.model_dump_json(indent=2), encoding="utf-8")


def get_document_path(schema_id: str, doc_id: str) -> Path:
    return documents_dir(schema_id) / f"{doc_id}.pdf"


def delete_document(schema_id: str, doc_id: str) -> bool:
    pdf_path = get_document_path(schema_id, doc_id)
    meta_path = documents_dir(schema_id) / f"{doc_id}.json"
    deleted = False
    if pdf_path.exists():
        pdf_path.unlink()
        deleted = True
    if meta_path.exists():
        meta_path.unlink()
        deleted = True
    # Also delete extraction
    ext_path = extractions_dir(schema_id) / f"{doc_id}.json"
    if ext_path.exists():
        ext_path.unlink()
    return deleted


# --- Extraction CRUD ---

def get_extraction(schema_id: str, doc_id: str) -> ExtractionResult | None:
    ext_path = extractions_dir(schema_id) / f"{doc_id}.json"
    if not ext_path.exists():
        return None
    data = json.loads(ext_path.read_text(encoding="utf-8"))
    return ExtractionResult(**data)


def save_extraction(schema_id: str, extraction: ExtractionResult):
    ext_path = extractions_dir(schema_id) / f"{extraction.document_id}.json"
    ext_path.write_text(extraction.model_dump_json(indent=2), encoding="utf-8")


def list_extractions(schema_id: str) -> list[ExtractionResult]:
    results = []
    d = extractions_dir(schema_id)
    for f in sorted(d.iterdir()):
        if f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            results.append(ExtractionResult(**data))
    return results


def clear_extractions(schema_id: str):
    d = extractions_dir(schema_id)
    if d.exists():
        for f in d.iterdir():
            if f.suffix == ".json":
                f.unlink()

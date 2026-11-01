from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime
import uuid


def generate_id() -> str:
    return uuid.uuid4().hex[:12]


class SchemaConfig(BaseModel):
    id: str = Field(default_factory=generate_id)
    name: str
    json_schema: dict[str, Any] = Field(default_factory=lambda: {
        "type": "object",
        "properties": {},
    })
    system_prompt: str = (
        "Você é um assistente especializado em extração de informações de documentos. "
        "Sua tarefa é analisar cuidadosamente o documento fornecido e extrair as informações "
        "solicitadas de forma precisa e completa.\n\n"
        "Para cada campo solicitado, você deve:\n"
        "1. Extrair o valor correto do documento\n"
        "2. Indicar o número da página (começando em 1) onde a informação foi encontrada\n"
        "3. Fornecer a transcrição exata do trecho do documento que contém a informação\n\n"
        "Regras importantes:\n"
        "- Seja preciso e fiel ao conteúdo do documento\n"
        "- A transcrição deve ser o trecho exato do texto original, sem modificações\n"
        "- Se uma informação não for encontrada no documento, retorne null para o valor, "
        "null para a página e null para a transcrição\n"
        "- O número da página deve corresponder à página real do documento onde a informação aparece"
    )
    prompt: str = (
        "Analise o documento a seguir e extraia todas as informações conforme o esquema definido.\n\n"
        "Para cada campo, forneça:\n"
        "- O valor extraído\n"
        "- O número da página onde a informação foi encontrada\n"
        "- A transcrição exata do trecho relevante do documento\n\n"
        "Documento:\n{document_text}"
    )
    model: str = "gpt-6-luna"
    reasoning_effort: str | None = "low"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class SchemaCreate(BaseModel):
    name: str
    json_schema: dict[str, Any] | None = None
    system_prompt: str | None = None
    prompt: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None


class SchemaUpdate(BaseModel):
    name: str | None = None
    json_schema: dict[str, Any] | None = None
    system_prompt: str | None = None
    prompt: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None


class DocumentMeta(BaseModel):
    id: str = Field(default_factory=generate_id)
    name: str
    original_type: str = "pdf"  # "pdf" or "text"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float
    page: int


class ExtractionResult(BaseModel):
    document_id: str
    result: dict[str, Any] | None = None
    status: str = "pending"  # "success", "error", "pending"
    error: str | None = None
    extracted_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class TextDocumentInput(BaseModel):
    name: str
    text: str

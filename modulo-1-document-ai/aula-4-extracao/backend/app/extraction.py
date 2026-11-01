import copy
import json
import logging
from typing import Any

from openai import AsyncOpenAI

from .pdf_utils import (
    extract_text_from_pdf,
    find_text_bounding_box,
    format_document_text,
)

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client


PRIMITIVE_TYPES = {"string", "number", "integer", "boolean"}


def augment_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Transform a JSON schema to include source fields (page, transcription)
    for each primitive property. Ensures OpenAI strict mode compatibility."""
    schema = copy.deepcopy(schema)
    return _augment_node(schema)


def _augment_node(node: dict[str, Any]) -> dict[str, Any]:
    node_type = node.get("type")

    # Auto-detect object type if properties exist but type is missing
    if node_type is None and "properties" in node:
        node["type"] = "object"
        node_type = "object"

    # Auto-detect array type if items exist but type is missing
    if node_type is None and "items" in node:
        node["type"] = "array"
        node_type = "array"

    # Handle nullable types like ["string", "null"]
    if isinstance(node_type, list):
        non_null = [t for t in node_type if t != "null"]
        if len(non_null) == 1 and non_null[0] in PRIMITIVE_TYPES:
            return _make_sourced_field(node)
        # If it's a complex union, don't augment
        return node

    if node_type in PRIMITIVE_TYPES:
        return _make_sourced_field(node)

    if node_type == "object":
        properties = node.get("properties", {})
        new_properties = {}
        for key, value in properties.items():
            new_properties[key] = _augment_node(value)
        node["properties"] = new_properties
        node["required"] = list(new_properties.keys())
        node["additionalProperties"] = False
        return node

    if node_type == "array":
        items = node.get("items", {})
        node["items"] = _augment_node(items)
        return node

    return node


def _make_sourced_field(original: dict[str, Any]) -> dict[str, Any]:
    """Wrap a primitive field with value/page/transcription for source tracking."""
    original_type = original.get("type")

    # Build the value schema - always make nullable
    value_schema: dict[str, Any] = {}
    if isinstance(original_type, list):
        value_schema["type"] = original_type if "null" in original_type else original_type + ["null"]
    else:
        value_schema["type"] = [original_type, "null"]

    # Preserve enum if present
    if "enum" in original:
        enum_values = list(original["enum"])
        if None not in enum_values:
            enum_values.append(None)
        value_schema["enum"] = enum_values

    if "description" in original:
        value_schema["description"] = original["description"]

    return {
        "type": "object",
        "description": original.get("description", ""),
        "properties": {
            "value": value_schema,
            "page": {
                "type": ["integer", "null"],
                "description": "Número da página (começando em 1) onde a informação foi encontrada",
            },
            "transcription": {
                "type": ["string", "null"],
                "description": "Transcrição exata do trecho do documento que contém esta informação",
            },
        },
        "required": ["value", "page", "transcription"],
        "additionalProperties": False,
    }


async def call_openai(
    system_prompt: str,
    user_prompt: str,
    augmented_schema: dict[str, Any],
    model: str = "gpt-6-luna",
    reasoning_effort: str | None = "low",
) -> dict[str, Any]:
    """Call OpenAI with structured output to extract information."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "extraction_result",
            "strict": True,
            "schema": augmented_schema,
        },
    }

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "response_format": response_format,
    }

    # Add reasoning_effort for models that support it
    if reasoning_effort and reasoning_effort != "none":
        kwargs["reasoning_effort"] = reasoning_effort

    response = await _get_client().chat.completions.create(**kwargs)
    content = response.choices[0].message.content

    if content is None:
        raise ValueError("Empty response from OpenAI")

    return json.loads(content)


def compute_bounding_boxes(
    result: dict[str, Any], pdf_path: str
) -> dict[str, Any]:
    """Recursively compute bounding boxes for all sourced fields in the extraction result."""
    result = copy.deepcopy(result)
    _process_bounding_boxes(result, pdf_path)
    return result


def _process_bounding_boxes(obj: Any, pdf_path: str):
    """Recursively walk the extraction result and compute bounding boxes."""
    if isinstance(obj, dict):
        if _is_sourced_field(obj):
            page = obj.get("page")
            transcription = obj.get("transcription")
            if page and transcription:
                bbox = find_text_bounding_box(pdf_path, page, transcription)
                obj["bounding_box"] = bbox
            else:
                obj["bounding_box"] = None
        else:
            for value in obj.values():
                _process_bounding_boxes(value, pdf_path)
    elif isinstance(obj, list):
        for item in obj:
            _process_bounding_boxes(item, pdf_path)


def _is_sourced_field(obj: dict) -> bool:
    """Check if a dict is a sourced field (has value, page, transcription)."""
    return (
        isinstance(obj, dict)
        and "value" in obj
        and "page" in obj
        and "transcription" in obj
    )


async def extract_document(
    pdf_path: str,
    json_schema: dict[str, Any],
    system_prompt: str,
    prompt: str,
    model: str = "gpt-6-luna",
    reasoning_effort: str | None = "low",
) -> dict[str, Any]:
    """Full extraction pipeline for a single document.

    1. Extract text from PDF
    2. Augment schema with source fields
    3. Call OpenAI
    4. Compute bounding boxes

    Returns the enriched extraction result.
    """
    # Extract text
    pages = extract_text_from_pdf(pdf_path)
    document_text = format_document_text(pages)

    # Augment schema
    augmented = augment_schema(json_schema)

    # Format prompt
    user_prompt = prompt.replace("{document_text}", document_text)

    # Call OpenAI
    raw_result = await call_openai(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        augmented_schema=augmented,
        model=model,
        reasoning_effort=reasoning_effort,
    )

    # Compute bounding boxes
    enriched_result = compute_bounding_boxes(raw_result, pdf_path)

    return enriched_result

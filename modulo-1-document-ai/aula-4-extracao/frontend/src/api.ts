import type {
  Schema,
  DocumentMeta,
  ExtractionResult,
} from "./types";

const BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

// --- Schemas ---

export async function fetchSchemas(): Promise<Schema[]> {
  return request("/schemas");
}

export async function fetchSchema(id: string): Promise<Schema> {
  return request(`/schemas/${id}`);
}

export async function createSchema(data: {
  name: string;
}): Promise<Schema> {
  return request("/schemas", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateSchema(
  id: string,
  data: Partial<Schema>
): Promise<Schema> {
  return request(`/schemas/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteSchema(id: string): Promise<void> {
  return request(`/schemas/${id}`, { method: "DELETE" });
}

// --- Documents ---

export async function fetchDocuments(
  schemaId: string
): Promise<DocumentMeta[]> {
  return request(`/schemas/${schemaId}/documents`);
}

export async function uploadDocument(
  schemaId: string,
  file: File,
  name?: string
): Promise<DocumentMeta> {
  const formData = new FormData();
  formData.append("file", file);
  if (name) formData.append("name", name);

  const res = await fetch(`${BASE}/schemas/${schemaId}/documents`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || "Upload failed");
  }
  return res.json();
}

export async function addTextDocument(
  schemaId: string,
  name: string,
  text: string
): Promise<DocumentMeta> {
  return request(`/schemas/${schemaId}/documents/text`, {
    method: "POST",
    body: JSON.stringify({ name, text }),
  });
}

export function getDocumentFileUrl(
  schemaId: string,
  docId: string
): string {
  return `${BASE}/schemas/${schemaId}/documents/${docId}/file`;
}

export async function deleteDocument(
  schemaId: string,
  docId: string
): Promise<void> {
  return request(`/schemas/${schemaId}/documents/${docId}`, {
    method: "DELETE",
  });
}

// --- Extractions ---

export async function runExtraction(
  schemaId: string
): Promise<ExtractionResult[]> {
  return request(`/schemas/${schemaId}/extract`, {
    method: "POST",
  });
}

export async function fetchExtractions(
  schemaId: string
): Promise<ExtractionResult[]> {
  return request(`/schemas/${schemaId}/extractions`);
}

export async function fetchExtraction(
  schemaId: string,
  docId: string
): Promise<ExtractionResult> {
  return request(`/schemas/${schemaId}/extractions/${docId}`);
}

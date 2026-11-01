export interface Schema {
  id: string;
  name: string;
  json_schema: Record<string, unknown>;
  system_prompt: string;
  prompt: string;
  model: string;
  reasoning_effort: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentMeta {
  id: string;
  name: string;
  original_type: "pdf" | "text";
  created_at: string;
}

export interface BoundingBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  page: number;
}

export interface SourcedField {
  value: unknown;
  page: number | null;
  transcription: string | null;
  bounding_box: BoundingBox | null;
}

export interface ExtractionResult {
  document_id: string;
  result: Record<string, unknown> | null;
  status: "success" | "error" | "pending";
  error: string | null;
  extracted_at: string;
}

export interface HighlightSource {
  fieldPath: string;
  page: number;
  boundingBox: BoundingBox;
}

export function isSourcedField(obj: unknown): obj is SourcedField {
  return (
    typeof obj === "object" &&
    obj !== null &&
    "value" in obj &&
    "page" in obj &&
    "transcription" in obj
  );
}

export const MODELS = [
  { id: "gpt-6-luna", name: "GPT-6 Luna", supportsReasoning: true },
  { id: "gpt-5-mini", name: "GPT-5 Mini", supportsReasoning: true },
  { id: "gpt-5.2", name: "GPT-5.2", supportsReasoning: false },
] as const;

export const REASONING_EFFORTS = [
  { id: "none", name: "Nenhum" },
  { id: "low", name: "Mínimo" },
  { id: "medium", name: "Médio" },
  { id: "high", name: "Alto" },
] as const;

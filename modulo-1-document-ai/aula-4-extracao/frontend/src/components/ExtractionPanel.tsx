import {
  ChevronDown,
  ChevronRight,
  AlertCircle,
  FileSearch,
} from "lucide-react";
import { useState } from "react";
import type { ExtractionResult, BoundingBox } from "../types";
import { isSourcedField } from "../types";

interface Props {
  extraction: ExtractionResult | null;
  onSelectField: (highlight: BoundingBox | null) => void;
  selectedHighlight: BoundingBox | null;
}

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  string: { label: "TEXTO", color: "bg-blue-100 text-blue-700" },
  number: { label: "NÚMERO", color: "bg-green-100 text-green-700" },
  integer: { label: "INTEIRO", color: "bg-green-100 text-green-700" },
  boolean: { label: "BOOLEANO", color: "bg-purple-100 text-purple-700" },
  null: { label: "NULO", color: "bg-gray-100 text-gray-500" },
};

function getValueType(value: unknown): string {
  if (value === null || value === undefined) return "null";
  if (typeof value === "boolean") return "boolean";
  if (typeof value === "number") return Number.isInteger(value) ? "integer" : "number";
  return "string";
}

export default function ExtractionPanel({
  extraction,
  onSelectField,
  selectedHighlight,
}: Props) {
  if (!extraction) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center">
          <FileSearch className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500">
            Nenhuma extração disponível
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Execute a extração para ver os resultados
          </p>
        </div>
      </div>
    );
  }

  if (extraction.status === "error") {
    return (
      <div className="p-4">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-medium text-red-800">
                Erro na extração
              </h4>
              <p className="mt-1 text-sm text-red-700 break-words">
                {extraction.error}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!extraction.result) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <p className="text-sm text-gray-500">Resultado vazio</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 bg-white border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900">
          Resultado da Extração
        </h3>
        <p className="text-xs text-gray-500 mt-0.5">
          Clique em um campo para ver a origem no documento
        </p>
      </div>
      <div className="flex-1 overflow-auto p-3 space-y-2">
        <ResultNode
          data={extraction.result}
          path=""
          onSelectField={onSelectField}
          selectedHighlight={selectedHighlight}
        />
      </div>
    </div>
  );
}

// --- Recursive result renderer ---

interface ResultNodeProps {
  data: unknown;
  path: string;
  label?: string;
  onSelectField: (highlight: BoundingBox | null) => void;
  selectedHighlight: BoundingBox | null;
}

function ResultNode({
  data,
  path,
  label,
  onSelectField,
  selectedHighlight,
}: ResultNodeProps) {
  const [expanded, setExpanded] = useState(true);

  if (data === null || data === undefined) {
    return null;
  }

  // Sourced field (leaf with value + page + transcription)
  if (isSourcedField(data)) {
    const bbox = data.bounding_box;
    const isSelected =
      selectedHighlight &&
      bbox &&
      selectedHighlight.x0 === bbox.x0 &&
      selectedHighlight.y0 === bbox.y0 &&
      selectedHighlight.page === bbox.page;

    const valueType = getValueType(data.value);
    const typeInfo = TYPE_LABELS[valueType] || TYPE_LABELS.string;

    return (
      <div
        className={`rounded-lg border bg-white transition-all cursor-pointer ${
          isSelected
            ? "border-indigo-400 ring-2 ring-indigo-200 shadow-sm"
            : "border-gray-200 hover:border-indigo-300 hover:shadow-sm"
        }`}
        onClick={() => {
          if (bbox) {
            onSelectField(isSelected ? null : bbox);
          }
        }}
      >
        {/* Card header */}
        <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100">
          <span className="font-mono text-xs font-semibold text-gray-600 uppercase tracking-wider truncate">
            {label}
          </span>
          <div className="flex items-center gap-1.5 shrink-0">
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-amber-50 text-amber-700">
              Fonte extraída
            </span>
            <span
              className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${typeInfo.color}`}
            >
              {typeInfo.label}
            </span>
          </div>
        </div>

        {/* Card body */}
        <div className="px-3 py-2.5">
          <div className="text-sm font-medium text-gray-900">
            {formatValue(data.value)}
          </div>
          {data.page && (
            <div className="flex items-center gap-2 mt-2">
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500">
                Pág. {data.page}
              </span>
              {data.transcription && (
                <span
                  className="text-[10px] text-gray-400 italic truncate"
                  title={data.transcription}
                >
                  "{data.transcription}"
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Array
  if (Array.isArray(data)) {
    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 text-sm font-medium text-gray-700 mb-1.5
            hover:text-indigo-600 transition-colors"
        >
          {expanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
          <span className="font-mono uppercase text-xs tracking-wider">
            {label || "Lista"}
          </span>
          <span className="text-[10px] text-gray-400 font-normal normal-case tracking-normal">
            ({data.length} itens)
          </span>
        </button>
        {expanded && (
          <div className="ml-3 pl-3 border-l-2 border-gray-100 space-y-2">
            {data.map((item, i) => (
              <ResultNode
                key={i}
                data={item}
                path={`${path}[${i}]`}
                label={`#${i + 1}`}
                onSelectField={onSelectField}
                selectedHighlight={selectedHighlight}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  // Object (non-sourced)
  if (typeof data === "object") {
    const entries = Object.entries(data as Record<string, unknown>);
    return (
      <div>
        {label && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1.5 text-sm font-medium text-gray-700 mb-1.5
              hover:text-indigo-600 transition-colors"
          >
            {expanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
            <span className="font-mono uppercase text-xs tracking-wider">
              {label}
            </span>
          </button>
        )}
        {(label ? expanded : true) && (
          <div
            className={
              label
                ? "ml-3 pl-3 border-l-2 border-gray-100 space-y-2"
                : "space-y-2"
            }
          >
            {entries.map(([key, value]) => (
              <ResultNode
                key={key}
                data={value}
                path={`${path}.${key}`}
                label={key}
                onSelectField={onSelectField}
                selectedHighlight={selectedHighlight}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  // Primitive fallback
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2">
      {label && (
        <span className="font-mono text-xs font-semibold text-gray-600 uppercase tracking-wider">
          {label}
        </span>
      )}
      <div className="text-sm text-gray-900">{formatValue(data)}</div>
    </div>
  );
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Sim" : "Não";
  return String(value);
}

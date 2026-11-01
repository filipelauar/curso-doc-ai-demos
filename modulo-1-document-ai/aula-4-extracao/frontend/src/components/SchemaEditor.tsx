import { useState, useEffect, useCallback } from "react";
import type { Schema } from "../types";
import SchemaVisualEditor from "./SchemaVisualEditor";

interface Props {
  schema: Schema;
  onSave: (jsonSchema: Record<string, unknown>) => void;
}

export default function SchemaEditor({ schema, onSave }: Props) {
  const [tab, setTab] = useState<"visual" | "json">("visual");
  const [jsonText, setJsonText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [localSchema, setLocalSchema] = useState<Record<string, unknown>>(
    schema.json_schema
  );

  // Sync from server when schema changes
  useEffect(() => {
    setLocalSchema(schema.json_schema);
    setJsonText(JSON.stringify(schema.json_schema, null, 2));
    setError(null);
    setIsDirty(false);
  }, [schema.id, schema.json_schema]);

  // --- Visual editor handlers ---
  const handleVisualChange = useCallback(
    (updated: Record<string, unknown>) => {
      setLocalSchema(updated);
      setJsonText(JSON.stringify(updated, null, 2));
      setIsDirty(true);
      setError(null);
    },
    []
  );

  // --- JSON editor handlers ---
  const handleJsonChange = useCallback((value: string) => {
    setJsonText(value);
    setIsDirty(true);
    try {
      const parsed = JSON.parse(value);
      setLocalSchema(parsed);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  const handleSave = useCallback(() => {
    if (error) return;
    onSave(localSchema);
    setIsDirty(false);
  }, [localSchema, error, onSave]);

  const handleFormat = useCallback(() => {
    try {
      const parsed = JSON.parse(jsonText);
      setJsonText(JSON.stringify(parsed, null, 2));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [jsonText]);

  return (
    <div className="flex flex-col h-full">
      {/* Tabs */}
      <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4">
        <div className="flex">
          <button
            onClick={() => setTab("visual")}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === "visual"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            Visual
          </button>
          <button
            onClick={() => setTab("json")}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === "json"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            JSON
          </button>
        </div>

        {/* Save indicator */}
        {isDirty && (
          <div className="flex items-center gap-2">
            {error ? (
              <span className="text-xs text-red-600 truncate max-w-[150px]">
                Erro no JSON
              </span>
            ) : (
              <span className="text-xs text-amber-600">Não salvo</span>
            )}
            <button
              onClick={handleSave}
              disabled={!!error}
              className="rounded-md bg-indigo-600 px-3 py-1 text-xs font-medium text-white
                hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed
                transition-colors"
            >
              Salvar
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {tab === "visual" ? (
          <SchemaVisualEditor
            schema={localSchema}
            onChange={handleVisualChange}
          />
        ) : (
          <div className="flex flex-col h-full">
            {/* JSON toolbar */}
            <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 border-b border-gray-200">
              <button
                onClick={handleFormat}
                className="rounded px-2.5 py-1 text-xs font-medium text-gray-600
                  bg-white border border-gray-300 hover:bg-gray-50 transition-colors"
              >
                Formatar
              </button>
            </div>

            {/* Editor */}
            <textarea
              value={jsonText}
              onChange={(e) => handleJsonChange(e.target.value)}
              className="flex-1 p-4 font-mono text-sm bg-gray-900 text-green-400
                resize-none focus:outline-none"
              spellCheck={false}
            />
          </div>
        )}
      </div>
    </div>
  );
}

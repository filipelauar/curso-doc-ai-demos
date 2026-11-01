import { useState, useEffect } from "react";
import { RotateCcw } from "lucide-react";
import type { Schema } from "../types";
import { MODELS, REASONING_EFFORTS } from "../types";

interface Props {
  schema: Schema;
  onSave: (updates: Partial<Schema>) => void;
}

const DEFAULT_SYSTEM_PROMPT =
  "Você é um assistente especializado em extração de informações de documentos. " +
  "Sua tarefa é analisar cuidadosamente o documento fornecido e extrair as informações " +
  "solicitadas de forma precisa e completa.\n\n" +
  "Para cada campo solicitado, você deve:\n" +
  "1. Extrair o valor correto do documento\n" +
  "2. Indicar o número da página (começando em 1) onde a informação foi encontrada\n" +
  "3. Fornecer a transcrição exata do trecho do documento que contém a informação\n\n" +
  "Regras importantes:\n" +
  "- Seja preciso e fiel ao conteúdo do documento\n" +
  "- A transcrição deve ser o trecho exato do texto original, sem modificações\n" +
  "- Se uma informação não for encontrada no documento, retorne null para o valor, " +
  "null para a página e null para a transcrição\n" +
  "- O número da página deve corresponder à página real do documento onde a informação aparece";

const DEFAULT_PROMPT =
  "Analise o documento a seguir e extraia todas as informações conforme o esquema definido.\n\n" +
  "Para cada campo, forneça:\n" +
  "- O valor extraído\n" +
  "- O número da página onde a informação foi encontrada\n" +
  "- A transcrição exata do trecho relevante do documento\n\n" +
  "Documento:\n{document_text}";

export default function PromptSettings({ schema, onSave }: Props) {
  const [model, setModel] = useState(schema.model);
  const [reasoning, setReasoning] = useState(
    schema.reasoning_effort || "none"
  );
  const [systemPrompt, setSystemPrompt] = useState(schema.system_prompt);
  const [prompt, setPrompt] = useState(schema.prompt);
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    setModel(schema.model);
    setReasoning(schema.reasoning_effort || "none");
    setSystemPrompt(schema.system_prompt);
    setPrompt(schema.prompt);
    setIsDirty(false);
  }, [schema.id]);

  const markDirty = () => setIsDirty(true);

  const selectedModel = MODELS.find((m) => m.id === model);

  const handleSave = () => {
    onSave({
      model,
      reasoning_effort: reasoning === "none" ? null : reasoning,
      system_prompt: systemPrompt,
      prompt,
    });
    setIsDirty(false);
  };

  return (
    <div className="flex flex-col h-full overflow-auto">
      <div className="p-4 space-y-5">
        {/* Save button */}
        {isDirty && (
          <div className="flex justify-end">
            <button
              onClick={handleSave}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white
                hover:bg-indigo-700 transition-colors"
            >
              Salvar Configurações
            </button>
          </div>
        )}

        {/* Model */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Modelo
          </label>
          <select
            value={model}
            onChange={(e) => {
              setModel(e.target.value);
              const m = MODELS.find((m) => m.id === e.target.value);
              if (m && !m.supportsReasoning) {
                setReasoning("none");
              }
              markDirty();
            }}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm
              shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            {MODELS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>

        {/* Reasoning Effort */}
        {selectedModel?.supportsReasoning && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nível de Raciocínio
            </label>
            <select
              value={reasoning}
              onChange={(e) => {
                setReasoning(e.target.value);
                markDirty();
              }}
              className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm
                shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              {REASONING_EFFORTS.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500">
              Controla o esforço de raciocínio do modelo. "Mínimo" é recomendado
              para extração de documentos.
            </p>
          </div>
        )}

        {/* System Prompt */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-sm font-medium text-gray-700">
              System Prompt
            </label>
            <button
              onClick={() => {
                setSystemPrompt(DEFAULT_SYSTEM_PROMPT);
                markDirty();
              }}
              className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-indigo-600
                transition-colors"
              title="Restaurar padrão"
            >
              <RotateCcw className="w-3 h-3" />
              Padrão
            </button>
          </div>
          <textarea
            value={systemPrompt}
            onChange={(e) => {
              setSystemPrompt(e.target.value);
              markDirty();
            }}
            rows={8}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm
              focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500
              resize-y font-mono"
          />
        </div>

        {/* Prompt */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-sm font-medium text-gray-700">Prompt</label>
            <button
              onClick={() => {
                setPrompt(DEFAULT_PROMPT);
                markDirty();
              }}
              className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-indigo-600
                transition-colors"
              title="Restaurar padrão"
            >
              <RotateCcw className="w-3 h-3" />
              Padrão
            </button>
          </div>
          <textarea
            value={prompt}
            onChange={(e) => {
              setPrompt(e.target.value);
              markDirty();
            }}
            rows={8}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm
              focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500
              resize-y font-mono"
          />
          <p className="mt-1 text-xs text-gray-500">
            Use <code className="bg-gray-100 px-1 rounded">{"{document_text}"}</code>{" "}
            como placeholder para o texto do documento.
          </p>
        </div>
      </div>
    </div>
  );
}

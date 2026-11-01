import { useState, useEffect, useCallback } from "react";
import { Toaster, toast } from "react-hot-toast";
import { Play, Loader2, Settings, FileCode2 } from "lucide-react";

import type {
  Schema,
  DocumentMeta,
  ExtractionResult,
  BoundingBox,
} from "./types";
import * as api from "./api";

import SchemaSelector from "./components/SchemaSelector";
import SchemaEditor from "./components/SchemaEditor";
import PromptSettings from "./components/PromptSettings";
import DocumentPanel from "./components/DocumentPanel";
import ExtractionPanel from "./components/ExtractionPanel";

export default function App() {
  // --- Schema state ---
  const [schemas, setSchemas] = useState<Schema[]>([]);
  const [selectedSchemaId, setSelectedSchemaId] = useState<string | null>(null);
  const [selectedSchema, setSelectedSchema] = useState<Schema | null>(null);

  // --- Document state ---
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(
    null
  );

  // --- Extraction state ---
  const [extractions, setExtractions] = useState<
    Record<string, ExtractionResult>
  >({});
  const [isExtracting, setIsExtracting] = useState(false);

  // --- Highlight state ---
  const [selectedHighlight, setSelectedHighlight] =
    useState<BoundingBox | null>(null);

  // --- Left panel tab ---
  const [leftTab, setLeftTab] = useState<"schema" | "settings">("schema");

  // --- Load schemas on mount ---
  useEffect(() => {
    loadSchemas();
  }, []);

  // --- Load schema details when selected ---
  useEffect(() => {
    if (selectedSchemaId) {
      loadSchemaDetails(selectedSchemaId);
    } else {
      setSelectedSchema(null);
      setDocuments([]);
      setExtractions({});
      setSelectedDocumentId(null);
    }
  }, [selectedSchemaId]);

  // --- Data loading functions ---

  const loadSchemas = async () => {
    try {
      const data = await api.fetchSchemas();
      setSchemas(data);
    } catch (e) {
      toast.error("Erro ao carregar schemas");
    }
  };

  const loadSchemaDetails = async (schemaId: string) => {
    try {
      const [schema, docs, exts] = await Promise.all([
        api.fetchSchema(schemaId),
        api.fetchDocuments(schemaId),
        api.fetchExtractions(schemaId),
      ]);
      setSelectedSchema(schema);
      setDocuments(docs);
      setSelectedDocumentId(docs[0]?.id || null);

      const extMap: Record<string, ExtractionResult> = {};
      for (const ext of exts) {
        extMap[ext.document_id] = ext;
      }
      setExtractions(extMap);
    } catch (e) {
      toast.error("Erro ao carregar schema");
    }
  };

  // --- Schema CRUD ---

  const handleCreateSchema = async (name: string) => {
    try {
      const schema = await api.createSchema({ name });
      await loadSchemas();
      setSelectedSchemaId(schema.id);
      toast.success("Schema criado!");
    } catch (e) {
      toast.error("Erro ao criar schema");
    }
  };

  const handleDeleteSchema = async (id: string) => {
    try {
      await api.deleteSchema(id);
      setSelectedSchemaId(null);
      await loadSchemas();
      toast.success("Schema excluído!");
    } catch (e) {
      toast.error("Erro ao excluir schema");
    }
  };

  const handleSaveJsonSchema = useCallback(
    async (jsonSchema: Record<string, unknown>) => {
      if (!selectedSchemaId) return;
      try {
        const updated = await api.updateSchema(selectedSchemaId, {
          json_schema: jsonSchema,
        } as Partial<Schema>);
        setSelectedSchema(updated);
        toast.success("Schema salvo!");
      } catch (e) {
        toast.error("Erro ao salvar schema");
      }
    },
    [selectedSchemaId]
  );

  const handleSaveSettings = useCallback(
    async (updates: Partial<Schema>) => {
      if (!selectedSchemaId) return;
      try {
        const updated = await api.updateSchema(selectedSchemaId, updates);
        setSelectedSchema(updated);
        toast.success("Configurações salvas!");
      } catch (e) {
        toast.error("Erro ao salvar configurações");
      }
    },
    [selectedSchemaId]
  );

  // --- Document management ---

  const handleUploadDocument = async (file: File) => {
    if (!selectedSchemaId) return;
    try {
      const doc = await api.uploadDocument(selectedSchemaId, file);
      const docs = await api.fetchDocuments(selectedSchemaId);
      setDocuments(docs);
      setSelectedDocumentId(doc.id);
      toast.success("Documento adicionado!");
    } catch (e) {
      toast.error("Erro ao fazer upload");
    }
  };

  const handleAddTextDocument = async (name: string, text: string) => {
    if (!selectedSchemaId) return;
    try {
      const doc = await api.addTextDocument(selectedSchemaId, name, text);
      const docs = await api.fetchDocuments(selectedSchemaId);
      setDocuments(docs);
      setSelectedDocumentId(doc.id);
      toast.success("Documento de texto adicionado!");
    } catch (e) {
      toast.error("Erro ao adicionar texto");
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!selectedSchemaId) return;
    try {
      await api.deleteDocument(selectedSchemaId, docId);
      const docs = await api.fetchDocuments(selectedSchemaId);
      setDocuments(docs);
      if (selectedDocumentId === docId) {
        setSelectedDocumentId(docs[0]?.id || null);
      }
      setExtractions((prev) => {
        const next = { ...prev };
        delete next[docId];
        return next;
      });
      toast.success("Documento excluído!");
    } catch (e) {
      toast.error("Erro ao excluir documento");
    }
  };

  // --- Extraction ---

  const handleRunExtraction = async () => {
    if (!selectedSchemaId) return;
    setIsExtracting(true);
    setSelectedHighlight(null);
    try {
      const results = await api.runExtraction(selectedSchemaId);
      const extMap: Record<string, ExtractionResult> = {};
      for (const ext of results) {
        extMap[ext.document_id] = ext;
      }
      setExtractions(extMap);

      const successCount = results.filter(
        (r) => r.status === "success"
      ).length;
      const errorCount = results.filter((r) => r.status === "error").length;

      if (errorCount === 0) {
        toast.success(
          `Extração concluída! ${successCount} documento(s) processado(s).`
        );
      } else {
        toast.error(
          `${successCount} sucesso(s), ${errorCount} erro(s)`
        );
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Erro na extração";
      toast.error(msg);
    } finally {
      setIsExtracting(false);
    }
  };

  // --- Highlight ---

  const handleSelectField = (highlight: BoundingBox | null) => {
    setSelectedHighlight(highlight);
  };

  // --- Derived ---

  const currentExtraction = selectedDocumentId
    ? extractions[selectedDocumentId] || null
    : null;

  // Only the clicked field is highlighted on the PDF
  const highlights = selectedHighlight ? [selectedHighlight] : [];

  const getDocumentUrl = (docId: string) =>
    api.getDocumentFileUrl(selectedSchemaId!, docId);

  // --- Render ---

  return (
    <div className="flex flex-col h-screen">
      <Toaster position="top-right" />

      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="flex items-center justify-between px-6 py-3">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-bold text-gray-900 tracking-tight">
              Document Extractor
            </h1>
            <div className="h-6 w-px bg-gray-200" />
            <SchemaSelector
              schemas={schemas}
              selectedSchemaId={selectedSchemaId}
              onSelect={setSelectedSchemaId}
              onCreate={handleCreateSchema}
              onDelete={handleDeleteSchema}
            />
          </div>

          {selectedSchema && (
            <button
              onClick={handleRunExtraction}
              disabled={isExtracting || documents.length === 0}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600
                text-white font-medium text-sm hover:bg-emerald-700 disabled:opacity-50
                disabled:cursor-not-allowed transition-colors shadow-sm"
            >
              {isExtracting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Extraindo...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Executar Extração
                </>
              )}
            </button>
          )}
        </div>
      </header>

      {/* Main Content */}
      {selectedSchema ? (
        <div className="flex flex-1 overflow-hidden">
          {/* Left Panel - Schema Editor & Settings */}
          <div className="w-[30%] min-w-[320px] border-r border-gray-200 flex flex-col bg-white">
            {/* Panel tabs */}
            <div className="flex border-b border-gray-200">
              <button
                onClick={() => setLeftTab("schema")}
                className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium
                  border-b-2 transition-colors ${
                    leftTab === "schema"
                      ? "border-indigo-600 text-indigo-600"
                      : "border-transparent text-gray-500 hover:text-gray-700"
                  }`}
              >
                <FileCode2 className="w-4 h-4" />
                Schema
              </button>
              <button
                onClick={() => setLeftTab("settings")}
                className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium
                  border-b-2 transition-colors ${
                    leftTab === "settings"
                      ? "border-indigo-600 text-indigo-600"
                      : "border-transparent text-gray-500 hover:text-gray-700"
                  }`}
              >
                <Settings className="w-4 h-4" />
                Modelo & Prompt
              </button>
            </div>

            {/* Panel content */}
            <div className="flex-1 overflow-hidden">
              {leftTab === "schema" ? (
                <SchemaEditor
                  schema={selectedSchema}
                  onSave={handleSaveJsonSchema}
                />
              ) : (
                <PromptSettings
                  schema={selectedSchema}
                  onSave={handleSaveSettings}
                />
              )}
            </div>
          </div>

          {/* Center Panel - Documents */}
          <div
            className={`${
              currentExtraction ? "w-[40%]" : "flex-1"
            } min-w-[300px] border-r border-gray-200 flex flex-col`}
          >
            <DocumentPanel
              schemaId={selectedSchemaId!}
              documents={documents}
              selectedDocumentId={selectedDocumentId}
              onSelectDocument={setSelectedDocumentId}
              onUpload={handleUploadDocument}
              onAddText={handleAddTextDocument}
              onDelete={handleDeleteDocument}
              highlights={highlights}
              selectedHighlight={selectedHighlight}
              getDocumentUrl={getDocumentUrl}
            />
          </div>

          {/* Right Panel - Extraction Results (conditional) */}
          {currentExtraction && (
            <div className="w-[30%] min-w-[280px] flex flex-col bg-white">
              <ExtractionPanel
                extraction={currentExtraction}
                onSelectField={handleSelectField}
                selectedHighlight={selectedHighlight}
              />
            </div>
          )}
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center bg-gray-50">
          <div className="text-center max-w-md">
            <div className="w-16 h-16 rounded-2xl bg-indigo-100 flex items-center justify-center mx-auto mb-4">
              <FileCode2 className="w-8 h-8 text-indigo-600" />
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Bem-vindo ao Document Extractor
            </h2>
            <p className="text-gray-500 text-sm mb-6">
              Crie um schema de extração para começar. Defina os campos que
              deseja extrair dos seus documentos usando JSON Schema.
            </p>
            <p className="text-gray-400 text-xs">
              Selecione ou crie um schema no menu acima para começar.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}


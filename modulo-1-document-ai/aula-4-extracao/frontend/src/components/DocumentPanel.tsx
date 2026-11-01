import { useState, useRef } from "react";
import {
  Upload,
  FileText,
  Trash2,
  X,
  Plus,
  File as FileIcon,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import type { DocumentMeta, BoundingBox } from "../types";
import PdfViewer from "./PdfViewer";

interface Props {
  schemaId: string;
  documents: DocumentMeta[];
  selectedDocumentId: string | null;
  onSelectDocument: (id: string) => void;
  onUpload: (file: File) => void;
  onAddText: (name: string, text: string) => void;
  onDelete: (id: string) => void;
  highlights: BoundingBox[];
  selectedHighlight: BoundingBox | null;
  getDocumentUrl: (docId: string) => string;
}

export default function DocumentPanel({
  documents,
  selectedDocumentId,
  onSelectDocument,
  onUpload,
  onAddText,
  onDelete,
  highlights,
  selectedHighlight,
  getDocumentUrl,
}: Props) {
  const [showTextDialog, setShowTextDialog] = useState(false);
  const [textName, setTextName] = useState("");
  const [textContent, setTextContent] = useState("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onUpload(file);
      e.target.value = "";
    }
  };

  const handleAddText = () => {
    if (textName.trim() && textContent.trim()) {
      onAddText(textName.trim(), textContent.trim());
      setTextName("");
      setTextContent("");
      setShowTextDialog(false);
    }
  };

  return (
    <div className="flex h-full">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Document Sidebar */}
      <div
        className={`${
          sidebarCollapsed ? "w-10" : "w-56"
        } shrink-0 bg-white border-r border-gray-200 flex flex-col transition-all duration-200`}
      >
        {sidebarCollapsed ? (
          /* Collapsed sidebar */
          <div className="flex flex-col items-center py-2 gap-2">
            <button
              onClick={() => setSidebarCollapsed(false)}
              className="p-1.5 rounded hover:bg-gray-100 transition-colors"
              title="Expandir documentos"
            >
              <ChevronRight className="w-4 h-4 text-gray-500" />
            </button>
            <div className="w-6 h-px bg-gray-200" />
            <span className="text-[10px] text-gray-400 font-medium [writing-mode:vertical-lr] rotate-180">
              {documents.length} doc{documents.length !== 1 ? "s" : ""}
            </span>
          </div>
        ) : (
          <>
            {/* Sidebar header */}
            <div className="px-3 py-3 border-b border-gray-200">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Documentos ({documents.length})
                </h3>
                <button
                  onClick={() => setSidebarCollapsed(true)}
                  className="p-1 rounded hover:bg-gray-100 transition-colors"
                  title="Recolher"
                >
                  <ChevronLeft className="w-3.5 h-3.5 text-gray-400" />
                </button>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="flex-1 inline-flex items-center justify-center gap-1.5 px-2 py-2
                    rounded-md text-xs font-medium text-white bg-indigo-600
                    hover:bg-indigo-700 transition-colors"
                >
                  <Upload className="w-3.5 h-3.5" />
                  PDF
                </button>
                <button
                  onClick={() => setShowTextDialog(true)}
                  className="flex-1 inline-flex items-center justify-center gap-1.5 px-2 py-2
                    rounded-md text-xs font-medium text-gray-700 bg-gray-100
                    hover:bg-gray-200 transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Texto
                </button>
              </div>
            </div>

            {/* Document list */}
            <div className="flex-1 overflow-auto py-1">
              {documents.length === 0 ? (
                <div className="px-3 py-8 text-center">
                  <FileIcon className="w-8 h-8 text-gray-200 mx-auto mb-2" />
                  <p className="text-xs text-gray-400">
                    Nenhum documento
                  </p>
                </div>
              ) : (
                documents.map((doc) => (
                  <div
                    key={doc.id}
                    className={`group flex items-center gap-2 px-3 py-2 cursor-pointer
                      transition-colors ${
                        selectedDocumentId === doc.id
                          ? "bg-indigo-50 border-r-2 border-indigo-600"
                          : "hover:bg-gray-50"
                      }`}
                    onClick={() => onSelectDocument(doc.id)}
                  >
                    {doc.original_type === "text" ? (
                      <FileText
                        className={`w-4 h-4 shrink-0 ${
                          selectedDocumentId === doc.id
                            ? "text-indigo-600"
                            : "text-gray-400"
                        }`}
                      />
                    ) : (
                      <FileIcon
                        className={`w-4 h-4 shrink-0 ${
                          selectedDocumentId === doc.id
                            ? "text-indigo-600"
                            : "text-gray-400"
                        }`}
                      />
                    )}
                    <span
                      className={`text-sm truncate flex-1 ${
                        selectedDocumentId === doc.id
                          ? "text-indigo-700 font-medium"
                          : "text-gray-700"
                      }`}
                      title={doc.name}
                    >
                      {doc.name}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm(`Excluir "${doc.name}"?`)) {
                          onDelete(doc.id);
                        }
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded
                        hover:bg-red-100 transition-all shrink-0"
                    >
                      <Trash2 className="w-3 h-3 text-red-500" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </>
        )}
      </div>

      {/* PDF Viewer */}
      <div className="flex-1 flex flex-col min-w-0">
        {selectedDocumentId ? (
          <PdfViewer
            url={getDocumentUrl(selectedDocumentId)}
            highlights={highlights}
            selectedHighlight={selectedHighlight}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center bg-gray-50">
            <div className="text-center">
              <FileIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-500">
                {documents.length === 0
                  ? "Adicione documentos para começar"
                  : "Selecione um documento na lista"}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Text Document Dialog */}
      {showTextDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">
                Adicionar Documento de Texto
              </h3>
              <button
                onClick={() => setShowTextDialog(false)}
                className="p-1 rounded hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="px-6 py-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nome do documento
                </label>
                <input
                  type="text"
                  value={textName}
                  onChange={(e) => setTextName(e.target.value)}
                  placeholder="Ex: Contrato de prestação de serviço"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm
                    focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Conteúdo do texto
                </label>
                <textarea
                  value={textContent}
                  onChange={(e) => setTextContent(e.target.value)}
                  rows={12}
                  placeholder="Cole ou digite o texto do documento aqui..."
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm
                    focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500
                    resize-y font-mono"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-xl">
              <button
                onClick={() => setShowTextDialog(false)}
                className="px-4 py-2 rounded-md text-sm font-medium text-gray-700
                  bg-white border border-gray-300 hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleAddText}
                disabled={!textName.trim() || !textContent.trim()}
                className="px-4 py-2 rounded-md text-sm font-medium text-white
                  bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50
                  disabled:cursor-not-allowed transition-colors"
              >
                Adicionar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

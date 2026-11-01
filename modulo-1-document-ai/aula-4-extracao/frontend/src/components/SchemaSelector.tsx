import { useState } from "react";
import { Plus, Trash2, FileJson } from "lucide-react";
import type { Schema } from "../types";

interface Props {
  schemas: Schema[];
  selectedSchemaId: string | null;
  onSelect: (id: string) => void;
  onCreate: (name: string) => void;
  onDelete: (id: string) => void;
}

export default function SchemaSelector({
  schemas,
  selectedSchemaId,
  onSelect,
  onCreate,
  onDelete,
}: Props) {
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");

  const handleCreate = () => {
    if (newName.trim()) {
      onCreate(newName.trim());
      setNewName("");
      setShowCreate(false);
    }
  };

  return (
    <div className="flex items-center gap-3 flex-wrap">
      <div className="flex items-center gap-2">
        <FileJson className="w-5 h-5 text-indigo-600" />
        <label className="text-sm font-medium text-gray-700">Schema:</label>
      </div>

      <select
        className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm shadow-sm
          focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500
          min-w-[200px]"
        value={selectedSchemaId || ""}
        onChange={(e) => onSelect(e.target.value)}
      >
        <option value="" disabled>
          Selecione um schema...
        </option>
        {schemas.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </select>

      {showCreate ? (
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Nome do schema..."
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm shadow-sm
              focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            autoFocus
          />
          <button
            onClick={handleCreate}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white
              hover:bg-indigo-700 transition-colors"
          >
            Criar
          </button>
          <button
            onClick={() => {
              setShowCreate(false);
              setNewName("");
            }}
            className="rounded-md bg-gray-200 px-3 py-1.5 text-sm font-medium text-gray-700
              hover:bg-gray-300 transition-colors"
          >
            Cancelar
          </button>
        </div>
      ) : (
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-1.5
            text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Novo
        </button>
      )}

      {selectedSchemaId && (
        <button
          onClick={() => {
            if (confirm("Tem certeza que deseja excluir este schema?")) {
              onDelete(selectedSchemaId);
            }
          }}
          className="inline-flex items-center gap-1.5 rounded-md bg-red-50 px-3 py-1.5
            text-sm font-medium text-red-700 hover:bg-red-100 transition-colors"
        >
          <Trash2 className="w-4 h-4" />
          Excluir
        </button>
      )}
    </div>
  );
}

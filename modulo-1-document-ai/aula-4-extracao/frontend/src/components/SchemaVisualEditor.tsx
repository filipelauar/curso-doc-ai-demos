import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Plus,
  Trash2,
  GripVertical,
} from "lucide-react";

interface FieldSchema {
  type?: string;
  description?: string;
  enum?: string[];
  properties?: Record<string, FieldSchema>;
  items?: FieldSchema;
  required?: string[];
}

interface Props {
  schema: Record<string, unknown>;
  onChange: (schema: Record<string, unknown>) => void;
}

const TYPE_OPTIONS = [
  { value: "string", label: "Texto" },
  { value: "number", label: "Número" },
  { value: "integer", label: "Inteiro" },
  { value: "boolean", label: "Booleano" },
  { value: "object", label: "Objeto" },
  { value: "array", label: "Lista" },
] as const;

const TYPE_COLORS: Record<string, string> = {
  string: "bg-blue-100 text-blue-700",
  number: "bg-green-100 text-green-700",
  integer: "bg-green-100 text-green-700",
  boolean: "bg-purple-100 text-purple-700",
  object: "bg-orange-100 text-orange-700",
  array: "bg-yellow-100 text-yellow-700",
};

function getTypeLabel(type: string | undefined): string {
  return TYPE_OPTIONS.find((t) => t.value === type)?.label || type || "Texto";
}

export default function SchemaVisualEditor({ schema, onChange }: Props) {
  const properties = (schema.properties || {}) as Record<string, FieldSchema>;
  const required = ((schema.required || []) as string[]);

  const [addingField, setAddingField] = useState(false);
  const [newFieldName, setNewFieldName] = useState("");

  const updateProperties = (
    newProps: Record<string, FieldSchema>,
    newRequired?: string[]
  ) => {
    onChange({
      ...schema,
      type: "object",
      properties: newProps,
      required: newRequired ?? required,
    });
  };

  const handleAddField = () => {
    if (!newFieldName.trim()) return;
    const key = newFieldName.trim().toLowerCase().replace(/\s+/g, "_");
    if (properties[key]) return; // duplicate

    const newProps = {
      ...properties,
      [key]: { type: "string", description: "" } as FieldSchema,
    };
    updateProperties(newProps, [...required, key]);
    setNewFieldName("");
    setAddingField(false);
  };

  const handleUpdateField = (
    name: string,
    updated: FieldSchema
  ) => {
    updateProperties({ ...properties, [name]: updated });
  };

  const handleDeleteField = (name: string) => {
    const newProps = { ...properties };
    delete newProps[name];
    updateProperties(
      newProps,
      required.filter((r) => r !== name)
    );
  };

  const handleRenameField = (oldName: string, newName: string) => {
    const key = newName.trim().toLowerCase().replace(/\s+/g, "_");
    if (!key || key === oldName || properties[key]) return;

    const entries = Object.entries(properties);
    const newProps: Record<string, FieldSchema> = {};
    for (const [k, v] of entries) {
      newProps[k === oldName ? key : k] = v;
    }
    const newReq = required.map((r) => (r === oldName ? key : r));
    updateProperties(newProps, newReq);
  };

  const handleToggleRequired = (name: string) => {
    const isReq = required.includes(name);
    const newReq = isReq
      ? required.filter((r) => r !== name)
      : [...required, name];
    updateProperties(properties, newReq);
  };

  const fieldEntries = Object.entries(properties);

  return (
    <div className="p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-700">
          JSON Schema Editor
        </h3>
        {addingField ? (
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={newFieldName}
              onChange={(e) => setNewFieldName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleAddField();
                if (e.key === "Escape") {
                  setAddingField(false);
                  setNewFieldName("");
                }
              }}
              placeholder="nome_do_campo"
              className="rounded-md border border-gray-300 px-2.5 py-1.5 text-sm
                focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500
                font-mono"
              autoFocus
            />
            <button
              onClick={handleAddField}
              disabled={!newFieldName.trim()}
              className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white
                hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              Adicionar
            </button>
            <button
              onClick={() => {
                setAddingField(false);
                setNewFieldName("");
              }}
              className="rounded-md bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-600
                hover:bg-gray-200 transition-colors"
            >
              Cancelar
            </button>
          </div>
        ) : (
          <button
            onClick={() => setAddingField(true)}
            className="inline-flex items-center gap-1.5 rounded-md bg-gray-100 px-3 py-1.5
              text-xs font-medium text-gray-700 hover:bg-gray-200 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Adicionar Campo
          </button>
        )}
      </div>

      {/* Fields list */}
      {fieldEntries.length === 0 ? (
        <div className="text-center py-12 border-2 border-dashed border-gray-200 rounded-lg">
          <p className="text-sm text-gray-500">Nenhum campo definido</p>
          <p className="text-xs text-gray-400 mt-1">
            Clique em "Adicionar Campo" para começar
          </p>
        </div>
      ) : (
        <div className="space-y-1">
          {fieldEntries.map(([name, fieldSchema]) => (
            <FieldRow
              key={name}
              name={name}
              schema={fieldSchema}
              isRequired={required.includes(name)}
              onUpdate={(updated) => handleUpdateField(name, updated)}
              onDelete={() => handleDeleteField(name)}
              onRename={(newName) => handleRenameField(name, newName)}
              onToggleRequired={() => handleToggleRequired(name)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// --- Field Row ---

interface FieldRowProps {
  name: string;
  schema: FieldSchema;
  isRequired: boolean;
  onUpdate: (schema: FieldSchema) => void;
  onDelete: () => void;
  onRename: (newName: string) => void;
  onToggleRequired: () => void;
  depth?: number;
}

function FieldRow({
  name,
  schema,
  isRequired,
  onUpdate,
  onDelete,
  onRename,
  onToggleRequired,
  depth = 0,
}: FieldRowProps) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState(name);
  const type = schema.type || "string";
  const hasDetails = !!(schema.description || schema.enum);
  const isNested = type === "object" && schema.properties;

  const handleNameSubmit = () => {
    if (editName.trim() && editName !== name) {
      onRename(editName.trim());
    }
    setEditing(false);
  };

  return (
    <div
      className={`border border-gray-200 rounded-lg bg-white overflow-hidden ${
        depth > 0 ? "ml-6" : ""
      }`}
    >
      {/* Main row */}
      <div
        className="flex items-center gap-2 px-3 py-2.5 hover:bg-gray-50 transition-colors cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Expand chevron */}
        <button
          className="text-gray-400 hover:text-gray-600 shrink-0"
          onClick={(e) => {
            e.stopPropagation();
            setExpanded(!expanded);
          }}
        >
          {expanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </button>

        <GripVertical className="w-3.5 h-3.5 text-gray-300 shrink-0" />

        {/* Field name */}
        {editing ? (
          <input
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            onBlur={handleNameSubmit}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleNameSubmit();
              if (e.key === "Escape") {
                setEditName(name);
                setEditing(false);
              }
            }}
            onClick={(e) => e.stopPropagation()}
            className="font-mono text-sm font-medium text-gray-900 bg-indigo-50 border
              border-indigo-300 rounded px-1.5 py-0.5 focus:outline-none focus:ring-1
              focus:ring-indigo-500 min-w-[100px]"
            autoFocus
          />
        ) : (
          <span
            className="font-mono text-sm font-medium text-gray-900 cursor-text
              hover:bg-gray-100 px-1.5 py-0.5 rounded transition-colors"
            onClick={(e) => {
              e.stopPropagation();
              setEditName(name);
              setEditing(true);
            }}
            title="Clique para renomear"
          >
            {name}
          </span>
        )}

        {/* Description preview */}
        {schema.description && !expanded && (
          <span className="text-xs text-gray-400 truncate max-w-[200px] hidden lg:inline">
            {schema.description}
          </span>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Type badge */}
        <select
          value={type}
          onChange={(e) => {
            e.stopPropagation();
            const newType = e.target.value;
            const updated: FieldSchema = { ...schema, type: newType };
            if (newType === "object" && !updated.properties) {
              updated.properties = {};
            }
            if (newType !== "object") {
              delete updated.properties;
            }
            if (newType === "array" && !updated.items) {
              updated.items = { type: "string" };
            }
            if (newType !== "array") {
              delete updated.items;
            }
            onUpdate(updated);
          }}
          onClick={(e) => e.stopPropagation()}
          className={`text-xs font-medium px-2.5 py-1 rounded-full border-0 cursor-pointer
            appearance-none text-center ${TYPE_COLORS[type] || "bg-gray-100 text-gray-600"}`}
        >
          {TYPE_OPTIONS.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>

        {/* Required badge */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleRequired();
          }}
          className={`text-xs font-medium px-2 py-1 rounded-full transition-colors ${
            isRequired
              ? "bg-red-100 text-red-700 hover:bg-red-200"
              : "bg-gray-100 text-gray-400 hover:bg-gray-200"
          }`}
        >
          {isRequired ? "Obrigatório" : "Opcional"}
        </button>

        {/* Delete */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="p-1 text-gray-300 hover:text-red-500 transition-colors rounded
            hover:bg-red-50 shrink-0"
          title="Remover campo"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="px-4 pb-4 pt-1 border-t border-gray-100 bg-gray-50/50">
          {/* Description */}
          <div className="mb-3">
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Descrição
            </label>
            <textarea
              value={schema.description || ""}
              onChange={(e) =>
                onUpdate({ ...schema, description: e.target.value })
              }
              placeholder="Descreva o que este campo deve conter..."
              rows={3}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm
                focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500
                resize-y bg-white"
            />
          </div>

          {/* Enum values (for string fields) */}
          {(type === "string") && (
            <div className="mb-3">
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Valores permitidos (enum, um por linha)
              </label>
              <textarea
                value={(schema.enum || []).join("\n")}
                onChange={(e) => {
                  const vals = e.target.value
                    .split("\n")
                    .filter((v) => v.trim());
                  onUpdate({
                    ...schema,
                    enum: vals.length > 0 ? vals : undefined,
                  } as FieldSchema);
                }}
                placeholder="Deixe vazio para aceitar qualquer texto"
                rows={2}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm
                  font-mono focus:border-indigo-500 focus:outline-none focus:ring-1
                  focus:ring-indigo-500 resize-y bg-white"
              />
            </div>
          )}

          {/* Nested object fields */}
          {type === "object" && (
            <NestedObjectEditor
              schema={schema}
              onUpdate={onUpdate}
              depth={depth + 1}
            />
          )}

          {/* Array items editor */}
          {type === "array" && schema.items && (
            <div>
              <div className="flex items-center gap-3 mb-2">
                <label className="text-xs font-medium text-gray-500">
                  Tipo dos itens
                </label>
                <select
                  value={schema.items.type || "string"}
                  onChange={(e) => {
                    const newType = e.target.value;
                    const newItems: FieldSchema = { ...schema.items, type: newType };
                    if (newType === "object" && !newItems.properties) {
                      newItems.properties = {};
                      newItems.required = [];
                    }
                    if (newType !== "object") {
                      delete newItems.properties;
                      delete newItems.required;
                    }
                    if (newType === "array" && !newItems.items) {
                      newItems.items = { type: "string" };
                    }
                    if (newType !== "array") {
                      delete newItems.items;
                    }
                    onUpdate({ ...schema, items: newItems });
                  }}
                  className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm
                    focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  {TYPE_OPTIONS.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Description for array items */}
              {schema.items.description !== undefined && (
                <div className="mb-3">
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Descrição dos itens
                  </label>
                  <textarea
                    value={schema.items.description || ""}
                    onChange={(e) =>
                      onUpdate({
                        ...schema,
                        items: { ...schema.items, description: e.target.value },
                      })
                    }
                    placeholder="Descreva os itens da lista..."
                    rows={2}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm
                      focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500
                      resize-y bg-white"
                  />
                </div>
              )}

              {/* If items are objects, show nested properties */}
              {schema.items.type === "object" && (
                <NestedObjectEditor
                  schema={schema.items}
                  onUpdate={(updatedItems) =>
                    onUpdate({ ...schema, items: updatedItems })
                  }
                  depth={depth + 1}
                />
              )}

              {/* If items are arrays, show nested array editor */}
              {schema.items.type === "array" && schema.items.items && (
                <div className="ml-4 mt-2 pl-3 border-l-2 border-gray-200">
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Itens da sub-lista
                  </label>
                  <FieldRow
                    name="items"
                    schema={schema.items.items}
                    isRequired={false}
                    onUpdate={(updated) =>
                      onUpdate({
                        ...schema,
                        items: { ...schema.items, items: updated },
                      })
                    }
                    onDelete={() => {}}
                    onRename={() => {}}
                    onToggleRequired={() => {}}
                    depth={depth + 1}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// --- Nested object editor ---

function NestedObjectEditor({
  schema,
  onUpdate,
  depth,
}: {
  schema: FieldSchema;
  onUpdate: (schema: FieldSchema) => void;
  depth: number;
}) {
  const properties = schema.properties || {};
  const required = schema.required || [];
  const [addingField, setAddingField] = useState(false);
  const [newFieldName, setNewFieldName] = useState("");

  const handleAddField = () => {
    if (!newFieldName.trim()) return;
    const key = newFieldName.trim().toLowerCase().replace(/\s+/g, "_");
    if (properties[key]) return;

    onUpdate({
      ...schema,
      properties: {
        ...properties,
        [key]: { type: "string", description: "" },
      },
      required: [...required, key],
    });
    setNewFieldName("");
    setAddingField(false);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <label className="text-xs font-medium text-gray-500">
          Propriedades
        </label>
        {addingField ? (
          <div className="flex items-center gap-1.5">
            <input
              type="text"
              value={newFieldName}
              onChange={(e) => setNewFieldName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleAddField();
                if (e.key === "Escape") {
                  setAddingField(false);
                  setNewFieldName("");
                }
              }}
              placeholder="campo"
              className="rounded border border-gray-300 px-2 py-1 text-xs font-mono
                focus:border-indigo-500 focus:outline-none"
              autoFocus
            />
            <button
              onClick={handleAddField}
              className="text-xs text-indigo-600 font-medium hover:text-indigo-800"
            >
              OK
            </button>
          </div>
        ) : (
          <button
            onClick={() => setAddingField(true)}
            className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-indigo-600"
          >
            <Plus className="w-3 h-3" />
            Campo
          </button>
        )}
      </div>
      <div className="space-y-1">
        {Object.entries(properties).map(([name, fieldSchema]) => (
          <FieldRow
            key={name}
            name={name}
            schema={fieldSchema}
            isRequired={required.includes(name)}
            depth={depth}
            onUpdate={(updated) =>
              onUpdate({
                ...schema,
                properties: { ...properties, [name]: updated },
              })
            }
            onDelete={() => {
              const newProps = { ...properties };
              delete newProps[name];
              onUpdate({
                ...schema,
                properties: newProps,
                required: required.filter((r) => r !== name),
              });
            }}
            onRename={(newName) => {
              const entries = Object.entries(properties);
              const newProps: Record<string, FieldSchema> = {};
              for (const [k, v] of entries) {
                newProps[k === name ? newName : k] = v;
              }
              onUpdate({
                ...schema,
                properties: newProps,
                required: required.map((r) => (r === name ? newName : r)),
              });
            }}
            onToggleRequired={() => {
              const isReq = required.includes(name);
              onUpdate({
                ...schema,
                required: isReq
                  ? required.filter((r) => r !== name)
                  : [...required, name],
              });
            }}
          />
        ))}
      </div>
    </div>
  );
}

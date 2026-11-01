import { useState, useRef, useCallback, useEffect } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { ZoomIn, ZoomOut } from "lucide-react";
import type { BoundingBox } from "../types";

import "react-pdf/dist/esm/Page/AnnotationLayer.css";
import "react-pdf/dist/esm/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface Props {
  url: string;
  highlights?: BoundingBox[];
  selectedHighlight?: BoundingBox | null;
}

export default function PdfViewer({
  url,
  highlights = [],
  selectedHighlight,
}: Props) {
  const [numPages, setNumPages] = useState(0);
  const [scale, setScale] = useState(1.0);
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const [containerWidth, setContainerWidth] = useState(600);

  // Auto-scroll to selected highlight page
  useEffect(() => {
    if (selectedHighlight && pageRefs.current[selectedHighlight.page]) {
      pageRefs.current[selectedHighlight.page]?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
  }, [selectedHighlight]);

  // Measure container width
  useEffect(() => {
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width - 32); // padding
      }
    });
    if (containerRef.current) {
      observer.observe(containerRef.current);
    }
    return () => observer.disconnect();
  }, []);

  const onDocumentLoadSuccess = useCallback(
    ({ numPages }: { numPages: number }) => {
      setNumPages(numPages);
    },
    []
  );

  const pageWidth = Math.max(300, containerWidth * scale);

  return (
    <div ref={containerRef} className="flex flex-col h-full">
      {/* Controls */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200">
        <span className="text-sm text-gray-600">
          {numPages} {numPages === 1 ? "página" : "páginas"}
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setScale((s) => Math.max(0.5, s - 0.1))}
            className="p-1 rounded hover:bg-gray-200 transition-colors"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="text-xs text-gray-500 min-w-[40px] text-center">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={() => setScale((s) => Math.min(2, s + 0.1))}
            className="p-1 rounded hover:bg-gray-200 transition-colors"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* PDF - all pages rendered, scrollable */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-auto p-4 bg-gray-100"
      >
        <Document
          file={url}
          onLoadSuccess={onDocumentLoadSuccess}
          loading={
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
            </div>
          }
          error={
            <div className="text-center py-12 text-red-500 text-sm">
              Erro ao carregar PDF
            </div>
          }
        >
          <div className="flex flex-col items-center gap-4">
            {Array.from({ length: numPages }, (_, i) => i + 1).map(
              (pageNum) => {
                const pageHighlights = highlights.filter(
                  (h) => h.page === pageNum
                );
                return (
                  <div
                    key={pageNum}
                    ref={(el) => {
                      pageRefs.current[pageNum] = el;
                    }}
                    className="relative inline-block shadow-lg"
                  >
                    <Page
                      pageNumber={pageNum}
                      width={pageWidth}
                      renderTextLayer={true}
                      renderAnnotationLayer={false}
                    />
                    {/* Page number label */}
                    <div className="absolute top-2 right-2 bg-black/60 text-white text-[10px] px-1.5 py-0.5 rounded">
                      {pageNum}
                    </div>
                    {/* Bounding box overlays */}
                    {pageHighlights.map((h, i) => {
                      const isSelected =
                        selectedHighlight &&
                        selectedHighlight.x0 === h.x0 &&
                        selectedHighlight.y0 === h.y0 &&
                        selectedHighlight.x1 === h.x1 &&
                        selectedHighlight.y1 === h.y1 &&
                        selectedHighlight.page === h.page;
                      return (
                        <div
                          key={i}
                          className={`absolute pointer-events-none transition-all duration-200 ${
                            isSelected
                              ? "border-2 border-indigo-500 bg-indigo-500/20 ring-2 ring-indigo-300"
                              : "border border-amber-400 bg-amber-400/10"
                          }`}
                          style={{
                            left: `${h.x0 * 100}%`,
                            top: `${h.y0 * 100}%`,
                            width: `${(h.x1 - h.x0) * 100}%`,
                            height: `${(h.y1 - h.y0) * 100}%`,
                          }}
                        />
                      );
                    })}
                  </div>
                );
              }
            )}
          </div>
        </Document>
      </div>
    </div>
  );
}

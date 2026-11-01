import React, { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { fetchFileBlob } from "../lib/api";

function DocumentViewerModal({
  isOpen,
  onClose,
  fileUrl,
  fileName,
  requirementTitle,
  onDelete,
}) {
  const { t } = useTranslation();
  const [blobUrl, setBlobUrl] = useState(null);
  const [mimeType, setMimeType] = useState("");
  const [fileSize, setFileSize] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Image controls state
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const modalRef = useRef(null);

  // Load file via credentialed fetch to create blob URL
  useEffect(() => {
    if (!isOpen || !fileUrl) {
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
        setBlobUrl(null);
      }
      return;
    }

    setLoading(true);
    setError(null);
    setZoom(1);
    setRotation(0);
    setPan({ x: 0, y: 0 });

    let active = true;

    fetchFileBlob(fileUrl)
      .then((blob) => {
        if (!active) return;
        const objectUrl = URL.createObjectURL(blob);
        setBlobUrl(objectUrl);
        setMimeType(blob.type);
        setFileSize(blob.size);
      })
      .catch((err) => {
        if (!active) return;
        console.error("Failed to load document:", err);
        setError(err.message || "Failed to load document preview.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, fileUrl]);

  // Keyboard navigation (+, -, r, Escape)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!isOpen) return;
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "+" || e.key === "=") {
        setZoom((z) => Math.min(z + 0.25, 4));
      } else if (e.key === "-" || e.key === "_") {
        setZoom((z) => Math.max(z - 0.25, 0.5));
      } else if (e.key.toLowerCase() === "r") {
        setRotation((r) => (r + 90) % 360);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Mouse pan handlers for image
  const handleMouseDown = (e) => {
    if (e.button !== 0) return; // Primary click only
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  if (!isOpen) return null;

  const isPdf =
    mimeType.includes("pdf") ||
    (fileName && fileName.toLowerCase().endsWith(".pdf")) ||
    (fileUrl && fileUrl.toLowerCase().includes(".pdf"));

  const formatSize = (bytes) => {
    if (!bytes) return null;
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const downloadUrl = fileUrl ? `${fileUrl}${fileUrl.includes("?") ? "&" : "?"}download=1` : null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="doc-viewer-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/75 backdrop-blur-sm animate-fade-in"
      onMouseUp={handleMouseUp}
    >
      <div
        ref={modalRef}
        className="relative w-full max-w-5xl h-[90vh] bg-white dark:bg-gray-900 rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-gray-200 dark:border-gray-800"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3 truncate pr-4">
            <span className="text-xl">📄</span>
            <div>
              <h2 id="doc-viewer-title" className="text-base font-bold text-gray-900 dark:text-white truncate">
                {requirementTitle || fileName || "Document Viewer"}
              </h2>
              <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                {fileName && <span className="truncate max-w-xs">{fileName}</span>}
                {fileSize && <span>• {formatSize(fileSize)}</span>}
                {mimeType && <span className="uppercase">• {mimeType.split("/")[1] || mimeType}</span>}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Download Button */}
            {downloadUrl && (
              <a
                href={downloadUrl}
                download={fileName || "document"}
                className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition"
                title="Download Document"
                aria-label="Download Document"
              >
                ⬇️
              </a>
            )}

            {/* Delete Button (if provided) */}
            {onDelete && (
              <button
                onClick={() => {
                  if (window.confirm("Are you sure you want to remove this uploaded document?")) {
                    onDelete();
                    onClose();
                  }
                }}
                className="p-2 rounded-lg border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 transition"
                title="Delete Document"
                aria-label="Delete Document"
              >
                🗑️
              </button>
            )}

            {/* Close Button */}
            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 transition font-bold"
              title="Close (Esc)"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Toolbar for image manipulation */}
        {!isPdf && !loading && !error && (
          <div className="flex items-center justify-center gap-2 sm:gap-4 px-4 py-2 bg-gray-100 dark:bg-gray-800/80 border-b border-gray-200 dark:border-gray-700 text-sm text-gray-700 dark:text-gray-300">
            <button
              onClick={() => setZoom((z) => Math.max(z - 0.25, 0.5))}
              className="px-2.5 py-1 rounded bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 font-bold"
              title="Zoom Out (-)"
            >
              −
            </button>
            <span className="w-14 text-center font-mono text-xs">{Math.round(zoom * 100)}%</span>
            <button
              onClick={() => setZoom((z) => Math.min(z + 0.25, 4))}
              className="px-2.5 py-1 rounded bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 font-bold"
              title="Zoom In (+)"
            >
              +
            </button>
            <div className="h-4 w-px bg-gray-300 dark:bg-gray-600 mx-1"></div>
            <button
              onClick={() => setRotation((r) => (r + 90) % 360)}
              className="px-3 py-1 rounded bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 text-xs flex items-center gap-1"
              title="Rotate 90° (R)"
            >
              <span>🔄</span> Rotate
            </button>
            <button
              onClick={() => {
                setZoom(1);
                setRotation(0);
                setPan({ x: 0, y: 0 });
              }}
              className="px-3 py-1 rounded bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 text-xs"
              title="Reset View"
            >
              Reset
            </button>
          </div>
        )}

        {/* Viewer Area */}
        <div className="flex-1 relative overflow-hidden bg-gray-900/90 flex items-center justify-center select-none">
          {loading && (
            <div className="flex flex-col items-center gap-3 text-white">
              <div className="w-10 h-10 border-4 border-white/20 border-t-white rounded-full animate-spin"></div>
              <p className="text-sm">Loading secure document preview...</p>
            </div>
          )}

          {error && (
            <div className="text-center p-6 bg-red-950/60 border border-red-800 rounded-xl max-w-md text-red-200">
              <span className="text-3xl block mb-2">⚠️</span>
              <p className="font-semibold">{error}</p>
              {downloadUrl && (
                <a
                  href={downloadUrl}
                  className="mt-4 inline-block px-4 py-2 bg-red-700 hover:bg-red-800 text-white rounded-lg text-sm font-medium transition"
                >
                  Download File Instead
                </a>
              )}
            </div>
          )}

          {!loading && !error && blobUrl && (
            <>
              {isPdf ? (
                <iframe
                  src={blobUrl}
                  title="PDF Document"
                  className="w-full h-full border-0 bg-white"
                />
              ) : (
                <div
                  className="w-full h-full flex items-center justify-center cursor-grab active:cursor-grabbing overflow-hidden"
                  onMouseDown={handleMouseDown}
                  onMouseMove={handleMouseMove}
                >
                  <img
                    src={blobUrl}
                    alt={fileName || "Document"}
                    style={{
                      transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom}) rotate(${rotation}deg)`,
                      transition: isDragging ? "none" : "transform 0.15s ease-out",
                    }}
                    className="max-w-[90%] max-h-[90%] object-contain pointer-events-none drop-shadow-2xl"
                    draggable={false}
                  />
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer shortcuts note */}
        <div className="px-6 py-2.5 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <span>
            {!isPdf ? "Keyboard shortcuts: +/- to zoom, R to rotate, drag to pan, Esc to close" : "Esc to close"}
          </span>
          <span>Sahayak Protected Document Viewer</span>
        </div>
      </div>
    </div>
  );
}

export default DocumentViewerModal;

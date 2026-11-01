import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import {
  fetchMyDocuments,
  deleteDocument,
  deleteAllDocuments,
  getChecklistFileUrl,
} from "../lib/api";
import DocumentViewerModal from "../components/DocumentViewerModal";

function MyDocuments() {
  const { t } = useTranslation();
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();

  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedService, setSelectedService] = useState("all");

  // Document Viewer Modal State
  const [activeViewerDoc, setActiveViewerDoc] = useState(null);

  // Bulk delete confirmation modal state
  const [showDeleteAllModal, setShowDeleteAllModal] = useState(false);
  const [isDeletingAll, setIsDeletingAll] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) {
      navigate("/login?next=/my-documents");
    }
  }, [user, authLoading, navigate]);

  const loadDocuments = () => {
    setLoading(true);
    setError(null);
    fetchMyDocuments()
      .then((data) => {
        setDocuments(data.documents || []);
      })
      .catch((err) => {
        console.error("Failed to load documents:", err);
        setError(err.message || "Unable to fetch your uploaded documents.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (user) {
      loadDocuments();
    }
  }, [user]);

  const handleDeleteSingle = async (docId) => {
    if (!window.confirm("Are you sure you want to delete this document?")) return;
    try {
      await deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err) {
      alert(err.message || "Failed to delete document.");
    }
  };

  const handleDeleteAll = async () => {
    setIsDeletingAll(true);
    try {
      await deleteAllDocuments();
      setDocuments([]);
      setShowDeleteAllModal(false);
    } catch (err) {
      alert(err.message || "Failed to delete all documents.");
    } finally {
      setIsDeletingAll(false);
    }
  };

  // Filter documents
  const filteredDocs = documents.filter((doc) => {
    const term = searchTerm.toLowerCase();
    const matchesSearch =
      !term ||
      (doc.chosen_option && doc.chosen_option.toLowerCase().includes(term)) ||
      (doc.requirement && doc.requirement.toLowerCase().includes(term)) ||
      (doc.service && doc.service.toLowerCase().includes(term)) ||
      (doc.file_name && doc.file_name.toLowerCase().includes(term));

    const matchesService = selectedService === "all" || doc.service === selectedService;

    return matchesSearch && matchesService;
  });

  const uniqueServices = Array.from(new Set(documents.map((d) => d.service)));

  const formatSize = (bytes) => {
    if (!bytes) return "0 B";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return "N/A";
    try {
      return new Date(isoStr).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoStr;
    }
  };

  if (authLoading || (!user && loading)) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 bg-gray-50 dark:bg-gray-900">
        <div className="w-10 h-10 border-4 border-brand-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header Breadcrumb & Actions */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gray-200 dark:border-gray-800">
          <div>
            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 mb-1">
              <Link to="/" className="hover:underline">Home</Link>
              <span>/</span>
              <span>My Documents</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900 dark:text-white flex items-center gap-3">
              <span>📁</span> My Documents
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Manage your uploaded identity and address records across all services securely.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {documents.length > 0 && (
              <button
                onClick={() => setShowDeleteAllModal(true)}
                className="px-4 py-2 rounded-xl border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 text-sm font-semibold transition flex items-center gap-1.5"
              >
                <span>🗑️</span> Delete All Documents
              </button>
            )}
            <Link
              to="/services"
              className="px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold shadow-sm transition"
            >
              + Upload for Service
            </Link>
          </div>
        </div>

        {/* Search & Filter Bar */}
        <div className="bg-white dark:bg-gray-800 p-4 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row gap-3 items-center justify-between">
          <div className="flex-1 w-full flex items-center gap-2 px-3.5 py-2 bg-gray-50 dark:bg-gray-700/60 rounded-xl border border-gray-300 dark:border-gray-600 focus-within:border-brand-500">
            <span className="text-gray-400">🔍</span>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by document type (Aadhaar, PAN), requirement, or service..."
              className="bg-transparent outline-none text-sm w-full"
            />
            {searchTerm && (
              <button onClick={() => setSearchTerm("")} className="text-gray-400 hover:text-gray-600 text-xs">
                ✕
              </button>
            )}
          </div>

          <div className="w-full sm:w-auto flex items-center gap-2">
            <span className="text-xs text-gray-500 whitespace-nowrap">Filter Service:</span>
            <select
              value={selectedService}
              onChange={(e) => setSelectedService(e.target.value)}
              className="px-3 py-2 bg-gray-50 dark:bg-gray-700 rounded-xl border border-gray-300 dark:border-gray-600 text-sm outline-none cursor-pointer"
            >
              <option value="all">All Services ({documents.length})</option>
              {uniqueServices.map((srv) => (
                <option key={srv} value={srv}>
                  {srv}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Content Area */}
        {loading ? (
          <div className="text-center py-20 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700">
            <div className="w-10 h-10 border-4 border-brand-600 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
            <p className="text-sm text-gray-500">Loading your documents...</p>
          </div>
        ) : error ? (
          <div className="p-6 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-2xl text-center text-red-700 dark:text-red-300">
            <p className="font-semibold">{error}</p>
            <button
              onClick={loadDocuments}
              className="mt-3 px-4 py-1.5 bg-red-600 text-white rounded-lg text-xs font-semibold"
            >
              Retry
            </button>
          </div>
        ) : filteredDocs.length === 0 ? (
          <div className="text-center py-16 px-4 bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 space-y-4">
            <span className="text-5xl block">📭</span>
            <h3 className="text-lg font-bold text-gray-800 dark:text-gray-200">
              {documents.length === 0 ? "No documents uploaded yet" : "No matching documents found"}
            </h3>
            <p className="text-sm text-gray-500 max-w-md mx-auto">
              {documents.length === 0
                ? "Select a government service and upload your required documents to check for spelling and date consistency."
                : "Try adjusting your search keywords or filter settings."}
            </p>
            {documents.length === 0 && (
              <Link
                to="/services"
                className="inline-block px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-semibold rounded-xl text-sm shadow-md transition"
              >
                Browse Services & Checklists
              </Link>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredDocs.map((doc) => {
              const fileUrl = getChecklistFileUrl(doc.service, "any", doc.variant, doc.requirement);
              const isPdf = doc.mime_type?.includes("pdf") || doc.file_name?.endsWith(".pdf");

              return (
                <div
                  key={doc.id}
                  className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-5 shadow-xs hover:shadow-md transition flex flex-col justify-between"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-2xl p-2 bg-brand-50 dark:bg-brand-950/60 rounded-xl text-brand-600 dark:text-brand-400">
                        {isPdf ? "📄" : "🖼️"}
                      </span>
                      <span className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                        {doc.service}
                      </span>
                    </div>

                    <div>
                      <h4 className="font-bold text-base text-gray-900 dark:text-white line-clamp-1">
                        {doc.chosen_option || doc.requirement}
                      </h4>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Requirement: {doc.requirement}
                      </p>
                    </div>

                    {/* Metadata badge */}
                    <div className="bg-gray-50 dark:bg-gray-700/40 p-2.5 rounded-xl space-y-1 text-xs">
                      <div className="flex justify-between text-gray-600 dark:text-gray-300">
                        <span>File:</span>
                        <span className="font-mono truncate max-w-[150px]">{doc.file_name || "Upload"}</span>
                      </div>
                      <div className="flex justify-between text-gray-600 dark:text-gray-300">
                        <span>Size:</span>
                        <span>{formatSize(doc.file_size_bytes)}</span>
                      </div>
                      <div className="flex justify-between text-gray-600 dark:text-gray-300">
                        <span>Uploaded:</span>
                        <span>{formatDate(doc.uploaded_at)}</span>
                      </div>
                    </div>

                    {/* OCR Summary pills */}
                    {doc.has_data && (
                      <div className="pt-1 flex flex-wrap gap-1 text-[11px]">
                        {doc.doc_name && (
                          <span className="px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900 truncate max-w-full">
                            👤 {doc.doc_name}
                          </span>
                        )}
                        {doc.doc_dob && (
                          <span className="px-2 py-0.5 rounded-md bg-green-50 dark:bg-green-950/40 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-900">
                            📅 {doc.doc_dob}
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="pt-4 border-t border-gray-100 dark:border-gray-700/80 mt-4 flex items-center justify-between gap-2">
                    <button
                      onClick={() =>
                        setActiveViewerDoc({
                          url: fileUrl,
                          name: doc.file_name,
                          title: doc.chosen_option || doc.requirement,
                          id: doc.id,
                        })
                      }
                      className="flex-1 py-1.5 px-3 rounded-xl bg-brand-50 hover:bg-brand-100 dark:bg-gray-700 dark:hover:bg-gray-600 text-brand-700 dark:text-brand-300 text-xs font-semibold transition flex items-center justify-center gap-1.5"
                    >
                      <span>👁️</span> View
                    </button>

                    <a
                      href={`${fileUrl}&download=1`}
                      download={doc.file_name || "document"}
                      className="p-2 rounded-xl border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs transition"
                      title="Download document"
                    >
                      ⬇️
                    </a>

                    <button
                      onClick={() => handleDeleteSingle(doc.id)}
                      className="p-2 rounded-xl border border-red-200 dark:border-red-900 text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40 text-xs transition"
                      title="Delete document"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Document Viewer Modal */}
      {activeViewerDoc && (
        <DocumentViewerModal
          isOpen={Boolean(activeViewerDoc)}
          onClose={() => setActiveViewerDoc(null)}
          fileUrl={activeViewerDoc.url}
          fileName={activeViewerDoc.name}
          requirementTitle={activeViewerDoc.title}
          onDelete={() => handleDeleteSingle(activeViewerDoc.id)}
        />
      )}

      {/* Delete All Confirmation Modal */}
      {showDeleteAllModal && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
        >
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 max-w-md w-full shadow-2xl border border-red-200 dark:border-red-900 text-center space-y-4">
            <span className="text-4xl block">⚠️</span>
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">
              Delete All Uploaded Documents?
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              This will permanently remove all {documents.length} documents and verification progress from your account. This action cannot be undone.
            </p>
            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={() => setShowDeleteAllModal(false)}
                className="flex-1 py-2 rounded-xl border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 text-sm font-semibold"
                disabled={isDeletingAll}
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAll}
                disabled={isDeletingAll}
                className="flex-1 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white text-sm font-semibold shadow-md"
              >
                {isDeletingAll ? "Deleting..." : "Yes, Delete All"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default MyDocuments;

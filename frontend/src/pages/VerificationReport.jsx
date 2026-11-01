import { useState, useEffect } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { fetchVerificationReport } from "../lib/api";

function VerificationReport() {
  const { slug } = useParams();
  const [searchParams] = useSearchParams();
  const variant = searchParams.get("variant") || "adult";
  const serviceName = decodeURIComponent(slug).replace(/-/g, " ");

  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    fetchVerificationReport(serviceName, variant)
      .then((data) => setReport(data))
      .catch((err) => {
        console.error("Failed to load verification report:", err);
        setError(err.message || "Failed to load report summary.");
      })
      .finally(() => setLoading(false));
  }, [serviceName, variant]);

  const handlePrint = () => {
    window.print();
  };

  const currentDate = new Date().toLocaleDateString("en-IN", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 bg-gray-50 dark:bg-gray-900">
        <div className="w-10 h-10 border-4 border-brand-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="min-h-screen p-6 bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-xl border border-red-200 dark:border-red-900 text-center max-w-md space-y-4">
          <span className="text-4xl block">⚠️</span>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Unable to Generate Report</h2>
          <p className="text-sm text-gray-600 dark:text-gray-300">{error || "Report data could not be retrieved."}</p>
          <Link
            to={`/checklist/${encodeURIComponent(serviceName)}`}
            className="inline-block px-4 py-2 bg-brand-600 text-white rounded-xl text-sm font-semibold hover:bg-brand-700"
          >
            Return to Checklist
          </Link>
        </div>
      </div>
    );
  }

  const {
    readinessScore,
    readinessLabel,
    documents = [],
    issues = [],
    comparisons = [],
    servicePortal,
  } = report;

  const scoreColor =
    readinessScore >= 90
      ? "text-green-600 bg-green-50 border-green-300 dark:bg-green-950/40 dark:border-green-800"
      : readinessScore >= 60
      ? "text-amber-600 bg-amber-50 border-amber-300 dark:bg-amber-950/40 dark:border-amber-800"
      : "text-red-600 bg-red-50 border-red-300 dark:bg-red-950/40 dark:border-red-800";

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-950 py-8 px-4 sm:px-6 lg:px-8 print:p-0 print:bg-white text-gray-900 dark:text-gray-100">
      <div className="max-w-4xl mx-auto space-y-6 print:space-y-4">
        {/* Top Action Bar (Hidden on print) */}
        <div className="flex items-center justify-between print:hidden bg-white dark:bg-gray-800 p-4 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-700">
          <Link
            to={`/checklist/${encodeURIComponent(serviceName)}?variant=${encodeURIComponent(variant)}`}
            className="inline-flex items-center gap-2 text-sm text-brand-600 hover:text-brand-700 dark:text-brand-400 font-semibold"
          >
            <span>←</span> Back to Checklist
          </Link>

          <div className="flex items-center gap-3">
            <button
              onClick={handlePrint}
              className="px-5 py-2 rounded-xl bg-brand-700 hover:bg-brand-800 text-white text-sm font-bold shadow-md transition flex items-center gap-2"
            >
              <span>🖨️</span> Print / Save PDF
            </button>
          </div>
        </div>

        {/* Printable Certificate Container */}
        <div className="bg-white dark:bg-gray-900 print:dark:bg-white rounded-3xl shadow-xl border border-gray-200 dark:border-gray-800 print:border-2 print:border-gray-300 p-6 sm:p-10 space-y-8 print:p-6 print:space-y-6">
          {/* Document Header */}
          <div className="border-b-2 border-gray-100 dark:border-gray-800 pb-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-2xl">🇮🇳</span>
                <span className="text-xs font-bold uppercase tracking-widest text-brand-700 dark:text-brand-400">
                  Sahayak Document Readiness System
                </span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900 dark:text-white mt-1">
                Document Verification Report
              </h1>
              <p className="text-sm text-gray-500 mt-1">
                Official Pre-Application Readiness Summary for <strong>{serviceName}</strong> ({variant})
              </p>
            </div>

            <div className="text-left sm:text-right text-xs text-gray-500 font-mono">
              <p>Date: {currentDate}</p>
              <p>Report ID: SHK-{Math.abs(serviceName.split("").reduce((a, b) => a + b.charCodeAt(0), 0))}-{variant.toUpperCase()}</p>
            </div>
          </div>

          {/* Readiness Score Card */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center bg-gray-50 dark:bg-gray-800/50 print:bg-gray-50 rounded-2xl p-6 border border-gray-200 dark:border-gray-700">
            <div className="text-center md:border-r border-gray-200 dark:border-gray-700 md:pr-6">
              <span className="text-xs font-bold uppercase text-gray-500 block mb-1">
                Readiness Score
              </span>
              <div className={`text-4xl font-extrabold px-4 py-2 rounded-xl inline-block border ${scoreColor}`}>
                {readinessScore}%
              </div>
              <p className="text-xs font-semibold mt-2">{readinessLabel}</p>
            </div>

            <div className="md:col-span-2 space-y-2 text-sm text-gray-700 dark:text-gray-300">
              <h3 className="font-bold text-gray-900 dark:text-white">Pre-Submission Assessment</h3>
              <p className="text-xs sm:text-sm">
                {readinessScore >= 90
                  ? "All required documents are uploaded and cross-verification indicates high consistency. You are ready to proceed with the official government application."
                  : "Inconsistencies or missing documents were detected across your records. Please review the correction steps below prior to final submission to avoid rejection."}
              </p>
              {servicePortal && (
                <div className="pt-2 text-xs">
                  <span className="font-semibold">Official Portal: </span>
                  <a
                    href={servicePortal.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-brand-600 dark:text-brand-400 font-semibold underline"
                  >
                    {servicePortal.name} ({servicePortal.url})
                  </a>
                </div>
              )}
            </div>
          </div>

          {/* Document Checklist Matrix */}
          <div className="space-y-3">
            <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <span>📋</span> Required Document Checklist
            </h3>
            <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700">
              <table className="w-full text-left text-xs sm:text-sm">
                <thead className="bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 uppercase font-semibold text-[11px]">
                  <tr>
                    <th className="py-2.5 px-4">Requirement</th>
                    <th className="py-2.5 px-4">Selected Document</th>
                    <th className="py-2.5 px-4">Extracted Name</th>
                    <th className="py-2.5 px-4">DOB</th>
                    <th className="py-2.5 px-4 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                  {documents.map((doc, idx) => (
                    <tr key={idx} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30">
                      <td className="py-3 px-4 font-semibold text-gray-800 dark:text-gray-200">
                        {doc.requirement}
                      </td>
                      <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                        {doc.chosenOption || "—"}
                      </td>
                      <td className="py-3 px-4 font-mono text-xs text-gray-700 dark:text-gray-300">
                        {doc.docName || "—"}
                      </td>
                      <td className="py-3 px-4 font-mono text-xs text-gray-700 dark:text-gray-300">
                        {doc.docDob || "—"}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                            doc.status === "Verified"
                              ? "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300"
                              : doc.status === "Mismatch"
                              ? "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300"
                              : doc.status === "Skipped"
                              ? "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300"
                              : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                          }`}
                        >
                          {doc.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Cross-Document Comparison Matrix */}
          {comparisons.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <span>🔍</span> Cross-Document Field Comparison Matrix
              </h3>
              <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700">
                <table className="w-full text-left text-xs sm:text-sm">
                  <thead className="bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 uppercase font-semibold text-[11px]">
                    <tr>
                      <th className="py-2.5 px-4">Field</th>
                      <th className="py-2.5 px-4">Document A</th>
                      <th className="py-2.5 px-4">Document B</th>
                      <th className="py-2.5 px-4 text-center">Result</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                    {comparisons.map((comp, idx) => (
                      <tr key={idx}>
                        <td className="py-3 px-4 font-semibold capitalize">{comp.field}</td>
                        <td className="py-3 px-4">
                          <span className="font-semibold text-xs block text-gray-500">{comp.docA}</span>
                          <span className="font-mono text-xs">{comp.valA || "—"}</span>
                        </td>
                        <td className="py-3 px-4">
                          <span className="font-semibold text-xs block text-gray-500">{comp.docB}</span>
                          <span className="font-mono text-xs">{comp.valB || "—"}</span>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span
                            className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                              comp.status === "match"
                                ? "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300"
                                : comp.status === "mismatch"
                                ? "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300"
                                : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                            }`}
                          >
                            {comp.status === "match" ? "Match" : comp.status === "mismatch" ? "Mismatch" : "Unable to Compare"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Actionable Correction Steps (If Mismatches Found) */}
          {issues.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-base font-bold text-red-700 dark:text-red-400 flex items-center gap-2">
                <span>🛠️</span> Required Correction Guidance
              </h3>
              <div className="space-y-3">
                {issues.map((iss, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-xl border border-red-200 dark:border-red-900 bg-red-50/50 dark:bg-red-950/20 space-y-2 text-xs sm:text-sm"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-red-800 dark:text-red-300">
                        {iss.field.toUpperCase()} difference between {iss.documents[0]} & {iss.documents[1]}
                      </span>
                      <span className="text-xs px-2 py-0.5 bg-red-200 dark:bg-red-900 text-red-800 dark:text-red-200 rounded font-semibold">
                        Decision: {iss.decision || "Pending"}
                      </span>
                    </div>

                    {iss.guidance && iss.guidance.map((g, gIdx) => (
                      <div key={gIdx} className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-200 dark:border-gray-700 text-xs mt-2">
                        <p className="font-bold text-gray-800 dark:text-gray-200">
                          To update {g.document_type || iss.documents[gIdx]}:
                        </p>
                        <ul className="list-disc pl-5 mt-1 space-y-0.5 text-gray-600 dark:text-gray-300">
                          {g.steps?.map((step, sIdx) => (
                            <li key={sIdx}>{step}</li>
                          ))}
                        </ul>
                        {g.official_portal && (
                          <p className="mt-2 text-brand-700 dark:text-brand-300">
                            Official Portal:{" "}
                            <a href={g.official_portal.url} target="_blank" rel="noopener noreferrer" className="underline font-semibold">
                              {g.official_portal.url}
                            </a>
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Legal Disclaimer Footer */}
          <div className="pt-6 border-t border-gray-200 dark:border-gray-800 text-[11px] text-gray-500 dark:text-gray-400 space-y-1">
            <p>
              <strong>Disclaimer:</strong> Sahayak is an independent document readiness and verification guidance tool. This report does not constitute an official government approval or certificate. Always submit your applications directly through designated Indian Government portals (.gov.in / .nic.in).
            </p>
            <p>Generated by Sahayak on {currentDate}. Privacy-first: no sensitive identity document data is shared with unauthorized third parties.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default VerificationReport;

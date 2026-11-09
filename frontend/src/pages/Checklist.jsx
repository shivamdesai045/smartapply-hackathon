import OcrReadiness from '../components/OcrReadiness';
import ApplicationReview from '../components/ApplicationReview';
import {fetchVerificationReport} from '../lib/api';
import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import {
  fetchChecklistVariants,
  fetchChecklist,
  fetchChecklistStatus,
  uploadChecklistFile,
  updateChecklistFields,
  getChecklistFileUrl,
  fetchFileBlob,
  fetchChecklistMismatches,
  postMismatchDecision,
  fetchCorrectionGuidancePair,
  rescanDocument,
  resumeDocumentJob,
  skipRequirement,
  deleteSessionData,
  fetchCorrectionSteps,
  saveCorrectionStep,
} from "../lib/api";
import DocumentViewerModal from "../components/DocumentViewerModal";
import MissingDocumentHelp from "../components/MissingDocumentHelp";
import MismatchResolutionCard from "../components/MismatchResolutionCard";
import { Eye } from "lucide-react";
import { getSessionId, initSession } from "../lib/session";
import { useTranslation } from "react-i18next";
import { getServiceNameFromSlug } from "../utils/slugify";
import { categories } from "../data/servicesData";
import { useAuth } from "../context/AuthContext";

const CHANNEL_LABELS = {
  online: "Fully online",
  in_person: "In-person visit required",
  online_then_appointment: "Online, then appointment",
  unknown: "Check official site",
};

export function maskAadhaar(val) {
  if (!val) return "";
  const s = String(val).trim();
  if (s.includes("XXXX")) return s;
  const digits = s.replace(/\s+/g, "");
  if (/^\d{12}$/.test(digits)) {
    return `XXXX XXXX ${digits.slice(8)}`;
  }
  return s;
}

function resolveServiceName(slug) {
  if (!slug) return null;
  const fromSlug = getServiceNameFromSlug(slug);
  if (fromSlug) return fromSlug;
  const normalized = slug.replace(/-/g, " ").toLowerCase();
  for (const cat of categories) {
    for (const service of cat.services) {
      if (service.name.toLowerCase() === normalized) {
        return service.name;
      }
    }
  }
  return null;
}

function CorrectionCard({ guidance, issueKey, completedSteps = [], onToggleStep }) {
  const stepsList = guidance.steps && guidance.steps.length > 0 ? guidance.steps : [
    `Visit official portal (${guidance.portal || "Designated Centre"})`,
    `Fill Form: ${guidance.form || "Correction / Update Form"}`,
    "Attach verified identity or date-of-birth proof",
    `Pay statutory fee (${guidance.fee || "Standard fee"}) & submit application`,
    `Track status (Turnaround: ${guidance.turnaround || "15 to 30 days"})`,
  ];

  const completedCount = stepsList.filter((_, idx) => completedSteps.includes(idx)).length;
  const progressPercent = Math.round((completedCount / stepsList.length) * 100);

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-xl p-4 bg-gray-50 dark:bg-gray-800 text-sm space-y-3">
      <div className="flex items-center justify-between">
        <div className="font-bold text-gray-800 dark:text-gray-200 capitalize">
          {guidance.document ? guidance.document.replace(/_/g, " ") : "Document Correction"}
        </div>
        <div className="text-xs px-2 py-0.5 rounded-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300">
          {CHANNEL_LABELS[guidance.channel] || guidance.channel}
        </div>
      </div>

      {guidance.portal && (
        <div className="text-xs text-gray-600 dark:text-gray-400">
          <span className="font-semibold text-gray-700 dark:text-gray-300">Portal: </span>
          {guidance.portal_url ? (
            <a
              href={guidance.portal_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-600 dark:text-brand-400 hover:underline font-semibold inline-flex items-center gap-0.5"
            >
              {guidance.portal} ↗
            </a>
          ) : (
            guidance.portal
          )}
        </div>
      )}
      {guidance.form && <div className="text-xs text-gray-600 dark:text-gray-400"><span className="font-semibold text-gray-700 dark:text-gray-300">Form:</span> {guidance.form}</div>}
      {guidance.fee && <div className="text-xs text-gray-600 dark:text-gray-400"><span className="font-semibold text-gray-700 dark:text-gray-300">Fee:</span> {guidance.fee}</div>}
      {guidance.turnaround && <div className="text-xs text-gray-600 dark:text-gray-400"><span className="font-semibold text-gray-700 dark:text-gray-300">Turnaround:</span> {guidance.turnaround}</div>}
      {guidance.notes && <div className="text-xs text-gray-500 dark:text-gray-400 bg-white/60 dark:bg-gray-900/40 p-2 rounded-lg border border-gray-200/60 dark:border-gray-700/60">{guidance.notes}</div>}

      {/* Step Tracker Checklist */}
      <div className="pt-2 border-t border-gray-200 dark:border-gray-700 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="font-bold text-gray-700 dark:text-gray-300">Correction Step Tracker</span>
          <span className="text-brand-600 dark:text-brand-400 font-semibold">{completedCount} of {stepsList.length} completed</span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 h-1.5 rounded-full overflow-hidden">
          <div className="bg-brand-600 h-full rounded-full transition-all duration-300" style={{ width: `${progressPercent}%` }}></div>
        </div>

        <div className="space-y-1.5 pt-1">
          {stepsList.map((st, sIdx) => {
            const isDone = completedSteps.includes(sIdx);
            return (
              <label key={sIdx} className="flex items-start gap-2 text-xs p-1 rounded hover:bg-white dark:hover:bg-gray-700/60 cursor-pointer transition">
                <input
                  type="checkbox"
                  checked={isDone}
                  onChange={(e) => onToggleStep && onToggleStep(issueKey, sIdx, e.target.checked)}
                  className="mt-0.5 rounded border-gray-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                />
                <span className={isDone ? "line-through text-gray-400 dark:text-gray-500" : "text-gray-700 dark:text-gray-200"}>
                  {st}
                </span>
              </label>
            );
          })}
        </div>
      </div>

      {guidance.portal_url && (
        <div className="pt-2 border-t border-gray-200 dark:border-gray-700 flex justify-end">
          <a
            href={guidance.portal_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-medium shadow-sm transition"
          >
            Visit Official Portal ↗
          </a>
        </div>
      )}
    </div>
  );
}

function OcrEditForm({ serviceName, sessionId, variant, requirement, reqData, onSaved }) {
  const rich = reqData.doc_fields || reqData.docFields || {};
  const type = (reqData.chosenOption || requirement || "").toLowerCase();
  const academic = /marksheet|ssc|hsc|10th|12th|certificate.*passing/.test(type);
  const keys = new Set(["name", "doc_number"]);
  const add = (items) => items.split(" ").forEach(k => keys.add(k));
  if (academic) add("father_name mother_name dob board exam_level exam_year roll_number seat_number certificate_number school_name issuing_authority issue_date");
  else if (/bill|rent|bank|passbook/.test(type)) add("address pincode mobile_number issue_date issuing_authority");
  else { add("father_name mother_name guardian_name dob gender");
    if (!/pan/.test(type)) add("address pincode");
    if (/aadhaar/.test(type)) add("mobile_number");
    if (/licen[cs]e/.test(type)) add("vehicle_classes guardian_name issuing_authority issue_date expiry_date");
    if (/passport|birth/.test(type)) add("place_of_birth");
    if (/passport|voter|ration/.test(type)) add("spouse_name");
    if (!/aadhaar|pan/.test(type)) add("issue_date expiry_date issuing_authority");
  }
  Object.entries(rich).forEach(([k,v]) => { if (v.value && k !== "document_type") keys.add(k); });
  const legacy = {name:reqData.docName,dob:reqData.docDob,address:reqData.docAddress,doc_number:reqData.docNumber};
  const [values, setValues] = useState(() => Object.fromEntries([...keys].map(k => {
    const v = rich[k]?.value ?? legacy[k] ?? "";
    return [k, typeof v === "object" ? v.number || "" : String(v)];
  })));
  const [changed, setChanged] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const label = k => k === "doc_number" ? "Document number" : k === "dob" ? "Date of birth (YYYY-MM-DD)" : k.replaceAll("_", " ");
  const save = async () => {
    setSaving(true); setError("");
    try {
      await updateChecklistFields(serviceName, sessionId, variant, requirement, {docFields:changed});
      onSaved();
    } catch (err) { setError(err.message || "Could not save corrections"); }
    finally { setSaving(false); }
  };
  return <div className="mt-3 space-y-3">
    <p className="text-xs text-gray-500">Correct the fields shown on this document. Only edited values are saved as confirmed.</p>
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {[...keys].map(k => <label key={k} className="text-xs capitalize text-gray-700 dark:text-gray-200">
        {label(k)}
        <input value={values[k] || ""} onChange={e => {setValues(v=>({...v,[k]:e.target.value}));setChanged(v=>({...v,[k]:e.target.value || null}));}}
          placeholder="Not shown / not detected" className="mt-1 w-full text-sm border border-gray-300 dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-700 dark:text-white" />
      </label>)}
    </div>
    {error && <p role="alert" className="text-sm text-red-500">{error}</p>}
    <button onClick={save} disabled={saving || !Object.keys(changed).length} className="bg-brand-600 text-white rounded px-4 py-2 disabled:opacity-50">{saving ? "Saving..." : "Save corrections"}</button>
  </div>;
}

function SecureDocumentPreview({ fileUrl, alt }) {
  const { t } = useTranslation();

  const [preview, setPreview] = useState({
    url: null,
    mime: "",
    loading: true,
    error: null,
  });

  useEffect(() => {
    let active = true;
    let objectUrl = null;

    setPreview({
      url: null,
      mime: "",
      loading: true,
      error: null,
    });

    fetchFileBlob(fileUrl)
      .then((blob) => {
        if (!active) return;

        objectUrl = URL.createObjectURL(blob);

        setPreview({
          url: objectUrl,
          mime: (blob.type || "").toLowerCase(),
          loading: false,
          error: null,
        });
      })
      .catch((error) => {
        if (!active) return;

        setPreview({
          url: null,
          mime: "",
          loading: false,
          error: error.message || t("doc_inline_error"),
        });
      });

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [fileUrl, t]);

  if (preview.loading) {
    return (
      <div role="status" className="p-4 text-center text-sm text-slate-500 dark:text-slate-300">
        {t("doc_inline_loading")}
      </div>
    );
  }

  if (preview.error) {
    return (
      <div role="alert" className="p-4 text-center text-sm text-red-600 dark:text-red-300">
        {t("doc_inline_error")}: {preview.error}
      </div>
    );
  }

  if (preview.mime.includes("pdf")) {
    return (
      <iframe
        src={preview.url}
        title={t("doc_inline_title")}
        className="h-full w-full border-0 bg-white"
      />
    );
  }

  if (preview.mime.startsWith("image/")) {
    return (
      <img
        src={preview.url}
        alt={alt || t("doc_inline_title")}
        className="max-h-full max-w-full object-contain"
        onError={() =>
          setPreview((old) => ({
            ...old,
            error: t("doc_inline_unavailable"),
          }))
        }
      />
    );
  }

  return (
    <p role="status" className="p-4 text-center text-sm text-slate-500 dark:text-slate-300">
      {t("doc_inline_unavailable")}
    </p>
  );
}

function RequirementRow({ serviceName, sessionId, variant, reqData, onUploaded, user }) {
  const { t } = useTranslation();
  const { openLoginModal } = useAuth();
  const [selectedOption, setSelectedOption] = useState(reqData.chosenOption || reqData.options[0]);
  const [viewerOpen, setViewerOpen] = useState(false);
  const [sideBySide, setSideBySide] = useState(false);
  const [warningDismissed, setWarningDismissed] = useState(false);
  const [uploading, setUploading] = useState(false);
  const documentRequest = useRef(null);
  useEffect(() => () => documentRequest.current?.abort(), []);
  const [ocrProgress, setOcrProgress] = useState("Reading document...");
  const [rescanning, setRescanning] = useState(false);
  const [skipping, setSkipping] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [lastOcr, setLastOcr] = useState(null);
  const [editingOcr, setEditingOcr] = useState(false);
  const [pdfPassword, setPdfPassword] = useState("");
  const isAadhaar = /aadh?aar|adhar/i.test(selectedOption || "");
  const uploadedCallback = useRef(onUploaded);
  uploadedCallback.current = onUploaded;
  useEffect(() => {
    if (!user) return;
    const controller = new AbortController();
    documentRequest.current = controller;
    resumeDocumentJob(serviceName, sessionId, variant, reqData.requirement, progress => {
      if (controller.signal.aborted) return;
      setRescanning(true);
      setOcrProgress(progress);
    }, controller.signal).then(result => {
      if (!result || controller.signal.aborted) return;
      setLastOcr(result.extracted || result.ocrExtracted);
      uploadedCallback.current();
    }).catch(err => {
      if (err.name !== "AbortError") setErrorMsg(err.message);
    }).finally(() => {
      if (documentRequest.current !== controller) return;
      documentRequest.current = null;
      setRescanning(false);
      setOcrProgress("");
    });
    return () => controller.abort();
  }, [serviceName, sessionId, variant, reqData.requirement, user?.id]);


  const isPhotoSig = reqData.compare === false || /photo|photograph|signature|thumb impression/i.test(reqData.requirement || "");
  const isSkipped = Boolean(reqData.skipped || reqData.chosenOption === "Not Applicable" || reqData.filePath === "SKIPPED");

  const handleFileChange = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    if (files.length > (isAadhaar ? 2 : 1)) {
      setErrorMsg("Select one document, or two photos for Aadhaar front and back.");
      e.target.value = "";
      return;
    }

    if (!user) {
      e.target.value = "";
      openLoginModal("Please log in to upload and scan documents.");
      return;
    }
    if (documentRequest.current) return;
    documentRequest.current = new AbortController();
    setUploading(true);
    setErrorMsg(null);
    try {
      const res = await uploadChecklistFile(serviceName, sessionId, variant, reqData.requirement, selectedOption, files, pdfPassword, setOcrProgress, documentRequest.current.signal);
      setLastOcr(res.extracted || res.ocrExtracted);
      onUploaded();
    } catch (err) {
      if (err.name !== "AbortError") setErrorMsg(err.message || "Upload failed");
    } finally {
      documentRequest.current = null;
      setOcrProgress("");
      setUploading(false);
      setPdfPassword("");
      e.target.value = "";
    }
  };

  const handleRescan = async () => {
    if (!user) {
      openLoginModal("Please log in to re-scan documents.");
      return;
    }
    if (documentRequest.current) return;
    documentRequest.current = new AbortController();
    setRescanning(true);
    setErrorMsg(null);
    try {
      const res = await rescanDocument(serviceName, sessionId, variant, reqData.requirement, pdfPassword, setOcrProgress, documentRequest.current.signal);
      setLastOcr(res.extracted || res.ocrExtracted);
      setEditingOcr(false);
      onUploaded();
    } catch (err) {
      if (err.name !== "AbortError") setErrorMsg(err.message || "Re-scan failed");
    } finally {
      documentRequest.current = null;
      setOcrProgress("");
      setRescanning(false);
      setPdfPassword("");
    }
  };

  const handleToggleSkip = async (skipState) => {
    setSkipping(true);
    setErrorMsg(null);
    try {
      await skipRequirement(serviceName, sessionId, variant, reqData.requirement, skipState);
      onUploaded();
    } catch (err) {
      setErrorMsg(err.message || "Failed to update requirement");
    } finally {
      setSkipping(false);
    }
  };

  const fieldConfs = reqData.fieldConfidence || (lastOcr && (lastOcr.fieldConfidence || lastOcr.fieldConfidences)) || {};
  const needsRev = reqData.needsReview || (lastOcr && lastOcr.needsReview) || {};

  const isFieldUnverified = (field, val) => {
    if (!val) return true;
    if (needsRev && needsRev[field] === true) return true;
    const conf = fieldConfs && fieldConfs[field];
    if (typeof conf === "number" && conf > 0 && conf < 0.70) return true;
    return false;
  };

  const ocrInfo = lastOcr || (reqData.uploaded ? {
    name: reqData.docName,
    dob: reqData.docDob,
    address: reqData.docAddress,
    doc_number: reqData.docNumber ? { type: "ID", number: reqData.docNumber } : null,
  } : null);

  const hasUnverifiedRequired = !isPhotoSig && !isSkipped && reqData.uploaded && !reqData.manuallyEdited && (
    !ocrInfo ||
    !ocrInfo.name ||
    isFieldUnverified("name", ocrInfo.name) ||
    (ocrInfo.dob && isFieldUnverified("dob", ocrInfo.dob)) ||
    (ocrInfo.address && isFieldUnverified("address", ocrInfo.address)) ||
    (needsRev && Object.values(needsRev).some((v) => v === true))
  );

  const foundNothing = ocrInfo && !ocrInfo.name && !ocrInfo.dob && !ocrInfo.address && !ocrInfo.doc_number;
  const viewUrl = reqData.uploaded && user && !isSkipped
    ? getChecklistFileUrl(
        serviceName,
        sessionId,
        variant,
        reqData.requirement
      )
    : null;
  const notSupported = ocrInfo && ocrInfo.ocrAttempted === false;

  const subjectLabel = reqData.subject && reqData.subject !== "applicant" ? reqData.subject : null;

  if (isSkipped) {
    return (
      <div className="border border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-4 bg-gray-50/70 dark:bg-gray-800/40 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <span className="w-6 h-6 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-500 flex items-center justify-center text-xs font-bold">
            -
          </span>
          <div>
            <div className="font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
              <span>{reqData.requirement}</span>
              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300">
                Not Applicable
              </span>
            </div>
            <div className="text-xs text-gray-400 mt-0.5">Marked as optional / not applicable for this application</div>
          </div>
        </div>
        <button
          onClick={() => handleToggleSkip(false)}
          disabled={skipping}
          className="text-xs px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 hover:bg-white dark:hover:bg-gray-700 text-brand-600 dark:text-brand-400 font-medium transition"
        >
          {skipping ? "Updating..." : "Provide Document Instead"}
        </button>
      </div>
    );
  }

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-white dark:bg-gray-800 shadow-sm">
      <div className="flex items-start gap-3 mb-3">
        <span
          className={`w-6 h-6 shrink-0 rounded-full flex items-center justify-center text-xs font-bold ${
            !reqData.uploaded
              ? "bg-gray-100 dark:bg-gray-700 text-gray-400"
              : hasUnverifiedRequired
              ? "bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300 border border-amber-300"
              : "bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300"
          }`}
          title={
            !reqData.uploaded
              ? "Not uploaded"
              : hasUnverifiedRequired
              ? "Fields need verification or review"
              : "All fields verified"
          }
        >
          {!reqData.uploaded ? "" : hasUnverifiedRequired ? "⚠" : "✓"}
        </span>
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="font-medium text-gray-800 dark:text-gray-100">{reqData.requirement}</div>
            {subjectLabel && (
              <span className={`text-[10px] uppercase font-semibold px-2 py-0.5 rounded ${
                subjectLabel === "parent" ? "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300" :
                subjectLabel === "deceased" ? "bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300" :
                "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300"
              }`}>
                {subjectLabel}
              </span>
            )}
            {isPhotoSig && (
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                Visual Proof
              </span>
            )}
            {viewUrl && (
              <div className="flex items-center gap-1.5 ml-auto">
                <button
    type="button"
    onClick={() => setViewerOpen(true)}
    aria-label={`${t("view")}: ${reqData.requirement}`}
    title={t("view")}
    className="inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-xl border border-indigo-200 bg-indigo-50 px-3 text-sm font-semibold text-indigo-700 hover:bg-indigo-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 dark:border-indigo-700 dark:bg-slate-700 dark:text-indigo-200"
  >
    <Eye size={18} aria-hidden="true" />
    <span>{t("view")}</span>
  </button>
                {!isPhotoSig && (
                  <button
                    type="button"
                    onClick={() => setSideBySide(!sideBySide)}
                    aria-pressed={sideBySide}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-lg border text-xs font-semibold transition ${
                      sideBySide
                        ? "bg-brand-50 border-brand-400 text-brand-700 dark:bg-brand-950 dark:border-brand-700 dark:text-brand-300"
                        : "border-gray-300 dark:border-gray-600 hover:bg-gray-50 text-gray-700 dark:text-gray-300"
                    }`}
                    title="Toggle desktop side-by-side review mode"
                  >
                    <span>◫</span> {sideBySide ? "Stacked Mode" : "Side-by-Side"}
                  </button>
                )}
              </div>
            )}
          </div>
          {reqData.uploaded && (
            <div className="text-xs text-gray-400 mt-0.5">
              Uploaded as "{reqData.chosenOption}" • {new Date(reqData.uploadedAt).toLocaleString("en-IN")}
            </div>
          )}
          {errorMsg && <div className="text-xs text-red-500 mt-1 font-medium">{errorMsg}</div>}
        </div>
      </div>

      <div className="pl-9 space-y-2">
        <select value={selectedOption} onChange={(e) => setSelectedOption(e.target.value)}
          className="w-full text-sm border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-white rounded px-3 py-2 outline-none focus:border-brand-500">
          {reqData.options.map((opt, i) => <option key={i} value={opt}>{opt}</option>)}
        </select>

        {isAadhaar && (
          <p className="text-xs text-gray-600 dark:text-gray-300">
            English text extraction: use upright, readable images. Select both front and back photos together, or one PDF/image containing both sides. Either side can come first.
          </p>
        )}
        <label className="block text-xs text-gray-600 dark:text-gray-300">
          PDF password (only if protected; enter before uploading or re-scanning)
          <input type="password" value={pdfPassword} onChange={(event) => setPdfPassword(event.target.value)}
            autoComplete="off" className="mt-1 block rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2" />
        </label>
        {(lastOcr?.doc_meta?.aadhaar_review_reasons || reqData.aadhaarReviewReasons || []).map((reason) => (
          <p key={reason} role="status" className="text-sm text-amber-700 dark:text-amber-300">{reason}</p>
        ))}
        <div className="flex items-center gap-2 flex-wrap">
          <label className="cursor-pointer inline-block text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded px-4 py-2 transition shadow-sm">
            {uploading || rescanning ? ocrProgress : reqData.uploaded ? t("replace_file") : t("upload_file")}
            <input type="file" className="hidden" accept=".pdf,.png,.jpg,.jpeg,.webp,.bmp,.tiff" multiple={isAadhaar} disabled={uploading || rescanning} onChange={handleFileChange} />
          </label>

          {(uploading || rescanning) && ocrProgress.startsWith("Queued") && (
            <button type="button" onClick={() => documentRequest.current?.abort()} className="text-sm underline">Cancel queued upload</button>
          )}
          {reqData.skippable && !reqData.uploaded && (
            <button
              type="button"
              onClick={() => handleToggleSkip(true)}
              disabled={uploading || skipping}
              className="text-xs px-3 py-2 border border-gray-300 dark:border-gray-600 rounded text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
            >
              {skipping ? "Updating..." : "Not Applicable (Skip)"}
            </button>
          )}

          {reqData.skippable && reqData.uploaded && (
            <button
              type="button"
              onClick={() => handleToggleSkip(true)}
              disabled={skipping}
              className="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:underline px-2 py-1"
            >
              Mark as Not Applicable
            </button>
          )}
        </div>

        {/* Uploaded state indicator for Photo / Signature slots */}
        {reqData.uploaded && isPhotoSig && (
          <div className="bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800 rounded px-3 py-2 text-xs text-emerald-800 dark:text-emerald-300 flex items-center justify-between">
            <span>✓ {reqData.requirement} uploaded successfully (No text comparison required)</span>
          </div>
        )}

        {/* Document Type Warning Banner */}
        {lastOcr?.documentTypeWarning && !warningDismissed && (
          <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-700 text-amber-900 dark:text-amber-200 text-xs flex items-start justify-between gap-2 animate-fade-in">
            <div className="flex items-start gap-2">
              <span className="text-base shrink-0">⚠️</span>
              <div>
                <p className="font-bold">Wrong Document Type Warning</p>
                <p className="mt-0.5">{lastOcr.documentTypeWarning}</p>
              </div>
            </div>
            <button
              onClick={() => setWarningDismissed(true)}
              className="text-amber-700 dark:text-amber-400 hover:text-amber-900 text-xs font-bold p-1"
              title="Dismiss warning"
            >
              ✕
            </button>
          </div>
        )}

        {/* Quality Score Badge */}
        {lastOcr?.quality && (
          <div className="flex items-center gap-2 flex-wrap text-xs">
            <span
              className={`px-2.5 py-0.5 rounded-full font-bold ${
                lastOcr.quality.score >= 80
                  ? "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300"
                  : lastOcr.quality.score >= 50
                  ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                  : "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300"
              }`}
            >
              Quality: {lastOcr.quality.score >= 80 ? "Good" : lastOcr.quality.score >= 50 ? "Fair" : "Poor"} ({lastOcr.quality.score}%)
            </span>
            {lastOcr.quality.tips && lastOcr.quality.tips.length > 0 && lastOcr.quality.score < 80 && (
              <span className="text-gray-500 dark:text-gray-400 text-[11px] truncate max-w-sm">
                💡 Tip: {lastOcr.quality.tips[0]}
              </span>
            )}
          </div>
        )}

        {/* Desktop Side-by-Side Review Pane */}
        {sideBySide && viewUrl && !isPhotoSig && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 p-3 bg-gray-50 dark:bg-gray-900/60 rounded-xl border border-gray-200 dark:border-gray-700">
            <div className="h-[70vh] min-h-96 rounded-lg overflow-auto border border-gray-200 dark:border-gray-700 bg-gray-900/10">
              <SecureDocumentPreview fileUrl={viewUrl} alt={reqData.chosenOption} />
            </div>
            <div className="flex flex-col justify-center space-y-2 text-xs">
              <span className="font-bold text-gray-700 dark:text-gray-300">Side-by-Side OCR Verification</span>
              {ocrInfo && (
                <div className="space-y-1 bg-white dark:bg-gray-800 p-2.5 rounded-lg border border-gray-200 dark:border-gray-700">
                  <p><strong>Name:</strong> {ocrInfo.name || "(Not detected)"}</p>
                  <p><strong>DOB:</strong> {ocrInfo.dob || "(Not detected)"}</p>
                  <p><strong>Address:</strong> {ocrInfo.address || "(Not detected)"}</p>
                  {ocrInfo.doc_number && <p><strong>ID Number:</strong> {maskAadhaar(ocrInfo.doc_number.number)}</p>}
                  {Object.entries(reqData.doc_fields || lastOcr?.doc_fields || {}).filter(([field]) => !["name", "dob", "address", "doc_number"].includes(field)).map(([field, entry]) => (
                    <div key={field} className="border-t py-2">
                      <strong className="capitalize">{field.replaceAll("_", " ")}: </strong>
                      <span>{entry.value || "Not detected"}</span>
                      {entry.value && <span className="block text-xs">{entry.user_verified ? "Confirmed by you" : entry.needs_review ? "Please confirm this value" : `OCR confidence: ${Math.round(entry.confidence * 100)}%`}</span>}
                    </div>
                  ))}
                </div>
              )}
              <button
                onClick={() => setEditingOcr(true)}
                className="w-fit text-brand-600 dark:text-brand-400 hover:underline font-semibold"
              >
                Wrong? Fix it in field editor →
              </button>
            </div>
          </div>
        )}

        {/* OCR feedback for identity documents */}
        {reqData.uploaded && !isPhotoSig && ocrInfo && !editingOcr && (
          <div className="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded px-3 py-2 text-xs text-gray-600 dark:text-gray-300">
            {notSupported && (t("file_invalid_type") || "Unsupported format. Please upload JPG, PNG, or PDF.")}
            {!notSupported && foundNothing && "Couldn't automatically read identity details from this document."}
            {!notSupported && !foundNothing && (
              <>
                <span className="font-semibold text-brand-700 dark:text-brand-400">OCR Extracted: </span>
                {ocrInfo.name && (
                  <span className="mr-2 inline-flex items-center gap-1">
                    <strong>Name:</strong> {ocrInfo.name}
                    {isFieldUnverified("name", ocrInfo.name) && (
                      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300 dark:bg-amber-900/50 dark:text-amber-300 dark:border-amber-700">
                        ⚠ Please verify
                      </span>
                    )}
                  </span>
                )}
                {isAadhaar && !ocrInfo.dob && <span className="mr-2 text-amber-700 dark:text-amber-300">DOB: Not detected — check the front side or correct it manually.</span>}
                {ocrInfo.dob && (
                  <span className="mr-2 inline-flex items-center gap-1">
                    <strong>DOB:</strong> {ocrInfo.dob}
                    {isFieldUnverified("dob", ocrInfo.dob) && (
                      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300 dark:bg-amber-900/50 dark:text-amber-300 dark:border-amber-700">
                        ⚠ Please verify
                      </span>
                    )}
                  </span>
                )}
                {ocrInfo.address && (
                  <span className="mr-2 inline-flex items-center gap-1">
                    <strong>Address:</strong> {ocrInfo.address}
                    {isFieldUnverified("address", ocrInfo.address) && (
                      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300 dark:bg-amber-900/50 dark:text-amber-300 dark:border-amber-700">
                        ⚠ Please verify
                      </span>
                    )}
                  </span>
                )}
                {ocrInfo.doc_number && (
                  <span className="mr-2 inline-flex items-center gap-1">
                    <span className="px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300 font-mono text-[11px]">
                      {ocrInfo.doc_number.type || "ID"}: {maskAadhaar(ocrInfo.doc_number.number)}
                    </span>
                    {isFieldUnverified("doc_number", ocrInfo.doc_number.number) && (
                      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300 dark:bg-amber-900/50 dark:text-amber-300 dark:border-amber-700">
                        ⚠ Please verify
                      </span>
                    )}
                  </span>
                )}
              </>
            )}
            {!notSupported && (
              <span className="inline-flex items-center gap-2 ml-2">
                <button onClick={() => setEditingOcr(true)} className="text-brand-600 dark:text-brand-400 hover:underline">
                  Wrong? Fix it
                </button>
                <span className="text-gray-300 dark:text-gray-600">|</span>
                <button
                  onClick={handleRescan}
                  disabled={rescanning || uploading}
                  className="text-blue-600 dark:text-blue-400 hover:underline"
                >
                  {rescanning ? ocrProgress : "Re-scan"}
                </button>
              </span>
            )}
          </div>
        )}

        {editingOcr && (
          <OcrEditForm
            serviceName={serviceName} sessionId={sessionId} variant={variant}
            requirement={reqData.requirement} reqData={reqData}
            onSaved={() => { setEditingOcr(false); setLastOcr(null); onUploaded(); }}
          />
        )}
      </div>

      {viewerOpen && (
        <DocumentViewerModal
          isOpen={viewerOpen}
          onClose={() => setViewerOpen(false)}
          fileUrl={viewUrl}
          fileName={reqData.chosenOption}
          requirementTitle={reqData.requirement}
          onDelete={async () => {
            // Reset uploaded status
            onUploaded();
          }}
        />
      )}
    </div>
  );
}

function PendingIssueCard({ serviceName, sessionId, variant, issue, onDecided, completedSteps = [], onToggleStep }) {
  const { t } = useTranslation();
  const [saving, setSaving] = useState(false);
  const decide = async (decision) => {
    setSaving(true);
    try {
      await postMismatchDecision(serviceName, sessionId, variant, issue.field, issue.documents, decision);
      onDecided();
    } finally {
      setSaving(false);
    }
  };
  const [docA, docB] = issue.documents;
  const isPossibleMismatch = issue.verdict === "possible_mismatch" || issue.result === "Possible Mismatch" || !issue.verdict;

  return (
    <div className={`border rounded-lg p-4 bg-white dark:bg-gray-800 shadow-sm ${
      isPossibleMismatch ? "border-amber-300 dark:border-amber-700" : "border-rose-300 dark:border-rose-700"
    }`}>
      <div className="flex items-center gap-2 mb-2">
        <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
          isPossibleMismatch
            ? "bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300"
            : "bg-rose-100 dark:bg-rose-900/40 text-rose-800 dark:text-rose-300"
        }`}>
          {isPossibleMismatch ? "Possible Mismatch" : "Mismatch Detected"}
        </span>
        <span className="text-xs text-gray-500 capitalize">Field: {issue.fieldName || issue.field}</span>
      </div>

      <div className="text-sm text-gray-800 dark:text-gray-200 mb-3 font-medium">
        {issue.explanation || issue.message || `Different values found between ${docA} and ${docB}`}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs bg-gray-50 dark:bg-gray-700/50 p-3 rounded mb-3 border border-gray-200 dark:border-gray-600">
        <div>
          <span className="text-gray-500 font-medium block mb-0.5">{docA}:</span>
          <span className="font-semibold text-gray-900 dark:text-gray-100">
            {maskAadhaar(issue.valA || issue.values?.[0] || "(Not detected)")}
          </span>
        </div>
        <div>
          <span className="text-gray-500 font-medium block mb-0.5">{docB}:</span>
          <span className="font-semibold text-gray-900 dark:text-gray-100">
            {maskAadhaar(issue.valB || issue.values?.[1] || "(Not detected)")}
          </span>
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-xs font-semibold text-gray-700 dark:text-gray-300">Select the correct record:</div>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => decide("doc_a_correct")} disabled={saving}
            className="text-xs px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200">
            {docA} is correct
          </button>
          <button onClick={() => decide("doc_b_correct")} disabled={saving}
            className="text-xs px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200">
            {docB} is correct
          </button>
          <button onClick={() => decide("neither_correct")} disabled={saving}
            className="text-xs px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200">
            Neither is correct
          </button>
          <button onClick={() => decide("ignored")} disabled={saving}
            className="text-xs px-3 py-1.5 rounded text-gray-500 hover:text-gray-700 hover:underline">
            Ignore (this is fine)
          </button>
        </div>
      </div>

      {issue.guidance && (
        <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
          <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">Correction Guidance:</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {issue.guidance.map((g, i) => (
              <CorrectionCard
                key={i}
                guidance={g}
                issueKey={issue.issueKey}
                completedSteps={completedSteps}
                onToggleStep={onToggleStep}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ConfirmedIssueCard({ issue, completedSteps = [], onToggleStep }) {
  const [docA, docB] = issue.documents;
  return (
    <div className="border border-amber-300 dark:border-amber-700 rounded-xl p-4 bg-amber-50/50 dark:bg-amber-950/20 text-sm space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/60 text-amber-800 dark:text-amber-200">
          Confirmed Issue
        </span>
        <span className="font-bold capitalize text-gray-900 dark:text-gray-100">{issue.fieldName || issue.field} mismatch</span>
      </div>
      <p className="text-xs text-gray-600 dark:text-gray-300">
        Discrepancy detected between <strong>{docA}</strong> and <strong>{docB}</strong>. Follow the statutory correction guidance below:
      </p>
      {issue.guidance && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {issue.guidance.map((g, i) => (
            <CorrectionCard
              key={i}
              guidance={g}
              issueKey={issue.issueKey}
              completedSteps={completedSteps}
              onToggleStep={onToggleStep}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function IgnoredIssueRow({ issue, onUndo }) {
  const [docA, docB] = issue.documents;
  return (
    <div className="flex items-center justify-between text-xs text-gray-400 py-1 px-2 rounded bg-gray-50 dark:bg-gray-800">
      <span>Dismissed: {issue.fieldName || issue.field} mismatch between {docA} and {docB}</span>
      <button onClick={onUndo} className="text-brand-600 hover:underline">Undo</button>
    </div>
  );
}

function SelfReportFallback({ availableDocs, onClose }) {
  const [docA, setDocA] = useState(availableDocs[0] || "");
  const [docB, setDocB] = useState(availableDocs[1] || "");
  const [field, setField] = useState("name");
  const [guidance, setGuidance] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFetchGuidance = async () => {
    setLoading(true);
    try {
      const res = await fetchCorrectionGuidancePair(docA, docB, field);
      setGuidance(res.guidance);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-white dark:bg-gray-800 mt-3">
      <h3 className="font-semibold text-gray-800 dark:text-gray-200 text-sm mb-3">Tell us what mismatches:</h3>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-3">
        <select value={docA} onChange={(e) => setDocA(e.target.value)}
          className="text-xs border rounded p-2 bg-white dark:bg-gray-700 dark:border-gray-600 dark:text-white">
          {availableDocs.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <select value={docB} onChange={(e) => setDocB(e.target.value)}
          className="text-xs border rounded p-2 bg-white dark:bg-gray-700 dark:border-gray-600 dark:text-white">
          {availableDocs.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <select value={field} onChange={(e) => setField(e.target.value)}
          className="text-xs border rounded p-2 bg-white dark:bg-gray-700 dark:border-gray-600 dark:text-white">
          <option value="name">Name</option>
          <option value="dob">Date of Birth</option>
          <option value="address">Address</option>
          <option value="doc_number">ID / Document Number</option>
        </select>
      </div>

      <div className="flex gap-2">
        <button onClick={handleFetchGuidance} disabled={loading || docA === docB}
          className="bg-brand-600 hover:bg-brand-700 text-white text-xs font-medium px-3 py-1.5 rounded disabled:opacity-50">
          {loading ? "Finding guidance..." : "Get Correction Steps"}
        </button>
        <button onClick={onClose}
          className="text-xs text-gray-500 hover:underline px-2 py-1.5">Cancel</button>
      </div>

      {guidance && (
        <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {guidance.map((g, i) => <CorrectionCard key={i} guidance={g} />)}
          </div>
        </div>
      )}
    </div>
  );
}

function MismatchCheckerStep({ serviceName, sessionId, variant, onBack }) {
  const [applicationReport,setApplicationReport]=useState(null);
  const [reviewError,setReviewError]=useState('');
  const openReview=async()=>{try{setReviewError('');setApplicationReport(await fetchVerificationReport(serviceName,variant));}catch(e){setReviewError(e.message);}};

  const { t } = useTranslation();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selfReportOpen, setSelfReportOpen] = useState(false);
  const [correctionSteps, setCorrectionSteps] = useState({});

  useEffect(() => {
    fetchCorrectionSteps(serviceName, variant)
      .then((res) => {
        if (res && res.steps) setCorrectionSteps(res.steps);
      })
      .catch((err) => console.warn("Failed to load steps:", err));
  }, [serviceName, variant]);

  const handleToggleStep = async (issueKey, stepIndex, isCompleted) => {
    try {
      await saveCorrectionStep(serviceName, variant, issueKey, stepIndex, isCompleted);
      setCorrectionSteps((prev) => {
        const cur = prev[issueKey] || [];
        const next = isCompleted ? [...cur, stepIndex] : cur.filter((s) => s !== stepIndex);
        return { ...prev, [issueKey]: next };
      });
    } catch (err) {
      console.error("Failed to save step:", err);
    }
  };

  const load = useCallback(() => {
    setLoading(true);
    fetchChecklistMismatches(serviceName, sessionId, variant)
      .then(setData)
      .finally(() => setLoading(false));
  }, [serviceName, sessionId, variant]);

  useEffect(() => { load(); }, [load]);

  const summary = data?.summary || {
    matches: 0,
    possibleMismatches: 0,
    mismatches: 0,
    unableToCompare: 0,
    totalComparisons: 0,
  };

  const anyUnverifiedFields = (data?.unverifiedFieldCount && data?.unverifiedFieldCount > 0) || !data?.clean;
  const isVerified = data?.verificationStatus === "verified" && !anyUnverifiedFields;
  const isPartial = data?.verificationStatus === "partially_verified";
  const isNotVerified = !isVerified && !isPartial && (data?.verificationStatus === "not_verified" || anyUnverifiedFields || (summary.mismatches === 0 && summary.possibleMismatches === 0));
  const _hasIssues = !isVerified && !isPartial && !isNotVerified;

  const getResultBadge = (result) => {
    switch (result) {
      case "Match":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-900/50 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            <span className="font-bold">✓</span> Match
          </span>
        );
      case "Possible Mismatch":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 dark:bg-amber-900/50 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
            <span className="font-bold">⚠</span> Possible Mismatch
          </span>
        );
      case "Mismatch":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-100 dark:bg-rose-900/50 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
            <span className="font-bold">✕</span> Mismatch
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700">
            <span className="font-bold">?</span> Unable to Compare
          </span>
        );
    }
  };

  if(applicationReport) return <ApplicationReview report={applicationReport} serviceName={serviceName} onBack={()=>setApplicationReport(null)} />;
  return (
    <div>
      <button onClick={onBack} className="text-sm text-brand-600 dark:text-brand-400 hover:underline mb-4 flex items-center gap-1">
        ← Back to Documents
      </button>
      <h1 className="text-2xl font-bold text-brand-700 dark:text-brand-400 mb-1">Mismatch Checker</h1>
      <p className="text-gray-600 dark:text-gray-400 mb-4">Comparing details extracted from your uploaded documents field by field.</p>

      <button onClick={openReview} disabled={loading} className="mb-4 rounded bg-brand-600 text-white px-5 py-3">Review details & apply online</button>
      {reviewError&&<p role="alert">{reviewError}</p>}
      {/* Notice / Legal OCR Disclaimer */}
      <div className="mb-6 p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 flex items-start gap-3">
        <span className="text-blue-600 dark:text-blue-400 text-lg">ℹ️</span>
        <p className="text-xs text-blue-800 dark:text-blue-200 leading-relaxed">
          <strong className="font-semibold">Important Notice:</strong> Automated OCR comparison assists in identifying potential discrepancies across documents. It does not constitute official identity verification or legal authentication. Always review your physical documents before final submission.
        </p>
      </div>

      {loading && (
        <div className="flex items-center gap-2 p-6 justify-center text-gray-500 dark:text-gray-400 text-sm">
          <div className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
          Scanning and comparing documents...
        </div>
      )}

      {!loading && data && !data.enoughData && (
        <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-lg p-5 text-sm text-amber-800 dark:text-amber-200">
          <div className="font-semibold text-base mb-1">At least 2 distinct documents needed</div>
          <p className="text-xs leading-relaxed text-amber-700 dark:text-amber-300">
            {data.message || "Please go back and upload at least 2 distinct comparable documents (such as Aadhaar Card + PAN Card or 10th Marksheet) to compare details across them."}
          </p>
          <button onClick={onBack} className="mt-3 inline-block px-4 py-1.5 text-xs font-medium rounded bg-brand-600 text-white hover:bg-brand-700">
            Go to Documents
          </button>
        </div>
      )}

      {!loading && data && data.enoughData && (() => {
        const issues = data.issues || [];
        const comparisons = data.comparisons || [];

        return (
          <>
            {/* Prominent Verification Status Banner */}
            <div className={`mb-6 p-5 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm ${
              isVerified
                ? "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-700 text-emerald-900 dark:text-emerald-100"
                : isPartial
                ? "bg-amber-50 dark:bg-amber-950/40 border-amber-300 dark:border-amber-700 text-amber-900 dark:text-amber-100"
                : "bg-rose-50 dark:bg-rose-950/40 border-rose-300 dark:border-rose-700 text-rose-900 dark:text-rose-100"
            }`}>
              <div className="flex items-start gap-3">
                <div className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-base shrink-0 mt-0.5 ${
                  isVerified
                    ? "bg-emerald-200 dark:bg-emerald-800 text-emerald-900 dark:text-emerald-100"
                    : isPartial
                    ? "bg-amber-200 dark:bg-amber-800 text-amber-900 dark:text-amber-100"
                    : "bg-rose-200 dark:bg-rose-800 text-rose-900 dark:text-rose-100"
                }`}>
                  {isVerified ? "✓" : isPartial ? "!" : "✕"}
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-base font-bold">
                      {isVerified
                        ? "All Documents Verified and Consistent"
                        : isPartial
                        ? "Partially Verified — Review Details"
                        : "Discrepancies Found — Action Required"}
                    </h2>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                      isVerified
                        ? "bg-emerald-200 dark:bg-emerald-800 text-emerald-900 dark:text-emerald-100"
                        : isPartial
                        ? "bg-amber-200 dark:bg-amber-800 text-amber-900 dark:text-amber-100"
                        : "bg-rose-200 dark:bg-rose-800 text-rose-900 dark:text-rose-100"
                    }`}>
                      {isVerified ? "Verified" : isPartial ? "Partially Verified" : "Issues Found"}
                    </span>
                  </div>
                  <p className="text-xs mt-1 leading-relaxed opacity-90">
                    {isVerified
                      ? "All extracted details across your uploaded documents match consistently. Your documents are ready for your application."
                      : isPartial
                      ? "Most fields match, but some could not be cross-verified or contain minor differences (e.g. initial or middle name variations)."
                      : "Differences in Name, Date of Birth, or other critical fields were detected between your documents. Review guidance below before submitting."}
                  </p>
                </div>
              </div>

              {data?.servicePortal && isVerified && (
                <a
                  href="#application-review" onClick={(e)=>{e.preventDefault();openReview();}}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow transition flex items-center gap-1.5"
                >
                  <span>Apply on {data.servicePortal.name}</span>
                  <span>↗</span>
                </a>
              )}
            </div>

            {/* Overview Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              <div className="p-3.5 rounded-lg border border-emerald-200 dark:border-emerald-800/80 bg-emerald-50 dark:bg-emerald-950/30">
                <div className="text-xs font-medium text-emerald-800 dark:text-emerald-300">Matches</div>
                <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-400 mt-1">{summary.matches}</div>
              </div>
              <div className="p-3.5 rounded-lg border border-amber-200 dark:border-amber-800/80 bg-amber-50 dark:bg-amber-950/30">
                <div className="text-xs font-medium text-amber-800 dark:text-amber-300">Possible Mismatches</div>
                <div className="text-2xl font-bold text-amber-700 dark:text-amber-400 mt-1">{summary.possibleMismatches}</div>
              </div>
              <div className="p-3.5 rounded-lg border border-rose-200 dark:border-rose-800/80 bg-rose-50 dark:bg-rose-950/30">
                <div className="text-xs font-medium text-rose-800 dark:text-rose-300">Mismatches</div>
                <div className="text-2xl font-bold text-rose-700 dark:text-rose-400 mt-1">{summary.mismatches}</div>
              </div>
              <div className="p-3.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60">
                <div className="text-xs font-medium text-gray-700 dark:text-gray-300">Unable to Compare</div>
                <div className="text-2xl font-bold text-gray-700 dark:text-gray-300 mt-1">{summary.unableToCompare}</div>
              </div>
            </div>

            {/* Field-by-Field Document Comparison Matrix */}
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Field-by-Field Document Comparison
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                Direct comparison of extracted fields across your uploaded records.
              </p>

              <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm bg-white dark:bg-gray-800">
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="bg-gray-50 dark:bg-gray-700/60 text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                      <th className="py-3 px-4">Field</th>
                      <th className="py-3 px-4">Document 1</th>
                      <th className="py-3 px-4">Document 2</th>
                      <th className="py-3 px-4">Result</th>
                      <th className="py-3 px-4">Details & Explanation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700/60">
                    {comparisons.map((c, idx) => (
                      <tr key={idx} className="hover:bg-gray-50/70 dark:hover:bg-gray-700/30 transition-colors">
                        <td className="py-3 px-4 font-semibold text-gray-800 dark:text-gray-200 whitespace-nowrap">
                          {c.fieldName || c.field}
                        </td>
                        <td className="py-3 px-4 max-w-xs">
                          <div className="text-[11px] text-gray-500 dark:text-gray-400 font-medium truncate">{c.docA}</div>
                          <div className={`font-mono text-xs mt-0.5 break-words ${
                            c.valA === "Not detected" ? "text-gray-400 italic" : "text-gray-900 dark:text-gray-100 font-medium"
                          }`}>
                            {maskAadhaar(c.valA)}
                          </div>
                        </td>
                        <td className="py-3 px-4 max-w-xs">
                          <div className="text-[11px] text-gray-500 dark:text-gray-400 font-medium truncate">{c.docB}</div>
                          <div className={`font-mono text-xs mt-0.5 break-words ${
                            c.valB === "Not detected" ? "text-gray-400 italic" : "text-gray-900 dark:text-gray-100 font-medium"
                          }`}>
                            {maskAadhaar(c.valB)}
                          </div>
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          {getResultBadge(c.result)}
                        </td>
                        <td className="py-3 px-4 text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
                          {c.explanation}
                          {c.similarity !== null && c.similarity !== undefined && (
                            <span className="text-[11px] text-gray-400 block mt-0.5">
                              Confidence / Similarity: {Math.round(c.similarity * 100)}%
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* When clean & verified: Direct Application Portal Banner */}
            {isVerified && (
              <div className="border border-emerald-200 dark:border-emerald-800 rounded-lg p-6 bg-emerald-50 dark:bg-emerald-950/20 mb-6 text-center shadow-sm">
                <div className="text-emerald-700 dark:text-emerald-300 font-bold text-lg mb-1">
                  ✓ Ready to Apply
                </div>
                <p className="text-xs text-emerald-800 dark:text-emerald-200 mb-4 max-w-lg mx-auto">
                  All required documents have been cross-checked without discrepancies. You can now proceed directly to the official government portal to submit your application.
                </p>
                {data?.servicePortal && (
                  <a
                    href="#application-review" onClick={(e)=>{e.preventDefault();openReview();}}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-5 py-2.5 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold rounded-lg shadow transition"
                  >
                    <span>Proceed to {data.servicePortal.name}</span>
                    <span>↗</span>
                  </a>
                )}
              </div>
            )}

            {/* User-led decision: confirm mismatch -> choose incorrect document -> correction guide */}
            {issues.length > 0 && (
              <section aria-labelledby="mismatch-resolution-title" className="mb-6 space-y-4">
                <div>
                  <h2 id="mismatch-resolution-title" className="text-lg font-semibold text-slate-900 dark:text-white">
                    {t("mf_section_heading")}
                  </h2>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                    {t("mf_section_intro")}
                  </p>
                </div>
                {issues.map((issue) => (
                  <MismatchResolutionCard
                    key={issue.issueKey}
                    issue={issue}
                    serviceName={serviceName}
                    sessionId={sessionId}
                    variant={variant}
                    onChanged={load}
                    onBack={onBack}
                  />
                ))}
              </section>
            )}

            {/* Optional manual self-report tool for subtle differences */}
            {!isVerified && (
              <div className="mt-4 mb-6">
                <button
                  onClick={() => setSelfReportOpen(!selfReportOpen)}
                  className="text-xs text-gray-500 hover:text-brand-600 dark:hover:text-brand-400 hover:underline flex items-center gap-1"
                >
                  <span>{selfReportOpen ? "▲ Close custom report" : "ℹ️ Have another discrepancy not shown above? Report manually"}</span>
                </button>
                {selfReportOpen && (
                  <SelfReportFallback availableDocs={data.documentsWithData} onClose={() => setSelfReportOpen(false)} />
                )}
              </div>
            )}

            {/* Re-check & Verification Report Action Bar */}
            <div className="mt-6 p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-3">
              <button
                onClick={onBack}
                className="w-full sm:w-auto px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 text-xs font-semibold text-gray-700 dark:text-gray-200 transition flex items-center justify-center gap-1.5"
              >
                <span>🔄</span> Re-check after correction
              </button>

              <Link
                to={`/report/${encodeURIComponent(serviceName)}?variant=${encodeURIComponent(variant)}`}
                className="w-full sm:w-auto px-5 py-2 rounded-xl bg-brand-700 hover:bg-brand-800 text-white text-xs font-bold shadow-sm transition flex items-center justify-center gap-2"
              >
                <span>📄</span> View Verification Certificate / Report →
              </Link>
            </div>

            {/* Official Portal Footer Reference */}
            {data?.servicePortal && !isVerified && (
              <div className="mt-6 mb-4 p-4 rounded-xl border border-brand-200 dark:border-brand-800 bg-brand-50/50 dark:bg-brand-950/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-lg">🏛️</span>
                    <h3 className="font-semibold text-sm text-brand-900 dark:text-brand-200">
                      Official Application Portal: {data.servicePortal.name}
                    </h3>
                  </div>
                  <p className="text-xs text-brand-700 dark:text-brand-300 mt-1 max-w-xl">
                    {data.servicePortal.description || `Submit your verified application directly on the official ${data.servicePortal.name}.`}
                  </p>
                </div>
                <a
                  href="#application-review" onClick={(e)=>{e.preventDefault();openReview();}}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-medium text-xs shadow transition-colors"
                >
                  <span>Apply on Official Portal</span>
                  <span>↗</span>
                </a>
              </div>
            )}
          </>
        );
      })()}
    </div>
  );
}

function Checklist() {
  const { slug } = useParams();
  const serviceName = resolveServiceName(slug);
  const sessionId = getSessionId();
  const { t } = useTranslation();
  const { user, openLoginModal } = useAuth();

  const [variants, setVariants] = useState([]);
  const [selectedVariant, setSelectedVariant] = useState(null);
  const [checklistData, setChecklistData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [step, setStep] = useState("docs");
  const [clearingSession, setClearingSession] = useState(false);

  // Initialize secure session on mount
  useEffect(() => {
    initSession().catch((err) => console.warn("Session init error:", err));
  }, []);

  // 1. Fetch available variants for this service
  useEffect(() => {
    if (!serviceName) {
      setLoading(false);
      return;
    }
    let isCancelled = false;
    setError(null);

    fetchChecklistVariants(serviceName)
      .then((res) => {
        if (isCancelled) return;
        let variantList = [];
        if (res && res.variantList && Array.isArray(res.variantList)) {
          variantList = res.variantList;
        } else if (res && res.variants) {
          if (Array.isArray(res.variants)) {
            variantList = res.variants;
          } else if (typeof res.variants === "object") {
            variantList = Object.entries(res.variants).map(([key, label]) => ({
              key,
              label,
            }));
          }
        }
        setVariants(variantList);
        const defaultKey = variantList.length > 0 ? variantList[0].key : "adult";
        setSelectedVariant(defaultKey);
      })
      .catch((err) => {
        if (isCancelled) return;
        console.error("Failed to load variants:", err);
        setSelectedVariant("adult");
      });

    return () => {
      isCancelled = true;
    };
  }, [serviceName]);

  // Refresh data without unmounting rows that own ongoing uploads/polling.
  const progressGeneration = useRef(0);
  const [refreshError, setRefreshError] = useState(null);
  const loadProgress = useCallback(async ({ background = false } = {}) => {
    if (!serviceName || !selectedVariant) return;
    const generation = ++progressGeneration.current;
    if (!background) { setLoading(true); setError(null); }
    setRefreshError(null);
    try {
      let data;
      if (user) {
        data = await fetchChecklistStatus(serviceName, sessionId, selectedVariant);
      } else {
        const checklist = await fetchChecklist(serviceName, selectedVariant);
        const requirements = (checklist.requirements || []).map(r => ({
          requirement: r.name, options: r.options, notes: r.notes,
          subject: r.subject || "applicant", compare: r.compare !== false,
          skippable: r.skippable || false, skipped: false,
          chosenOption: r.options[0], uploaded: false,
        }));
        data = { service: serviceName, variant: selectedVariant, requirements,
          uploadedCount: 0, comparableCount: 0, totalCount: requirements.length,
          complete: false, servicePortal: checklist.servicePortal || null };
      }
      if (generation === progressGeneration.current) setChecklistData(data);
    } catch (err) {
      if (generation === progressGeneration.current) {
        if (background) setRefreshError("Could not refresh progress. Your other document jobs are still running.");
        else setError(err.message || "Unable to load checklist requirements.");
      }
    } finally {
      if (generation === progressGeneration.current) setLoading(false);
    }
  }, [serviceName, sessionId, selectedVariant, user]);
  const refreshProgress = useCallback(() => loadProgress({ background: true }), [loadProgress]);
  useEffect(() => {
    loadProgress();
    return () => { progressGeneration.current++; };
  }, [loadProgress]);

  const handleClearSession = async () => {
    if (!window.confirm(t("confirm_clear_session") || "Are you sure you want to delete all uploaded files and session records?")) {
      return;
    }
    setClearingSession(true);
    try {
      await deleteSessionData(sessionId);
      await loadProgress();
    } catch (err) {
      console.error("Failed to clear session:", err);
    } finally {
      setClearingSession(false);
    }
  };

  if (!serviceName) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 text-center text-gray-600 dark:text-gray-300">
        <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100 mb-2">Service Not Found</h2>
        <p className="text-sm mb-4">The service "{slug}" was not found or does not have a checklist defined.</p>
        <Link to="/services" className="inline-block bg-brand-600 text-white text-xs font-semibold px-4 py-2 rounded-lg hover:bg-brand-700">
          Back to Services
        </Link>
      </div>
    );
  }

  const reqList = checklistData?.requirements || checklistData?.status || [];
  const totalCount = checklistData?.totalCount ?? reqList.length;
  const uploadedCount = Math.min(checklistData?.uploadedCount ?? reqList.filter((r) => r.uploaded).length, totalCount);
  const comparableCount = Math.min(checklistData?.comparableCount ?? 0, totalCount);
  const readyCount = Math.min(checklistData?.readyCount ?? comparableCount, totalCount);

  if (step === "mismatch" && selectedVariant) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <MismatchCheckerStep
          serviceName={serviceName}
          sessionId={sessionId}
          variant={selectedVariant}
          onBack={() => { setStep("docs"); loadProgress(); }}
        />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div>
          <Link to="/services" className="text-sm text-brand-600 dark:text-brand-400 hover:underline mb-1 inline-block">
            ← Back to Services
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {serviceName} Checklist
          </h1>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            Upload your documents below to verify completeness and automatically check for discrepancies across records.
          </p>
          <OcrReadiness />
          {checklistData?.servicePortal && (
            <div className="mt-1.5">
              <a
                href={checklistData.servicePortal.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-[11px] text-brand-600 dark:text-brand-400 hover:underline font-medium"
              >
                <span>Official Portal: {checklistData.servicePortal.name}</span>
                <span>↗</span>
              </a>
            </div>
          )}
        </div>

        {variants && variants.length > 1 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">Applicant Type:</span>
            <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-1 border border-gray-200 dark:border-gray-700">
              {variants.map((v) => (
                <button
                  key={v.key}
                  onClick={() => setSelectedVariant(v.key)}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                    selectedVariant === v.key
                      ? "bg-white dark:bg-gray-700 text-brand-600 dark:text-brand-400 shadow-sm font-semibold"
                      : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
                  }`}
                >
                  {v.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/80 rounded-lg border border-gray-200 dark:border-gray-700 mb-6 gap-4">
        <div>
          <div className="text-sm font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
            <span>Document Progress: {uploadedCount} of {totalCount} completed</span>
            {comparableCount > 0 && (
              <span className="text-xs font-normal text-gray-500 dark:text-gray-400">
                ({comparableCount} comparable)
              </span>
            )}
          </div>
          <div className="w-48 bg-gray-200 dark:bg-gray-700 h-2 rounded-full mt-2 overflow-hidden">
            <div
              className="bg-brand-600 h-full rounded-full transition-all duration-300"
              style={{ width: `${totalCount > 0 ? (uploadedCount / totalCount) * 100 : 0}%` }}
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          {uploadedCount > 0 && (
            <button
              onClick={handleClearSession}
              disabled={clearingSession}
              className="px-3 py-2 text-xs font-medium text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-800/60 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
              title="Delete all uploaded files and progress for this session"
            >
              {clearingSession ? "Clearing..." : "Clear Uploads"}
            </button>
          )}

          <button
            onClick={() => {
              if (!user) {
                openLoginModal("Please log in to check your documents for mismatches.");
                return;
              }
              setStep("mismatch");
            }}
            className={`px-4 py-2 text-sm font-medium rounded-lg shadow-sm transition-colors ${
              comparableCount >= 2 || !user
                ? "bg-brand-600 hover:bg-brand-700 text-white cursor-pointer"
                : "bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed"
            }`}
            disabled={user && comparableCount < 2}
            title={
              comparableCount < 2
                ? "Upload at least 2 distinct comparable documents (e.g. Aadhaar + PAN or Marksheet) to check mismatches"
                : "Check documents for mismatches"
            }
          >
            Check Mismatches ({Math.min(comparableCount, Math.min(2, totalCount))}/{Math.min(2, totalCount)} ready) →
          </button>
        </div>
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center py-16 gap-3">
          <div className="w-8 h-8 border-3 border-brand-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-500 dark:text-gray-400 text-sm">
            Loading checklist requirements...
          </p>
        </div>
      )}

      {error && !loading && (
        <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center my-6">
          <h2 className="text-base font-semibold text-red-700 dark:text-red-400 mb-1">
            Unable to load requirements
          </h2>
          <p className="text-xs text-red-600 dark:text-red-300 mb-4">{error}</p>
          <button
            onClick={loadProgress}
            className="inline-block bg-brand-600 hover:bg-brand-700 text-white font-medium px-4 py-2 rounded-lg text-xs transition shadow-sm"
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && checklistData && reqList.length === 0 && (
        <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-8 text-center text-gray-500 dark:text-gray-400 text-sm">
          No document requirements found for this category.
        </div>
      )}

      {!loading && !error && reqList.some(
        (r) => !r.uploaded && !r.skipped
      ) && (
        <MissingDocumentHelp requirements={reqList} />
      )}

      {refreshError && <p role="status" className="text-amber-700">{refreshError}</p>}
      {!loading && !error && reqList.length > 0 && (
        <div className="space-y-4">
          {reqList.map((req, idx) => (
            <RequirementRow
              key={`${serviceName}:${sessionId}:${selectedVariant}:${user?.id || "guest"}:${req.requirement || idx}`}
              serviceName={serviceName}
              sessionId={sessionId}
              variant={selectedVariant}
              reqData={req}
              onUploaded={refreshProgress}
              user={user}
            />
          ))}
        </div>
      )}

      {/* Dev-only Diagnostic View */}
    </div>
  );
}

export default Checklist;

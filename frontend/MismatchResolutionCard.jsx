import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle, ArrowUpRight, CheckCircle2, FilePenLine, RotateCcw } from "lucide-react";
import { postMismatchDecision } from "../lib/api";

// A mismatch is a comparison warning, not proof that either original document is wrong.
export default function MismatchResolutionCard({ issue, serviceName, sessionId, variant, onChanged, onBack }) {
  const { t } = useTranslation();
  const [step, setStep] = useState("review");
  const [incorrectDocument, setIncorrectDocument] = useState(issue.incorrectDocument || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setStep("review");
    setIncorrectDocument(issue.incorrectDocument || "");
    setError("");
  }, [issue.issueKey, issue.decision, issue.incorrectDocument]);

  const save = async (decision, chosenDocument = null) => {
    setSaving(true);
    setError("");
    try {
      await postMismatchDecision(
        serviceName, sessionId, variant, issue.field,
        issue.documents, decision, chosenDocument
      );
      await onChanged();
    } catch (err) {
      setError(err.message || t("mf_save_error"));
    } finally {
      setSaving(false);
    }
  };

  const [docA, docB] = issue.documents;
  const values = [issue.valA ?? issue.values?.[0], issue.valB ?? issue.values?.[1]];
  const selectedGuide = issue.guidance;
  const isConfirmed = issue.decision === "confirmed" && issue.incorrectDocument;
  const hasDecision = issue.decision && issue.decision !== "pending";

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800 sm:p-6" aria-label={`${issue.fieldName || issue.field}: ${t("mf_difference")}`}>
      <div className="flex flex-wrap items-center gap-2">
        <AlertTriangle aria-hidden="true" className="text-amber-700 dark:text-amber-300" size={20} />
        <h3 className="text-base font-semibold text-slate-900 dark:text-white">{issue.fieldName || issue.field}</h3>
        <span className="rounded-lg bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-900 dark:bg-amber-950 dark:text-amber-200">{t("mf_difference")}</span>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{t("mf_compare_notice")}</p>
      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {[docA, docB].map((doc, index) => (
          <div key={index} className="min-w-0 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-600 dark:bg-slate-900">
            <p className="text-sm font-semibold text-slate-800 dark:text-white">{doc}</p>
            <p className="mt-1 break-words text-sm text-slate-700 dark:text-slate-200">{issue.field === "doc_number" ? t("mf_sensitive") : (values[index] || t("mf_not_detected"))}</p>
          </div>
        ))}
      </div>

      {!hasDecision && step === "review" && (
        <div className="mt-5 space-y-3">
          <p className="font-semibold text-slate-900 dark:text-white">{t("mf_confirm_question")}</p>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => setStep("choose")} disabled={saving} className="min-h-11 rounded-xl bg-indigo-600 px-4 py-2 font-semibold text-white hover:bg-indigo-700 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-indigo-600">{t("mf_yes")}</button>
            <button type="button" onClick={() => save("ocr_error")} disabled={saving} className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 font-medium text-slate-900 hover:bg-slate-50 focus-visible:outline-3 focus-visible:outline-indigo-600 dark:border-slate-500 dark:text-white dark:hover:bg-slate-700">{t("mf_ocr_wrong")}</button>
            <button type="button" onClick={() => save("ignored")} disabled={saving} className="min-h-11 rounded-xl border border-slate-300 px-4 py-2 font-medium text-slate-900 hover:bg-slate-50 focus-visible:outline-3 focus-visible:outline-indigo-600 dark:border-slate-500 dark:text-white dark:hover:bg-slate-700">{t("mf_acceptable")}</button>
          </div>
        </div>
      )}

      {(!hasDecision && step === "choose" || (isConfirmed && step === "choose")) && (
        <fieldset className="mt-5 space-y-3">
          <legend className="font-semibold text-slate-900 dark:text-white">{t("mf_which_wrong")}</legend>
          <p className="text-sm text-slate-600 dark:text-slate-300">{t("mf_which_hint")}</p>
          {issue.documents.map((doc) => (
            <label key={doc} className="flex min-h-11 cursor-pointer items-center gap-3 rounded-xl border border-slate-300 p-3 text-sm text-slate-900 dark:border-slate-600 dark:text-white">
              <input type="radio" name={`incorrect-${issue.issueKey}`} value={doc} checked={incorrectDocument === doc} onChange={() => setIncorrectDocument(doc)} className="h-4 w-4 accent-indigo-600" />
              <span>{doc}</span>
            </label>
          ))}
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={!incorrectDocument || saving} onClick={() => save("confirmed", incorrectDocument)} className="min-h-11 rounded-xl bg-indigo-600 px-4 py-2 font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50">{saving ? t("mf_saving") : t("mf_show_steps")}</button>
            <button type="button" onClick={() => setStep("review")} className="min-h-11 rounded-xl px-3 text-slate-700 underline dark:text-slate-200">{t("mf_back")}</button>
          </div>
        </fieldset>
      )}

      {isConfirmed && step !== "choose" && (
        <section className="mt-5 rounded-xl border border-indigo-200 bg-indigo-50 p-4 dark:border-indigo-800 dark:bg-indigo-950/40" aria-label={t("mf_guidance_heading")}>
          <div className="flex items-start gap-2">
            <FilePenLine size={21} className="mt-0.5 shrink-0 text-indigo-700 dark:text-indigo-300" aria-hidden="true" />
            <div>
              <h4 className="font-semibold text-slate-900 dark:text-white">{t("mf_guidance_heading")}: {issue.incorrectDocument}</h4>
              <p className="mt-1 text-sm text-slate-700 dark:text-slate-200">{t("mf_confirmed_note")}</p>
            </div>
          </div>
          <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm leading-6 text-slate-800 dark:text-slate-100">
            <li>{t("mf_step1")}</li>
            <li>{selectedGuide?.form ? `${t("mf_step2_form")}: ${selectedGuide.form}` : t("mf_step2_generic")}</li>
            <li>{t("mf_step3")}</li>
            <li>{t("mf_step4")}</li>
          </ol>
          {selectedGuide?.notes && !selectedGuide?.needs_verification && (
            <p className="mt-3 rounded-lg border border-indigo-100 bg-white/80 p-3 text-sm leading-6 text-slate-700 dark:border-indigo-800 dark:bg-slate-900/70 dark:text-slate-200">{selectedGuide.notes}</p>
          )}
          {selectedGuide?.needs_verification && (
            <p className="mt-3 text-sm text-amber-900 dark:text-amber-200">{t("mf_generic_notice")}</p>
          )}
          <p className="mt-3 text-xs leading-5 text-slate-600 dark:text-slate-300">{t("mf_fees_notice")}</p>
          {selectedGuide?.portal_url && (
            <a href={selectedGuide.portal_url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-flex min-h-11 items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-indigo-600">
              {t("mf_open_portal")} <ArrowUpRight size={17} aria-hidden="true" />
            </a>
          )}
          <div className="mt-4 flex flex-wrap gap-3">
            <button type="button" onClick={() => setStep("choose")} className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-indigo-700 underline dark:text-indigo-300"><FilePenLine size={16} aria-hidden="true" />{t("mf_change_doc")}</button>
            <button type="button" onClick={onBack} className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-indigo-700 underline dark:text-indigo-300"><RotateCcw size={16} aria-hidden="true" />{t("mf_reupload")}</button>
          </div>
        </section>
      )}

      {hasDecision && !isConfirmed && (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-slate-100 p-3 dark:bg-slate-700">
          <div className="flex items-center gap-2 text-sm text-slate-800 dark:text-white">
            <CheckCircle2 size={19} aria-hidden="true" className="text-indigo-600 dark:text-indigo-300" />
            {issue.decision === "ocr_error" ? t("mf_ocr_status") : issue.decision === "confirmed" ? t("mf_choose_again") : t("mf_dismissed")}
          </div>
          <div className="flex flex-wrap gap-2">
            {issue.decision === "ocr_error" && <button type="button" onClick={onBack} className="min-h-11 rounded-lg px-3 text-sm font-semibold text-indigo-700 underline dark:text-indigo-300">{t("mf_edit_ocr")}</button>}
            <button type="button" disabled={saving} onClick={() => save("pending")} className="min-h-11 rounded-lg px-3 text-sm font-semibold text-indigo-700 underline dark:text-indigo-300">{t("mf_reconsider")}</button>
          </div>
        </div>
      )}
      {error && <p role="alert" className="mt-3 text-sm font-medium text-red-700 dark:text-red-300">{error}</p>}
    </article>
  );
}

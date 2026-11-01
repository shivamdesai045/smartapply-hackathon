
import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ArrowRight,
  ExternalLink,
  FileQuestion,
  HelpCircle,
  X,
} from "lucide-react";

import { useServices } from "../hooks/useServices";
import { slugify } from "../utils/slugify";

const aliasRules = [
  [/aadhaar/i, "Aadhaar Card"],
  [/\bpan card\b/i, "PAN Card"],
  [/voter id|epic card/i, "Voter ID"],
  [/birth certificate/i, "Birth Certificate"],
  [/death certificate/i, "Death Certificate"],
  [/ration card/i, "Ration Card"],
  [/driving licen[cs]e/i, "Driving Licence"],
  [/^passport$/i, "Passport"],
  [/registration certificate \(rc\)/i, "Vehicle Registration (RC)"],
];

const sources = [
  {
    match:
      /income certificate|caste certificate|ews certificate|non.?creamy|domicile certificate|residence certificate/i,
    url: "https://aaplesarkar.mahaonline.gov.in/en/CommonForm/CitizenServices_RTS",
    label: "Aaple Sarkar",
    regional: true,
  },
  {
    match: /7\/12|8a extract|land record|khasra|khatauni/i,
    url: "https://mahabhumi.gov.in/",
    label: "Mahabhumi",
    regional: true,
  },
  {
    match:
      /marksheet|mark sheet|academic certificate|10th certificate|12th certificate/i,
    url: "https://nad.digilocker.gov.in/students",
    label: "DigiLocker / NAD",
    regional: false,
  },
];

function findService(option, data) {
  const services = (data?.categories ?? []).flatMap(
    (category) => category.services ?? []
  );

  const normalize = (value) =>
    String(value)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, " ")
      .trim();

  const direct = services.find(
    (service) => normalize(service.name) === normalize(option)
  );

  if (direct) return direct;

  const rule = aliasRules.find(([regex]) => regex.test(option));

  return rule
    ? services.find((service) => service.name === rule[1])
    : undefined;
}

export default function MissingDocumentHelp({
  requirements = [],
}) {
  const { t } = useTranslation();
  const { data, loading } = useServices();

  const [open, setOpen] = useState(false);
  const [requirementName, setRequirementName] = useState("");
  const [documentName, setDocumentName] = useState("");

  const missing = requirements.filter(
    (requirement) => !requirement.uploaded && !requirement.skipped
  );

  if (missing.length === 0) return null;

  const selectedRequirement =
    missing.find(
      (requirement) => requirement.requirement === requirementName
    ) ?? missing[0];

  const accepted = selectedRequirement.options ?? [];

  const selectedDocument = accepted.includes(documentName)
    ? documentName
    : accepted[0] ?? "";

  const service = !loading
    ? findService(selectedDocument, data)
    : undefined;

  const source = service
    ? undefined
    : sources.find((item) => item.match.test(selectedDocument));

  const notApplicable =
    /not applicable|general category/i.test(selectedDocument);

  const localDocument =
    /photo|photograph|signature|thumb impression|bank passbook|salary slip|rent agreement|electricity bill|water bill|hospital record|school id|college id|admission receipt|insurance policy/i.test(
      selectedDocument
    );

  const directory =
    "https://www.india.gov.in/services/services-by-category";

  return (
    <section
      aria-labelledby="missing-help-title"
      className="mb-6 rounded-2xl border border-indigo-200 bg-white p-4 shadow-sm dark:border-indigo-800 dark:bg-slate-800 sm:p-5"
    >
      <button
        type="button"
        onClick={() => setOpen((previous) => !previous)}
        aria-expanded={open}
        aria-controls="missing-help-panel"
        className="flex min-h-11 w-full items-center gap-3 rounded-xl text-left text-indigo-700 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 dark:text-indigo-300"
      >
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-indigo-50 dark:bg-indigo-950">
          <HelpCircle size={23} aria-hidden="true" />
        </span>

        <span className="flex-1">
          <span
            id="missing-help-title"
            className="block text-base font-semibold"
          >
            {t("md_title")}
          </span>

          <span className="block text-sm font-normal text-slate-600 dark:text-slate-300">
            {t("md_subtitle")}
          </span>
        </span>

        {open ? (
          <X size={21} aria-hidden="true" />
        ) : (
          <ArrowRight size={21} aria-hidden="true" />
        )}
      </button>

      {open && (
        <div
          id="missing-help-panel"
          className="mt-5 border-t border-slate-200 pt-5 dark:border-slate-700"
        >
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block text-sm font-semibold text-slate-800 dark:text-slate-100">
              {t("md_requirement")}

              <select
                value={selectedRequirement.requirement}
                onChange={(event) => {
                  setRequirementName(event.target.value);
                  setDocumentName("");
                }}
                className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-base font-normal text-slate-900 focus-visible:outline-3 focus-visible:outline-indigo-600 dark:border-slate-600 dark:bg-slate-900 dark:text-white"
              >
                {missing.map((requirement) => (
                  <option
                    key={requirement.requirement}
                    value={requirement.requirement}
                  >
                    {requirement.requirement}
                  </option>
                ))}
              </select>
            </label>

            <label className="block text-sm font-semibold text-slate-800 dark:text-slate-100">
              {t("md_document")}

              <select
                value={selectedDocument}
                onChange={(event) =>
                  setDocumentName(event.target.value)
                }
                className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-base font-normal text-slate-900 focus-visible:outline-3 focus-visible:outline-indigo-600 dark:border-slate-600 dark:bg-slate-900 dark:text-white"
              >
                {accepted.map((option) => (
                  <option value={option} key={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center gap-2 text-slate-900 dark:text-white">
              <FileQuestion
                size={20}
                className="text-indigo-600 dark:text-indigo-300"
                aria-hidden="true"
              />

              <h3 className="font-semibold">{selectedDocument}</h3>
            </div>

            <p className="mt-2 text-sm leading-6 text-slate-700 dark:text-slate-300">
              {notApplicable
                ? t("md_exemption")
                : loading
                ? t("md_loading")
                : service
                ? t("md_internal")
                : source?.regional
                ? t("md_regional")
                : source
                ? t("md_issuer")
                : localDocument
                ? t("md_local")
                : t("md_directory")}
            </p>

            {!notApplicable && (
              <ol className="ml-5 mt-3 list-decimal space-y-1 text-sm leading-6 text-slate-700 dark:text-slate-300">
                <li>{t("md_step1")}</li>
                <li>{t("md_step2")}</li>
                <li>{t("md_step3")}</li>
              </ol>
            )}

            {!loading && !notApplicable && service && (
              <Link
                to={`/checklist/${slugify(service.name)}`}
                className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
              >
                {t("md_open_sahayak")}
                <ArrowRight size={18} aria-hidden="true" />
              </Link>
            )}

            {!loading &&
              !notApplicable &&
              !service &&
              (source || !localDocument) && (
                <a
                  href={source?.url || directory}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
                >
                  {source
                    ? `${t("md_open_source")} — ${source.label}`
                    : t("md_find_portal")}

                  <ExternalLink size={17} aria-hidden="true" />
                </a>
              )}
          </div>

          <p className="mt-3 text-xs leading-5 text-slate-600 dark:text-slate-300">
            {t("md_disclaimer")}
          </p>
        </div>
      )}
    </section>
  );
}


import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import {
  ArrowRight,
  ClipboardList,
  FileSearch,
  ListChecks,
  ExternalLink,
  Info,
} from "lucide-react";

const features = [
  {
    title: "about_new_feature1_title",
    description: "about_new_feature1_desc",
    icon: ListChecks,
    background: "bg-[#EFF6FF] dark:bg-blue-950",
    iconColor: "text-[#2563EB] dark:text-blue-300",
  },
  {
    title: "about_new_feature2_title",
    description: "about_new_feature2_desc",
    icon: ClipboardList,
    background: "bg-[#FFF7ED] dark:bg-orange-950",
    iconColor: "text-[#EA580C] dark:text-orange-300",
  },
  {
    title: "about_new_feature3_title",
    description: "about_new_feature3_desc",
    icon: FileSearch,
    background: "bg-[#ECFDF5] dark:bg-emerald-950",
    iconColor: "text-[#059669] dark:text-emerald-300",
  },
  {
    title: "about_new_feature4_title",
    description: "about_new_feature4_desc",
    icon: ExternalLink,
    background: "bg-[#F5F3FF] dark:bg-violet-950",
    iconColor: "text-[#7C3AED] dark:text-violet-300",
  },
];

export default function About() {
  const { t } = useTranslation();

  return (
    <main
      className="min-h-[70vh] bg-[#F8FAFC] px-6 py-12 text-[#0F172A] dark:bg-slate-950 dark:text-slate-100 sm:py-16"
      style={{
        fontFamily:
          'Inter, "Noto Sans Devanagari", sans-serif',
      }}
    >
      <div className="mx-auto max-w-[1200px]">

        {/* ABOUT INTRODUCTION */}

        <div className="mx-auto max-w-3xl text-center">

          <span className="inline-flex rounded-full border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm font-semibold text-indigo-700 dark:border-indigo-800 dark:bg-indigo-950 dark:text-indigo-200">
            {t("about_new_label")}
          </span>

          <h1 className="mt-6 text-3xl font-bold leading-tight tracking-tight text-[#0F172A] dark:text-white sm:text-4xl lg:text-5xl">
            {t("about_new_heading")}
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-base leading-8 text-[#475569] dark:text-slate-300 sm:text-lg">
            {t("about_new_description")}
          </p>

          <Link
            to="/#explore-services"
            className="mt-8 inline-flex min-h-12 items-center justify-center gap-3 rounded-xl bg-[#4F46E5] px-7 py-3 text-base font-semibold text-white shadow-sm transition-colors hover:bg-[#4338CA] focus-visible:outline-3 focus-visible:outline-offset-4 focus-visible:outline-[#4F46E5]"
          >
            {t("about_new_button")}
            <ArrowRight size={20} aria-hidden="true" />
          </Link>

        </div>

        {/* WHAT USERS CAN DO */}

        <section
          className="mt-16 sm:mt-20"
          aria-labelledby="about-features-heading"
        >
          <div className="mb-8 text-center">

            <h2
              id="about-features-heading"
              className="text-2xl font-semibold text-[#0F172A] dark:text-white"
            >
              {t("about_new_features_heading")}
            </h2>

            <p className="mt-3 text-base leading-7 text-[#475569] dark:text-slate-300">
              {t("about_new_features_subtitle")}
            </p>

          </div>

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-4">

            {features.map((feature) => {
              const Icon = feature.icon;

              return (
                <article
                  key={feature.title}
                  className="rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-[0_3px_12px_rgba(15,23,42,0.04)] transition-[border-color,box-shadow,transform] duration-200 hover:-translate-y-0.5 hover:border-indigo-300 hover:shadow-[0_12px_28px_rgba(15,23,42,0.08)] motion-reduce:transform-none motion-reduce:transition-none dark:border-slate-700 dark:bg-slate-900 dark:hover:border-indigo-500"
                >

                  <div
                    className={`flex h-12 w-12 items-center justify-center rounded-xl ${feature.background} ${feature.iconColor}`}
                  >
                    <Icon
                      size={24}
                      strokeWidth={1.9}
                      aria-hidden="true"
                    />
                  </div>

                  <h3 className="mt-6 text-lg font-semibold leading-7 text-[#0F172A] dark:text-white">
                    {t(feature.title)}
                  </h3>

                  <p className="mt-3 text-base leading-7 text-[#475569] dark:text-slate-300">
                    {t(feature.description)}
                  </p>

                </article>
              );
            })}

          </div>
        </section>

        {/* IMPORTANT NOTE */}

        <div
          role="note"
          className="mx-auto mt-12 flex max-w-3xl items-start gap-3 rounded-xl border border-[#E2E8F0] bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
        >
          <Info
            className="mt-0.5 shrink-0 text-[#4F46E5] dark:text-indigo-300"
            size={21}
            aria-hidden="true"
          />

          <p className="text-sm leading-6 text-[#475569] dark:text-slate-300">
            {t("about_new_disclaimer")}
          </p>
        </div>

      </div>
    </main>
  );
}

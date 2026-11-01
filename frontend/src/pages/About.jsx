import React from "react";
import { useTranslation } from "react-i18next";

function About() {
  const { t } = useTranslation();

  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold text-brand-700 dark:text-brand-400 mb-6">{t("about_title")}</h1>
      
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8 mb-8">
        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-4">{t("about_overview_title")}</h2>
        <p className="text-gray-600 dark:text-gray-400 mb-4 leading-relaxed">
          {t("about_overview_desc")}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8">
          <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-4">{t("about_how_title")}</h2>
          <ul className="list-disc pl-5 space-y-2 text-gray-600 dark:text-gray-400">
            <li>{t("about_how_1")}</li>
            <li>{t("about_how_2")}</li>
            <li>{t("about_how_3")}</li>
            <li>{t("about_how_4")}</li>
            <li>{t("about_how_5")}</li>
          </ul>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-8">
        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-4">{t("about_tech_title")}</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div className="p-4 bg-brand-50 dark:bg-gray-700 text-brand-700 dark:text-brand-400 rounded-lg font-medium">React & Vite</div>
          <div className="p-4 bg-brand-50 dark:bg-gray-700 text-brand-700 dark:text-brand-400 rounded-lg font-medium">Python Flask</div>
          <div className="p-4 bg-brand-50 dark:bg-gray-700 text-brand-700 dark:text-brand-400 rounded-lg font-medium">Tesseract OCR</div>
          <div className="p-4 bg-brand-50 dark:bg-gray-700 text-brand-700 dark:text-brand-400 rounded-lg font-medium">PostgreSQL</div>
        </div>
      </div>
    </div>
  );
}

export default About;

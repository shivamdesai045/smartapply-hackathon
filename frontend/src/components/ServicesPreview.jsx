import { Link } from "react-router-dom";
import { useServices } from "../hooks/useServices";
import { useTranslation } from "react-i18next";

function ServicesPreview() {
  const { data, loading, error } = useServices();
  const { t } = useTranslation();

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100">{t("services_preview_title")}</h2>
        <Link
          to="/services"
          className="text-brand-600 dark:text-brand-400 text-sm font-medium hover:underline"
        >
          {t("services_preview_link")}
        </Link>
      </div>

      {loading && (
        <p className="text-gray-400 text-sm">{t("services_loading")}</p>
      )}

      {error && (
        <p className="text-red-500 text-sm">
          {t("services_error")} ({error})
        </p>
      )}

      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {data.categories.map((cat, i) => (
            <Link
              key={i}
              to="/services"
              className="border border-gray-200 dark:border-gray-700 rounded-xl p-6 hover:border-brand-500 dark:hover:border-brand-500 hover:shadow-md transition bg-white dark:bg-gray-800"
            >
              <div className="text-3xl mb-3">{cat.icon}</div>
              <div className="font-semibold text-brand-700 dark:text-brand-400 mb-1">
                {t(cat.title)}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {cat.services.length} {t("services_available")}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default ServicesPreview;
import { Link } from "react-router-dom";
import { useServices } from "../hooks/useServices";
import { useTranslation } from "react-i18next";
import { slugify } from "../utils/slugify";

function Services() {
  const { data, loading, error } = useServices();
  const { t } = useTranslation();

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <h1 className="text-2xl font-bold text-brand-700 dark:text-brand-400 mb-2">{t("services_title")}</h1>
      <p className="text-gray-600 dark:text-gray-400 mb-8">
        {t("services_desc")}
      </p>

      {loading && (
        <p className="text-gray-400 text-sm">{t("services_loading")}</p>
      )}

      {error && (
        <p className="text-red-500 text-sm">
          {t("services_error")} ({error})
        </p>
      )}

      {data &&
        data.categories.map((cat, i) => (
          <div key={i} className="mb-10">
            <div className="flex items-center gap-2 mb-4">
              <span className="text-2xl">{cat.icon}</span>
              <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
                {t(cat.title)}
              </h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {cat.services.map((service, j) => (
                <Link
                  key={j}
                  to={`/checklist/${slugify(service.name)}`}
                  className="text-left border border-gray-200 dark:border-gray-700 rounded-xl p-4 hover:border-brand-500 dark:hover:border-brand-500 hover:shadow-md transition bg-white dark:bg-gray-800 block"
                >
                  <div className="font-medium text-brand-700 dark:text-brand-400 mb-1">
                    {t(service.name)}
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">{t(service.desc)}</div>
                </Link>
              ))}
            </div>
          </div>
        ))}
    </div>
  );
}

export default Services;
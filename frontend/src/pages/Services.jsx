
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useServices } from "../hooks/useServices";
import { slugify } from "../utils/slugify";

export default function Services() {
  const { id } = useParams();
  const { t } = useTranslation();
  const { data, loading, error, retry } = useServices();

  const visibleCategories = (data?.categories || []).filter(
    (category) => !id || category.id === id
  );

  return (
    <main className="max-w-6xl mx-auto px-6 py-10">
      <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-2">
        {id && visibleCategories.length
          ? t(visibleCategories[0].title)
          : t("services_title")}
      </h1>

      <p className="text-gray-600 dark:text-gray-300 mb-8">
        {t("services_desc")}
      </p>

      {loading && <p role="status">{t("services_loading")}</p>}

      {error && (
        <div role="alert" className="flex items-center gap-4">
          <p>{t("services_error")}</p>
          <button
            type="button"
            onClick={retry}
            className="px-4 py-3 bg-indigo-600 text-white rounded-xl"
          >
            {t("home_retry")}
          </button>
        </div>
      )}

      {data && visibleCategories.length === 0 && (
        <p className="text-gray-600 dark:text-gray-300">
          {t("home_no_categories")}
        </p>
      )}

      {visibleCategories.map((category) => (
        <section key={category.id} className="mb-10">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            {t(category.title)}
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {category.services.map((service) => (
              <Link
                key={service.name}
                to={`/checklist/${slugify(service.name)}`}
                className="block rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 hover:border-indigo-600 hover:shadow-md focus-visible:outline-3 focus-visible:outline-indigo-600 transition"
              >
                <h3 className="font-semibold text-gray-900 dark:text-white">
                  {t(service.name)}
                </h3>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                  {t(service.desc)}
                </p>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </main>
  );
}

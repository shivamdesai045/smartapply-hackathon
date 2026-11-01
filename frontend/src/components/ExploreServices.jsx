
import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { ArrowRight, RefreshCw } from "lucide-react";
import { useTranslation } from "react-i18next";
import { slugify } from "../utils/slugify";
import CategoryCard from "./CategoryCard";

export default function ExploreServices({
  data,
  loading,
  error,
  onRetry,
}) {
  const { t } = useTranslation();
  const location = useLocation();

  const selectedId = new URLSearchParams(location.search)
    .get("category");

  const categories = data?.categories || [];

  const selectedCategories =
    selectedId === "all"
      ? categories
      : categories.filter((category) => category.id === selectedId);

  useEffect(() => {
    if (
      location.hash !== "#selected-services" ||
      loading ||
      !data
    ) {
      return;
    }

    const frame = requestAnimationFrame(() => {
      const element = document.getElementById("selected-services");

      if (!element) return;

      const reduceMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
      ).matches;

      element.scrollIntoView({
        behavior: reduceMotion ? "auto" : "smooth",
        block: "start",
      });
    });

    return () => cancelAnimationFrame(frame);
  }, [location.hash, selectedId, loading, data]);

  return (
    <section
      id="explore-services"
      className="sh-explore scroll-mt-28"
      aria-labelledby="sh-explore-heading"
    >
      <div className="sh-container">

        <div className="sh-explore-header">
          <div>
            <h2 id="sh-explore-heading">
              {t("home_explore_title")}
            </h2>
            <p>{t("home_explore_subtitle")}</p>
          </div>

          <Link
            to="/?category=all#selected-services"
            className="sh-view-all"
          >
            {t("home_view_all")}
            <ArrowRight size={18} aria-hidden="true" />
          </Link>
        </div>

        {loading ? (
          <div className="sh-category-grid" aria-busy="true">
            {Array.from({ length: 4 }, (_, index) => (
              <div className="sh-category-skeleton" key={index}>
                <div className="sh-skeleton sh-skeleton-icon" />
                <div className="sh-skeleton sh-skeleton-title" />
                <div className="sh-skeleton sh-skeleton-caption" />
              </div>
            ))}
            <span className="sr-only">
              {t("services_loading")}
            </span>
          </div>
        ) : error ? (
          <div className="sh-error" role="alert">
            <p>{t("home_services_error")}</p>
            <button type="button" onClick={onRetry}>
              <RefreshCw size={18} aria-hidden="true" />
              {t("home_retry")}
            </button>
          </div>
        ) : (
          <>
            <div className="sh-category-grid">
              {categories.map((category) => (
                <CategoryCard
                  key={category.id}
                  category={category}
                />
              ))}
            </div>

            {selectedId && selectedCategories.length > 0 && (
              <div
                id="selected-services"
                className="mt-8 scroll-mt-28 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800"
              >
                {selectedCategories.map((category) => (
                  <section
                    key={category.id}
                    className="mb-8 last:mb-0"
                  >
                    <h3 className="mb-4 text-xl font-semibold text-slate-900 dark:text-white">
                      {t(category.title)}
                    </h3>

                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {category.services.map((service) => (
                        <Link
                          key={service.name}
                          to={`/checklist/${slugify(service.name)}`}
                          className="flex min-h-20 items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 text-slate-900 transition hover:border-indigo-500 hover:bg-indigo-50 focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 dark:border-slate-600 dark:bg-slate-900 dark:text-white dark:hover:bg-slate-700"
                        >
                          <div>
                            <div className="font-semibold">
                              {t(service.name)}
                            </div>
                            <div className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                              {t(service.desc)}
                            </div>
                          </div>

                          <ArrowRight
                            size={19}
                            className="shrink-0 text-indigo-600 dark:text-indigo-300"
                            aria-hidden="true"
                          />
                        </Link>
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            )}

            {!categories.length && (
              <p className="sh-empty">
                {t("home_no_categories")}
              </p>
            )}
          </>
        )}
      </div>
    </section>
  );
}

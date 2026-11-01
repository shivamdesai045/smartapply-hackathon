import { useServices } from "../hooks/useServices";
import { useTranslation } from "react-i18next";

function StatsBar() {
  const { data, loading, error } = useServices();
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className="border-y border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 py-6 text-center text-gray-400 text-sm">
        {t("services_loading")}
      </div>
    );
  }

  if (error) {
    return (
      <div className="border-y border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 py-6 text-center text-red-500 text-sm">
        {t("services_error")} ({error})
      </div>
    );
  }

  const stats = [
    { icon: "📂", value: data.totalCategories, label: t("services_title") },
    { icon: "📋", value: data.totalServices, label: t("services_available") },
    { icon: "🌐", value: 3, label: "Languages" },
  ];

  return (
    <div className="border-y border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
      <div className="max-w-6xl mx-auto px-6 py-6 grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-gray-200 dark:divide-gray-800">
        {stats.map((stat, i) => (
          <div
            key={i}
            className="flex items-center gap-4 py-3 sm:py-0 sm:px-6 first:pl-0"
          >
            <span className="text-3xl">{stat.icon}</span>
            <div>
              <div className="text-2xl font-bold text-gray-800 dark:text-gray-100">
                {stat.value}
              </div>
              <div className="text-sm text-gray-500 dark:text-gray-400">{stat.label}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default StatsBar;
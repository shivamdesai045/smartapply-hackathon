
import { FolderOpen, ClipboardList, Languages } from "lucide-react";
import { useTranslation } from "react-i18next";

export default function StatsStrip({
  data,
  loading,
  languageCount = 3,
}) {
  const { t } = useTranslation();

  const stats = [
    {
      key: "categories",
      icon: FolderOpen,
      value: data?.totalCategories,
      label: t("home_categories"),
      tone: "blue",
    },
    {
      key: "services",
      icon: ClipboardList,
      value: data?.totalServices,
      label: t("home_services"),
      tone: "orange",
    },
    {
      key: "languages",
      icon: Languages,
      value: languageCount,
      label: t("home_languages"),
      tone: "violet",
    },
  ];

  return (
    <section
      className="sh-stats"
      aria-label={t("home_stats_label")}
      aria-busy={loading}
    >
      <div className="sh-container sh-stats-grid">
        {stats.map((stat) => {
          const Icon = stat.icon;

          return (
            <div className="sh-stat" key={stat.key}>
              <span className={`sh-stat-icon sh-tone-${stat.tone}`}>
                <Icon size={24} strokeWidth={1.9} aria-hidden="true" />
              </span>

              <div className="sh-stat-info">
                {loading && stat.key !== "languages" ? (
                  <span
                    className="sh-skeleton sh-skeleton-number"
                    aria-hidden="true"
                  />
                ) : (
                  <span className="sh-stat-number">
                    {stat.value ?? "—"}
                  </span>
                )}
                <span className="sh-stat-label">{stat.label}</span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

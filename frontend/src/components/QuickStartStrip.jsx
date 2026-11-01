import "./QuickStartStrip.css";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  CalendarDays,
  ArrowUpRight,
  ChevronDown,
  Bell,
} from "lucide-react";

const notices = [
  {
    id: "yasasvi",
    title: "news_yasasvi",
    category: "news_scholarship",
    date: "2026-11-15",
    source: "NSP",
    url: "https://scholarships.gov.in/All-Scholarships",
    featured: true,
  },
  {
    id: "jee",
    title: "news_jee",
    category: "news_exam",
    date: "2026-11-22",
    source: "NTA",
    url: "https://jeemain.nta.nic.in/online-application-form-for-jee-main-2027-session-1/",
    featured: true,
  },
  {
    id: "pragati",
    title: "news_pragati",
    category: "news_scholarship",
    date: "2026-11-30",
    source: "NSP",
    url: "https://scholarships.gov.in/All-Scholarships",
    featured: true,
  },
  {
    id: "jee-correction",
    title: "news_jee_correction",
    category: "news_exam",
    date: "2026-11-29",
    source: "NTA",
    url: "https://jeemain.nta.nic.in/",
    featured: false,
  },
  {
    id: "pmkisan",
    title: "news_pmkisan",
    category: "news_scheme",
    date: null,
    source: "PM-KISAN",
    url: "https://pmkisan.gov.in/",
    featured: false,
  },
];

function getIndiaToday() {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());

  const value = (type) =>
    parts.find((part) => part.type === type).value;

  return `${value("year")}-${value("month")}-${value("day")}`;
}

export default function QuickStartStrip() {
  const { t, i18n } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  const language = i18n.resolvedLanguage || "en";
  const locale = language.startsWith("hi")
    ? "hi-IN"
    : language.startsWith("mr")
    ? "mr-IN"
    : "en-IN";

  const formatDate = (date) =>
    new Intl.DateTimeFormat(locale, {
      day: "numeric",
      month: "short",
      year: "numeric",
      timeZone: "Asia/Kolkata",
    }).format(new Date(`${date}T12:00:00+05:30`));

  const today = getIndiaToday();

  const active = notices.filter(
    (item) => !item.date || item.date >= today
  );

  const sorted = [
    ...active.filter((item) => item.featured),
    ...active.filter((item) => !item.featured),
  ];

  const visible = expanded ? sorted : sorted.slice(0, 3);

  return (
    <section className="news-strip" aria-labelledby="news-heading">
      <div className="news-panel">

        <div className="news-header">
          <div className="news-heading">
            <span className="news-icon">
              <Bell size={21} aria-hidden="true" />
            </span>

            <div>
              <h2 id="news-heading">
                {t("news_heading")}
              </h2>
              <p className="news-subtitle">
                {t("news_subtitle")}
              </p>
            </div>
          </div>

          {sorted.length > 3 && (
            <button
              type="button"
              className="news-more"
              aria-expanded={expanded}
              aria-controls="news-items"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? t("news_less") : t("news_more")}
              <ChevronDown
                size={17}
                aria-hidden="true"
                className={expanded ? "news-rotated" : ""}
              />
            </button>
          )}
        </div>

        <div id="news-items" className="news-grid">
          {visible.map((item) => (
            <a
              key={item.id}
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="news-card"
              aria-label={`${t(item.title)} — ${t("news_source")} ${item.source}. ${t("news_new_tab")}`}
            >
              <div className="news-card-top">
                <span className="news-category">
                  {t(item.category)}
                </span>
                <ArrowUpRight
                  size={19}
                  className="news-arrow"
                  aria-hidden="true"
                />
              </div>

              <h3>{t(item.title)}</h3>

              <div className="news-card-bottom">
                <span className="news-date">
                  <CalendarDays size={15} aria-hidden="true" />

                  {item.date ? (
                    <time dateTime={item.date}>
                      {formatDate(item.date)}
                    </time>
                  ) : (
                    t("news_ongoing")
                  )}
                </span>

                <span className="news-source">
                  {item.source}
                </span>
              </div>
            </a>
          ))}
        </div>

        {sorted.length === 0 && (
          <p className="news-empty" role="status">
            {t("news_empty")}
          </p>
        )}

        <div className="news-footer">
          <span>
            {t("news_checked")}: {formatDate("2026-11-01")}
          </span>
          <span>{t("news_disclaimer")}</span>
        </div>

      </div>
    </section>
  );
}


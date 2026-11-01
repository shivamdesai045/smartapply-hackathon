
import { Link } from "react-router-dom";
import {
  IdCard,
  Car,
  FileText,
  Landmark,
  ArrowRight,
} from "lucide-react";
import { useTranslation } from "react-i18next";

const CATEGORY_DESIGN = {
  "identity-civil": { Icon: IdCard, tone: "blue" },
  "licenses-transport": { Icon: Car, tone: "orange" },
  "exam-forms": { Icon: FileText, tone: "green" },
  "govt-schemes": { Icon: Landmark, tone: "violet" },
};

export default function CategoryCard({ category }) {
  const { t } = useTranslation();

  const { Icon, tone } = CATEGORY_DESIGN[category.id] || {
    Icon: FileText,
    tone: "blue",
  };

  const count = category.services?.length ?? 0;

  return (
    <Link
      to={`/?category=${encodeURIComponent(category.id)}#selected-services`}
      className="sh-category-card"
      aria-label={`${t(category.title)}, ${count} ${t("home_services")}`}
    >
      <span className={`sh-category-icon sh-tone-${tone}`}>
        <Icon size={25} strokeWidth={1.8} aria-hidden="true" />
      </span>

      <h3>{t(category.title)}</h3>

      <p>
        {count} {t("home_services")}
      </p>

      <ArrowRight
        className="sh-category-arrow"
        size={20}
        aria-hidden="true"
      />
    </Link>
  );
}

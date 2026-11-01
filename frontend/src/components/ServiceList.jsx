import { useTranslation } from "react-i18next";
import ServiceCard from "./ServiceCard";

function ServiceList() {
  const { t } = useTranslation();

  const services = [
    { icon: "🆔", key: "aadhaar" },
    { icon: "📝", key: "pan" },
    { icon: "🎓", key: "exam" },
    { icon: "📄", key: "checklist" },
  ];

  return (
    <section className="px-6 py-12 max-w-5xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">
        {t("servicesHeading")}
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        {services.map((service, index) => (
          <ServiceCard
            key={index}
            icon={service.icon}
            title={t(`services.${service.key}.title`)}
            description={t(`services.${service.key}.description`)}
          />
        ))}
      </div>
    </section>
  );
}

export default ServiceList;
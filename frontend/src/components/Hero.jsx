import { useTranslation } from "react-i18next";

function Hero() {
  const { t } = useTranslation();

  return (
    <section className="relative overflow-hidden px-6 py-20 bg-gradient-to-br from-brand-500 to-brand-700">
      {/* Floating cards */}
      <div className="absolute top-16 left-[8%] bg-white rounded-xl shadow-lg px-4 py-2 flex items-center gap-2 animate-float">
        <span className="text-green-500">✔️</span>
        <span className="text-sm font-semibold text-gray-800">Document Verified</span>
      </div>

      <div className="absolute bottom-24 left-[15%] bg-white rounded-xl shadow-lg px-4 py-2 flex items-center gap-2 animate-float animation-delay-2000">
        <span className="text-blue-600">🛡️</span>
        <span className="text-sm font-semibold text-gray-800">Genuine Source</span>
      </div>

      <div className="absolute bottom-16 right-[10%] bg-white rounded-xl shadow-lg px-4 py-2 flex items-center gap-2 animate-float animation-delay-4000">
        <span className="text-yellow-500">⚠️</span>
        <span className="text-sm font-semibold text-gray-800">Risk: LOW</span>
      </div>

      {/* Main text */}
      <div className="relative z-10 flex flex-col items-center text-center">
        <h1 className="text-3xl md:text-4xl font-bold text-white max-w-2xl">
          {t("tagline")}
        </h1>

        <div className="mt-8 w-full max-w-xl">
          <input
            type="text"
            placeholder={t("searchPlaceholder")}
            className="w-full px-5 py-3 rounded-full border-0 shadow-lg focus:outline-none focus:ring-2 focus:ring-white text-gray-700"
          />
        </div>
      </div>
    </section>
  );
}

export default Hero;
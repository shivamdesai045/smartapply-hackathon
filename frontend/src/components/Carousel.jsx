
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { ChevronLeft, ChevronRight } from "lucide-react";

import banner1 from "../assets/banner1.png";
import banner2 from "../assets/banner2.png";
import banner3 from "../assets/Banner3.png";

const banners = {
  hindi: { id: "hindi", src: banner1 },
  english: { id: "english", src: banner2 },
  features: { id: "features", src: banner3 },
};

function Carousel() {
  const { t, i18n } = useTranslation();
  const [current, setCurrent] = useState(0);
  const [paused, setPaused] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  const language = i18n.resolvedLanguage || i18n.language || "en";

  const slides = language.startsWith("hi")
    ? [banners.hindi, banners.english, banners.features]
    : [banners.english, banners.features, banners.hindi];

  useEffect(() => {
    setCurrent(0);
  }, [language]);

  useEffect(() => {
    const query = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    );

    const updatePreference = () => {
      setReducedMotion(query.matches);
    };

    updatePreference();
    query.addEventListener("change", updatePreference);

    return () => {
      query.removeEventListener("change", updatePreference);
    };
  }, []);

  useEffect(() => {
    if (paused || reducedMotion) return;

    const timer = window.setInterval(() => {
      setCurrent((previous) => (previous + 1) % 3);
    }, 5500);

    return () => window.clearInterval(timer);
  }, [paused, reducedMotion]);

  const previousSlide = () => {
    setCurrent((previous) => (previous + slides.length - 1) % slides.length);
  };

  const nextSlide = () => {
    setCurrent((previous) => (previous + 1) % slides.length);
  };

  return (
    <section className="w-full bg-[#F8FBFF] px-4 py-8 sm:px-6 sm:py-10 dark:bg-slate-950">
      <div
        className="mx-auto w-full max-w-[1600px] overflow-hidden rounded-xl border border-blue-100 bg-white shadow-[0_8px_24px_rgba(18,49,95,0.08)] dark:border-slate-700 dark:bg-slate-900"
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
        onFocusCapture={() => setPaused(true)}
        onBlurCapture={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget)) {
            setPaused(false);
          }
        }}
      >
        {/* Banner images */}
        <div className="relative aspect-[2048/682] w-full overflow-hidden">
          {slides.map((slide, index) => (
            <img
              key={slide.id}
              src={slide.src}
              alt={`${t("banner_label")} ${index + 1}`}
              aria-hidden={index !== current}
              loading={index === 0 ? "eager" : "lazy"}
              className={`absolute inset-0 block h-full w-full object-contain transition-opacity duration-500 motion-reduce:transition-none ${
                current === index
                  ? "opacity-100"
                  : "opacity-0"
              }`}
            />
          ))}
        </div>

        {/* Carousel controls */}
        <div className="flex min-h-14 items-center justify-center gap-4 border-t border-blue-100 bg-white px-4 py-1 dark:border-slate-700 dark:bg-slate-900">
          <button
            type="button"
            onClick={previousSlide}
            aria-label={t("banner_previous")}
            className="flex h-11 w-11 items-center justify-center rounded-xl text-blue-700 transition-colors hover:bg-blue-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:text-blue-300 dark:hover:bg-slate-800"
          >
            <ChevronLeft size={22} />
          </button>

          <div className="flex items-center gap-1">
            {slides.map((slide, index) => (
              <button
                key={slide.id}
                type="button"
                onClick={() => setCurrent(index)}
                aria-label={`${t("banner_label")} ${index + 1}`}
                aria-current={current === index ? "true" : undefined}
                className="flex h-11 w-11 items-center justify-center rounded-full focus-visible:outline-2 focus-visible:outline-blue-600"
              >
                <span
                  className={`block h-2.5 rounded-full transition-all duration-300 motion-reduce:transition-none ${
                    current === index
                      ? "w-6 bg-blue-600"
                      : "w-2.5 bg-slate-300 dark:bg-slate-500"
                  }`}
                />
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={nextSlide}
            aria-label={t("banner_next")}
            className="flex h-11 w-11 items-center justify-center rounded-xl text-blue-700 transition-colors hover:bg-blue-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:text-blue-300 dark:hover:bg-slate-800"
          >
            <ChevronRight size={22} />
          </button>
        </div>
      </div>
    </section>
  );
}

export default Carousel;

import { useState, useEffect } from "react";
import banner1 from "../assets/banner1.png";
import banner2 from "../assets/banner2.png";
import banner3 from "../assets/banner3.png";

const slides = [banner1, banner3, banner2];

function Carousel() {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrent((prev) => (prev + 1) % slides.length);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="relative w-full aspect-[3/1] overflow-hidden rounded-xl shadow-lg bg-brand-50">
      <div
        className="flex h-full transition-transform duration-700 ease-in-out"
        style={{
          width: `${slides.length * 100}%`,
          transform: `translateX(-${(100 / slides.length) * current}%)`,
        }}
      >
        {slides.map((slide, i) => (
          <div
            key={i}
            className="h-full flex-shrink-0 flex items-center justify-center"
            style={{ width: `${100 / slides.length}%` }}
          >
            <img
              src={slide}
              alt={`Banner ${i + 1}`}
              className="w-full h-full object-cover"
            />
          </div>
        ))}
      </div>

      {/* Dots */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2">
        {slides.map((_, i) => (
          <button
            key={i}
            onClick={() => setCurrent(i)}
            className={`w-2.5 h-2.5 rounded-full transition-colors ${
              current === i ? "bg-brand-600" : "bg-white/70"
            }`}
          />
        ))}
      </div>
    </div>
  );
}

export default Carousel;
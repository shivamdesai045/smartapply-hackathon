
import { useEffect } from "react";

import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useLocation,
  useParams,
} from "react-router-dom";

import { useTranslation } from "react-i18next";

import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";

// Existing components
import Header from "./components/Header";
import HeroSearch from "./components/HeroSearch";
import QuickStartStrip from "./components/QuickStartStrip";
import Carousel from "./components/Carousel";
import ChatBot from "./components/ChatBot";
import LoginRequiredModal from "./components/LoginRequiredModal";

// Redesigned homepage components
import StatsStrip from "./components/StatsStrip";
import ExploreServices from "./components/ExploreServices";
import { useServices } from "./hooks/useServices";

import "./components/HomePolish.css";

// Existing pages
import Login from "./pages/Login";
import Register from "./pages/Register";
import Checklist from "./pages/Checklist";
import About from "./pages/About";
import MyDocuments from "./pages/MyDocuments";
import VerificationReport from "./pages/VerificationReport";

// =====================================
// HOME PAGE
// =====================================

function Home() {
  const { data, loading, error, retry } = useServices();

  return (
    <>
      <HeroSearch />

      <QuickStartStrip />

      <Carousel />

      <div className="sh-home">
        <StatsStrip
          data={data}
          loading={loading}
          languageCount={3}
        />

        <ExploreServices
          data={data}
          loading={loading}
          error={error}
          onRetry={retry}
        />
      </div>
    </>
  );
}

// =====================================
// OLD CATEGORY LINKS REDIRECT
// =====================================

function LegacyCategoryRedirect() {
  const { id } = useParams();

  return (
    <Navigate
      to={`/?category=${encodeURIComponent(id || "")}#selected-services`}
      replace
    />
  );
}

// =====================================
// APP SHELL
// =====================================

function AppShell() {
  const location = useLocation();
  const { t } = useTranslation();

  const isHome = location.pathname === "/";

  // Scroll to Explore Services when clicking
  // Services in the navigation bar.
  useEffect(() => {
    if (
      location.pathname !== "/" ||
      location.hash !== "#explore-services"
    ) {
      return;
    }

    const frame = requestAnimationFrame(() => {
      const section = document.getElementById(
        "explore-services"
      );

      if (!section) return;

      const reducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
      ).matches;

      section.scrollIntoView({
        behavior: reducedMotion ? "auto" : "smooth",
        block: "start",
      });
    });

    return () => cancelAnimationFrame(frame);
  }, [location.pathname, location.hash]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 flex flex-col">

      <div className="flex-1">

        {!isHome && <Header />}

        <main>
          {import.meta.env.VITE_DEMO_MODE === '1' && <div role="note" className="border-b border-amber-300 bg-amber-50 px-4 py-3 text-center text-sm text-amber-950">
            Free demo: use synthetic sample documents only. Accounts and uploads reset when the server restarts. First access and OCR may be slow while the server starts.
          </div>}
          <Routes>

            <Route
              path="/"
              element={<Home />}
            />

            <Route
              path="/login"
              element={<Login />}
            />

            <Route
              path="/register"
              element={<Register />}
            />

            {/* Services now opens homepage */}

            <Route
              path="/services"
              element={
                <Navigate
                  to="/#explore-services"
                  replace
                />
              }
            />

            <Route
              path="/services/:id"
              element={<LegacyCategoryRedirect />}
            />

            {/* Existing application pages */}

            <Route
              path="/about"
              element={<About />}
            />

            <Route
              path="/checklist/:slug"
              element={<Checklist />}
            />

            <Route
              path="/my-documents"
              element={<MyDocuments />}
            />

            <Route
              path="/report/:slug"
              element={<VerificationReport />}
            />

          </Routes>
        </main>
      </div>

      {/* =====================================
          FOOTER
      ===================================== */}

      <footer className="border-t border-slate-700 bg-slate-950 px-6 py-8 text-slate-200">

        <div className="mx-auto max-w-7xl">

          <div className="flex flex-col justify-between gap-8 md:flex-row">

            {/* Brand and disclaimer */}

            <div className="max-w-sm">
              <p className="text-lg font-semibold text-white">
                Sahayak
              </p>

              <p className="mt-2 text-sm leading-6 text-slate-300">
                {t("home_footer_disclaimer")}
              </p>
            </div>

            {/* Privacy and policies */}

            <div className="grid gap-4 text-sm sm:grid-cols-3">

              {[
                [
                  "footer_privacy",
                  "footer_privacy_text",
                ],
                [
                  "footer_terms",
                  "footer_terms_text",
                ],
                [
                  "footer_accessibility",
                  "footer_accessibility_text",
                ],
              ].map(([label, description]) => (
                <details
                  key={label}
                  className="max-w-xs"
                >

                  <summary className="flex min-h-11 cursor-pointer items-center rounded-lg px-2 font-medium text-white hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-indigo-300">
                    {t(label)}
                  </summary>

                  <p className="mt-2 px-2 leading-6 text-slate-300">
                    {t(description)}
                  </p>

                </details>
              ))}

            </div>
          </div>

          {/* Copyright */}

          <div className="mt-8 border-t border-slate-700 pt-5 text-center text-sm text-slate-400">
            © {new Date().getFullYear()} Sahayak
          </div>

        </div>
      </footer>

      {/* Existing chatbot */}

      <ChatBot />

      <LoginRequiredModal />

    </div>
  );
}

// =====================================
// ROOT APP
// =====================================

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <AppShell />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;

import { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, Link, useNavigate } from "react-router-dom";
import logo from "../assets/logo.png";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

const languages = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिंदी" },
  { code: "mr", label: "मराठी" },
];

function Header() {
  const { t, i18n } = useTranslation();
  const [langOpen, setLangOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const { user, loading, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const userMenuRef = useRef(null);
  const langMenuRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setUserMenuOpen(false);
      }
      if (langMenuRef.current && !langMenuRef.current.contains(e.target)) {
        setLangOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = async () => {
    setUserMenuOpen(false);
    try {
      await logout();
      if (window.location.pathname.startsWith("/my-documents")) {
        navigate("/");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const changeLanguage = (lng) => {
    i18n.changeLanguage(lng);
    setLangOpen(false);
  };

  const currentLabel =
    languages.find((l) => l.code === i18n.language)?.label || "English";

  const firstName = user?.full_name ? user.full_name.trim().split(" ")[0] : "User";

  return (
    <header className="sticky top-0 z-40 shadow-sm print:hidden">
      <div className="bg-brand-700 dark:bg-brand-900 text-white text-xs text-center py-1 px-2">
        {t("notGovtSite")}
      </div>

      <div className="flex items-center px-4 sm:px-6 py-3 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 gap-4 sm:gap-6">
        <Link to="/" className="shrink-0">
          <img src={logo} alt="Sahayak" className="h-9 sm:h-10 w-auto" />
        </Link>

        <div className="flex-1 max-w-xl hidden md:block">
          <div className="flex items-center border border-gray-300 dark:border-gray-600 rounded-full px-4 py-2 bg-gray-50 dark:bg-gray-700 focus-within:border-brand-500 focus-within:bg-white dark:focus-within:bg-gray-800 transition">
            <span className="text-gray-400 mr-2">🔍</span>
            <input
              type="text"
              placeholder={t("searchPlaceholder")}
              className="bg-transparent outline-none text-sm w-full text-gray-700 dark:text-gray-200"
            />
          </div>
        </div>

        <div className="flex items-center gap-3 sm:gap-4 ml-auto shrink-0">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-full border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
            title="Toggle Theme"
            aria-label="Toggle Theme"
          >
            {theme === "light" ? "🌙" : "☀️"}
          </button>

          {/* Language Switcher */}
          <div className="relative" ref={langMenuRef}>
            <button
              onClick={() => setLangOpen(!langOpen)}
              className="px-3 py-1.5 rounded border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center gap-1 whitespace-nowrap"
              aria-expanded={langOpen}
            >
              <span>🌐</span>
              <span className="hidden sm:inline">{currentLabel}</span>
              <span className="text-xs">▼</span>
            </button>

            {langOpen && (
              <div className="absolute right-0 mt-1 w-36 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg z-50 py-1">
                {languages.map((lang) => (
                  <button
                    key={lang.code}
                    onClick={() => changeLanguage(lang.code)}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-brand-50 dark:hover:bg-gray-700 ${
                      i18n.language === lang.code
                        ? "bg-brand-50 dark:bg-gray-700 text-brand-700 dark:text-brand-400 font-semibold"
                        : "text-gray-700 dark:text-gray-300"
                    }`}
                  >
                    {lang.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Authentication State */}
          {loading ? (
            <div className="w-24 h-9 bg-gray-200 dark:bg-gray-700 animate-pulse rounded-full" />
          ) : user ? (
            <div className="relative" ref={userMenuRef}>
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-50 dark:bg-gray-700 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-gray-600 hover:bg-brand-100 dark:hover:bg-gray-600 text-sm font-semibold transition"
                aria-expanded={userMenuOpen}
                aria-haspopup="true"
              >
                <span className="w-6 h-6 rounded-full bg-brand-600 text-white flex items-center justify-center text-xs">
                  {firstName[0].toUpperCase()}
                </span>
                <span>Hi, {firstName}</span>
                <span className="text-xs">▼</span>
              </button>

              {userMenuOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 py-1 z-50 animate-fade-in">
                  <div className="px-4 py-2 border-b border-gray-100 dark:border-gray-700">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Signed in as</p>
                    <p className="text-sm font-semibold text-gray-800 dark:text-gray-100 truncate">
                      {user.full_name}
                    </p>
                  </div>

                  <Link
                    to="/my-documents"
                    onClick={() => setUserMenuOpen(false)}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
                  >
                    <span>📁</span>
                    <span>{t("my_documents", "My Documents")}</span>
                  </Link>

                  <div className="border-t border-gray-100 dark:border-gray-700 my-1"></div>

                  <button
                    onClick={handleLogout}
                    className="w-full text-left flex items-center gap-2 px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 transition"
                  >
                    <span>🚪</span>
                    <span>{t("logout", "Logout")}</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                to="/login"
                className="px-4 py-1.5 rounded-full border border-brand-700 dark:border-brand-500 text-brand-700 dark:text-brand-400 text-sm font-medium hover:bg-brand-50 dark:hover:bg-gray-700 transition"
              >
                {t("login", "Log In")}
              </Link>
              <Link
                to="/register"
                className="hidden sm:inline-block px-4 py-1.5 rounded-full bg-brand-700 hover:bg-brand-800 text-white text-sm font-medium shadow-sm transition"
              >
                {t("register", "Register")}
              </Link>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-7 px-6 py-2 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
        <NavLink
          to="/"
          className={({ isActive }) =>
            `text-base font-bold transition ${
              isActive
                ? "text-brand-600 dark:text-brand-400 border-b-2 border-brand-600 dark:border-brand-400 pb-1"
                : "text-gray-700 dark:text-gray-400 hover:text-brand-600 dark:hover:text-brand-300"
            }`
          }
        >
          {t("nav_home")}
        </NavLink>
        <NavLink
         to="/#explore-services"
          className={({ isActive }) =>
            `text-base font-bold transition ${
              isActive
                ? "text-brand-600 dark:text-brand-400 border-b-2 border-brand-600 dark:border-brand-400 pb-1"
                : "text-gray-700 dark:text-gray-400 hover:text-brand-600 dark:hover:text-brand-300"
            }`
          }
        >
          {t("nav_services")}
        </NavLink>
        {user && (
          <NavLink
            to="/my-documents"
            className={({ isActive }) =>
              `text-base font-bold transition ${
                isActive
                  ? "text-brand-600 dark:text-brand-400 border-b-2 border-brand-600 dark:border-brand-400 pb-1"
                  : "text-gray-700 dark:text-gray-400 hover:text-brand-600 dark:hover:text-brand-300"
              }`
            }
          >
            {t("my_documents", "My Documents")}
          </NavLink>
        )}
        <NavLink
          to="/about"
          className={({ isActive }) =>
            `text-base font-bold transition ${
              isActive
                ? "text-brand-600 dark:text-brand-400 border-b-2 border-brand-600 dark:border-brand-400 pb-1"
                : "text-gray-700 dark:text-gray-400 hover:text-brand-600 dark:hover:text-brand-300"
            }`
          }
        >
          {t("nav_about")}
        </NavLink>
      </div>
    </header>
  );
}

export default Header;

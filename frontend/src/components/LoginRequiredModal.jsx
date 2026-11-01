import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";

function LoginRequiredModal() {
  const { t } = useTranslation();
  const { loginModalState, closeLoginModal } = useAuth();
  const { isOpen, message, nextPath } = loginModalState;

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isOpen) {
        closeLoginModal();
      }
    };
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, closeLoginModal]);

  if (!isOpen) return null;

  const loginUrl = nextPath ? `/login?next=${encodeURIComponent(nextPath)}` : "/login";
  const registerUrl = nextPath ? `/register?next=${encodeURIComponent(nextPath)}` : "/register";

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="login-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
    >
      <div className="relative w-full max-w-md bg-white dark:bg-gray-800 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 p-6 overflow-hidden">
        {/* Close Button */}
        <button
          onClick={closeLoginModal}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition"
          aria-label="Close modal"
        >
          ✕
        </button>

        <div className="text-center space-y-4">
          <div className="w-14 h-14 bg-brand-50 dark:bg-brand-900/40 text-brand-600 dark:text-brand-400 rounded-full flex items-center justify-center mx-auto text-2xl shadow-inner">
            🔒
          </div>

          <h3 id="login-modal-title" className="text-xl font-bold text-gray-900 dark:text-white">
            {t("auth_required_title", "Login Required")}
          </h3>

          <p className="text-sm text-gray-600 dark:text-gray-300">
            {message || t("auth_required_msg", "Please log in or register to upload documents, review mismatches, and access correction guidance.")}
          </p>

          <div className="pt-2 flex flex-col gap-3">
            <Link
              to={loginUrl}
              onClick={closeLoginModal}
              className="w-full py-2.5 px-4 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm shadow-md hover:shadow-lg transition flex items-center justify-center gap-2"
            >
              <span>🔑</span> {t("nav_login", "Log In")}
            </Link>

            <Link
              to={registerUrl}
              onClick={closeLoginModal}
              className="w-full py-2.5 px-4 rounded-xl border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200 font-medium text-sm transition"
            >
              {t("create_account", "Create New Account")}
            </Link>

            <button
              onClick={closeLoginModal}
              className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 pt-1"
            >
              {t("continue_browsing", "Continue Browsing as Guest")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LoginRequiredModal;


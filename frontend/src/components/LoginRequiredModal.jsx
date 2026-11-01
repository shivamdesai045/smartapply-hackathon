
import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  LockKeyhole,
  ShieldCheck,
  Info,
  X,
  LogIn,
  UserRoundPlus,
  ArrowRight,
} from "lucide-react";

import { useAuth } from "../context/AuthContext";

export default function LoginRequiredModal() {
  const { t } = useTranslation();

  const { loginModalState, closeLoginModal } = useAuth();

  const { isOpen, message, nextPath } = loginModalState;

  const dialogRef = useRef(null);
  const loginRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return;

    const previouslyFocused = document.activeElement;

    const frame = requestAnimationFrame(() => {
      loginRef.current?.focus();
    });

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        closeLoginModal();
      }

      if (event.key === "Tab" && dialogRef.current) {
        const focusables = Array.from(
          dialogRef.current.querySelectorAll(
            'a[href], button:not([disabled])'
          )
        );

        const first = focusables[0];
        const last = focusables[focusables.length - 1];

        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (
          !event.shiftKey &&
          document.activeElement === last
        ) {
          event.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("keydown", handleKeyDown);
      previouslyFocused?.focus?.();
    };
  }, [isOpen, closeLoginModal]);

  if (!isOpen) return null;

  const loginUrl = nextPath
    ? `/login?next=${encodeURIComponent(nextPath)}`
    : "/login";

  const registerUrl = nextPath
    ? `/register?next=${encodeURIComponent(nextPath)}`
    : "/register";

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto bg-black/70 p-4 backdrop-blur-sm"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="login-modal-title"
        aria-describedby="login-modal-description"
        className="relative my-auto w-full max-w-[480px] rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-700 dark:bg-[#1E293B] sm:p-8"
      >
        {/* Close button */}
        <button
          type="button"
          onClick={closeLoginModal}
          aria-label={t("login_modal_close")}
          className="absolute right-4 top-4 flex h-11 w-11 items-center justify-center rounded-xl text-slate-500 hover:bg-slate-100 focus-visible:outline-3 focus-visible:outline-indigo-500 dark:text-slate-400 dark:hover:bg-slate-700"
        >
          <X size={21} aria-hidden="true" />
        </button>

        {/* Header */}
        <div className="text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-900/50 dark:text-indigo-300">
            <LockKeyhole size={30} strokeWidth={1.8} aria-hidden="true" />
          </div>

          <h2
            id="login-modal-title"
            className="mt-5 text-2xl font-bold text-slate-900 dark:text-white"
          >
            {t("auth_required_title")}
          </h2>

          <p
            id="login-modal-description"
            className="mx-auto mt-3 max-w-sm text-base leading-7 text-slate-600 dark:text-slate-300"
          >
            {message || t("login_modal_intro")}
          </p>
        </div>

        {/* Privacy and document information */}
        <div className="mt-6 rounded-xl border border-indigo-200 bg-indigo-50 p-4 dark:border-indigo-800 dark:bg-[#263957]">

          <div className="flex items-center gap-3">
            <ShieldCheck
              size={22}
              className="shrink-0 text-indigo-700 dark:text-indigo-300"
              aria-hidden="true"
            />

            <h3 className="text-base font-semibold text-slate-900 dark:text-white">
              {t("login_modal_privacy_title")}
            </h3>
          </div>

          <p className="mt-3 text-sm leading-6 text-slate-700 dark:text-slate-200">
            {t("login_modal_privacy_desc")}
          </p>

          <div className="mt-3 flex items-start gap-2 border-t border-indigo-200 pt-3 dark:border-indigo-700">
            <Info
              size={18}
              className="mt-0.5 shrink-0 text-indigo-700 dark:text-indigo-300"
              aria-hidden="true"
            />

            <p className="text-sm leading-6 text-slate-700 dark:text-slate-200">
              {t("login_modal_privacy_tip")}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-6 flex flex-col gap-3">

          <Link
            ref={loginRef}
            to={loginUrl}
            onClick={closeLoginModal}
            className="flex min-h-12 w-full items-center justify-center gap-3 rounded-xl bg-[#4F46E5] px-5 py-3 text-base font-semibold text-white shadow-sm transition-colors hover:bg-[#4338CA] focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-indigo-500"
          >
            <LogIn size={19} aria-hidden="true" />
            {t("nav_login", "Log In")}
            <ArrowRight size={18} aria-hidden="true" />
          </Link>

          <Link
            to={registerUrl}
            onClick={closeLoginModal}
            className="flex min-h-12 w-full items-center justify-center gap-3 rounded-xl border border-slate-300 bg-white px-5 py-3 text-base font-semibold text-slate-800 transition-colors hover:bg-slate-50 focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:hover:bg-slate-700"
          >
            <UserRoundPlus size={19} aria-hidden="true" />
            {t("create_account", "Create New Account")}
          </Link>

          <button
            type="button"
            onClick={closeLoginModal}
            className="min-h-11 rounded-xl px-4 text-sm font-medium text-slate-600 hover:text-indigo-700 focus-visible:outline-3 focus-visible:outline-indigo-500 dark:text-slate-300 dark:hover:text-white"
          >
            {t("continue_browsing", "Continue Browsing as Guest")}
          </button>
        </div>

        <p className="mt-3 text-center text-xs leading-5 text-slate-500 dark:text-slate-400">
          {t("login_modal_disclaimer")}
        </p>
      </div>
    </div>
  );
}

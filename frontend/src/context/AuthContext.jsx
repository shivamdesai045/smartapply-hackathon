import React, { createContext, useContext, useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { fetchMe, loginUser, logoutUser, registerUser } from "../lib/api";
import { initSession } from "../lib/session";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loginModalState, setLoginModalState] = useState({
    isOpen: false,
    message: "Please log in to continue.",
    nextPath: null,
  });

  const { i18n } = useTranslation();

  const openLoginModal = (message = "Please log in to continue.", nextPath = null) => {
    setLoginModalState({
      isOpen: true,
      message,
      nextPath: nextPath || (typeof window !== "undefined" ? window.location.pathname + window.location.search : null),
    });
  };

  const closeLoginModal = () => {
    setLoginModalState((prev) => ({ ...prev, isOpen: false }));
  };

  useEffect(() => {
    // Listen for 401 LOGIN_REQUIRED global events dispatched by api.js
    const handleLoginRequiredEvent = (e) => {
      const detail = e.detail || {};
      openLoginModal(detail.message, detail.nextPath);
    };

    window.addEventListener("sahayak:login_required", handleLoginRequiredEvent);
    return () => {
      window.removeEventListener("sahayak:login_required", handleLoginRequiredEvent);
    };
  }, []);

  useEffect(() => {
    // Initialize secure server session on startup
    initSession().catch((err) => console.error("Session initialization failed", err));

    // Check if user is already logged in via signed session cookie
    fetchMe()
      .then((data) => {
        if (data && data.user) {
          setUser(data.user);
          if (data.user.preferred_language && i18n.language !== data.user.preferred_language) {
            i18n.changeLanguage(data.user.preferred_language);
          }
        }
      })
      .catch((err) => console.error("Session check failed", err))
      .finally(() => setLoading(false));
  }, [i18n]);

  const login = async (email, password) => {
    const data = await loginUser(email, password);
    setUser(data.user);
    if (data.user?.preferred_language && i18n.language !== data.user.preferred_language) {
      i18n.changeLanguage(data.user.preferred_language);
    }
    closeLoginModal();
    return data;
  };

  const register = async (userData) => {
    const data = await registerUser(userData);
    if (data.user) {
      setUser(data.user);
      if (data.user.preferred_language && i18n.language !== data.user.preferred_language) {
        i18n.changeLanguage(data.user.preferred_language);
      }
    }
    closeLoginModal();
    return data;
  };

  const logout = async () => {
    try {
      await logoutUser();
    } catch (err) {
      console.warn("Logout error:", err);
    }
    setUser(null);
    try {
      sessionStorage.removeItem("sahayak_chat_history");
    } catch {}
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        loginModalState,
        openLoginModal,
        closeLoginModal,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

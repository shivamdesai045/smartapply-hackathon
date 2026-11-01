import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function Login() {
  const { t, i18n } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!formData.email.trim()) return setError("Email is required.");
    if (!formData.password) return setError("Password is required.");

    setLoading(true);
    try {
      const data = await login(formData.email, formData.password);
      // Auto switch language based on user preference if desired
      if (data.user?.preferred_language) {
        i18n.changeLanguage(data.user.preferred_language);
      }
      navigate("/");
    } catch (err) {
      setError(err.message || "Invalid email or password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative flex items-center justify-center px-6 py-12">
      {/* Background Image */}
      <div 
        className="absolute inset-0 z-0" 
        style={{
          backgroundImage: "url('https://commons.wikimedia.org/wiki/Special:FilePath/India_Gate_early_morning.jpg')",
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      />
      {/* Dark Overlay */}
      <div className="absolute inset-0 bg-black/60 z-0" />

      {/* Main Card */}
      <div className="relative z-10 bg-white dark:bg-gray-800 shadow-xl rounded-2xl p-8 w-full max-w-md border border-gray-100 dark:border-gray-700">
        <h1 className="text-3xl font-bold text-brand-700 dark:text-brand-400 mb-2 text-center">Welcome Back</h1>
        <p className="text-gray-500 dark:text-gray-400 text-center mb-8 text-sm">Sign in to your SmartApply account</p>

        {error && (
          <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm mb-4 border border-red-200 text-center font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email Address</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="rahul@example.com"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none transition bg-white dark:bg-gray-700 dark:text-white"
              required
            />
          </div>

          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Password</label>
              <button type="button" className="text-brand-600 dark:text-brand-400 hover:underline text-xs font-medium">Forgot Password?</button>
            </div>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Enter your password"
                className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none transition pr-10 bg-white dark:bg-gray-700 dark:text-white"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600 text-sm font-medium"
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className={`w-full text-white rounded-lg py-2.5 font-semibold text-sm transition mt-2 ${
              loading ? "bg-brand-400 cursor-not-allowed" : "bg-brand-600 hover:bg-brand-700 shadow-md"
            }`}
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
          Don't have an account?{" "}
          <Link to="/register" className="text-brand-600 dark:text-brand-400 font-semibold hover:underline">
            Create one now
          </Link>
        </div>
      </div>
    </div>
  );
}

export default Login;
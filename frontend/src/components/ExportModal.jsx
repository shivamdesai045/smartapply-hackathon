import { useState, useEffect } from "react";
import { createExportFile, downloadDetailsJson } from "../lib/exportProfile";
import { sendProfileToExtension, pingExtension } from "../lib/extensionBridge";

function ExportModal({ isOpen, onClose, initialProfile = {}, onProfileChange }) {
  const [profile, setProfile] = useState({
    fullName: "",
    fatherName: "",
    motherName: "",
    dob: "",
    gender: "",
    mobile: "",
    email: "",
    address: "",
    city: "",
    district: "",
    state: "",
    pin: "",
    ...initialProfile,
  });

  const [passphrase, setPassphrase] = useState("");
  const [error, setError] = useState(null);
  const [warnings, setWarnings] = useState([]);
  const [exporting, setExporting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [success, setSuccess] = useState(false);
  const [syncSuccess, setSyncSuccess] = useState(false);
  const [hasExtension, setHasExtension] = useState(false);

  useEffect(() => {
    pingExtension().then((detected) => setHasExtension(detected));
  }, [isOpen]);

  useEffect(() => {
    if (initialProfile) {
      setProfile((prev) => ({
        ...prev,
        ...initialProfile,
      }));
    }
  }, [initialProfile]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleChange = (field, value) => {
    setProfile((prev) => {
      const next = { ...prev, [field]: value };
      if (onProfileChange) onProfileChange(next);
      return next;
    });
  };

  const handleExport = async (e) => {
    e.preventDefault();
    setError(null);
    setWarnings([]);
    setSuccess(false);

    if (passphrase && passphrase.length < 8) {
      setError("Passphrase must be at least 8 characters long, or leave it blank for an unprotected file.");
      return;
    }

    setExporting(true);
    try {
      const { text, warnings: exportWarns } = await createExportFile(profile, passphrase);
      downloadDetailsJson(text, "sahayak-details.json");
      setWarnings(exportWarns || []);
      setSuccess(true);
    } catch (err) {
      setError(err.message || "Failed to generate details file.");
    } finally {
      setExporting(false);
    }
  };

  const handleDirectSync = async () => {
    setError(null);
    setSuccess(false);
    setSyncSuccess(false);
    setSyncing(true);
    try {
      await sendProfileToExtension(profile);
      setSyncSuccess(true);
    } catch (err) {
      setError(err.message || "Failed to sync to extension. Ensure the extension is enabled.");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="export-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm overflow-y-auto"
    >
      <div className="relative w-full max-w-2xl bg-white dark:bg-gray-800 rounded-3xl shadow-2xl border border-gray-200 dark:border-gray-700 p-6 sm:p-8 my-8 space-y-6">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition"
          aria-label="Close modal"
        >
          ✕
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3">
          <span className="text-3xl">📤</span>
          <div>
            <h2 id="export-modal-title" className="text-xl font-bold text-gray-900 dark:text-white">
              Export Corrected Details
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Download your verified details to import directly into the Sahayak AutoFill browser extension.
            </p>
          </div>
        </div>

        {/* Statutory & Privacy Notice Banner */}
        <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 rounded-2xl p-4 text-xs space-y-2 text-amber-900 dark:text-amber-200">
          <p className="font-semibold flex items-center gap-1.5">
            <span>🛡️</span> Privacy & Security Notice
          </p>
          <ul className="list-disc pl-5 space-y-1 text-amber-800 dark:text-amber-300">
            <li>
              <strong>Aadhaar and PAN numbers are NEVER included</strong> in the exported file. You type them manually in the extension.
            </li>
            <li>
              If you export an unprotected file (no passphrase), <strong>delete the downloaded file after importing</strong> it into the extension.
            </li>
            <li>
              <strong>Statutory Notice:</strong> Sahayak is an independent tool and is not affiliated with, authorized, or endorsed by the Government of India.
            </li>
          </ul>
        </div>

        {/* Form Body */}
        <form onSubmit={handleExport} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div>
              <label className="block font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Full Name
              </label>
              <input
                type="text"
                value={profile.fullName || ""}
                onChange={(e) => handleChange("fullName", e.target.value)}
                placeholder="Full Name"
                className="w-full px-3 py-2 border rounded-xl dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Date of Birth (YYYY-MM-DD)
              </label>
              <input
                type="text"
                value={profile.dob || ""}
                onChange={(e) => handleChange("dob", e.target.value)}
                placeholder="YYYY-MM-DD"
                className="w-full px-3 py-2 border rounded-xl dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Father's Name
              </label>
              <input
                type="text"
                value={profile.fatherName || ""}
                onChange={(e) => handleChange("fatherName", e.target.value)}
                placeholder="Father's Name"
                className="w-full px-3 py-2 border rounded-xl dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Mother's Name
              </label>
              <input
                type="text"
                value={profile.motherName || ""}
                onChange={(e) => handleChange("motherName", e.target.value)}
                placeholder="Mother's Name"
                className="w-full px-3 py-2 border rounded-xl dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Gender
              </label>
              <select
                value={profile.gender || ""}
                onChange={(e) => handleChange("gender", e.target.value)}
                className="w-full px-3 py-2 border rounded-xl dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              >
                <option value="">Select Gender</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Mobile Number (10 digits)
              </label>
              <input
                type="tel"
                maxLength="10"
                value={profile.mobile || ""}
                onChange={(e) => handleChange("mobile", e.target.value)}
                placeholder="10-digit mobile"
                className="w-full px-3 py-2 border rounded-xl dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Email Address
              </label>
              <input
                type="email"
                value={profile.email || ""}
                onChange={(e) => handleChange("email", e.target.value)}
                placeholder="user@example.com"
                className="w-full px-3 py-2 border rounded-xl dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 dark:text-gray-300 mb-1">
                PIN Code (6 digits)
              </label>
              <input
                type="text"
                maxLength="6"
                value={profile.pin || ""}
                onChange={(e) => handleChange("pin", e.target.value)}
                placeholder="PIN Code"
                className="w-full px-3 py-2 border rounded-xl dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Address
              </label>
              <textarea
                rows="2"
                value={profile.address || ""}
                onChange={(e) => handleChange("address", e.target.value)}
                placeholder="Street address / Landmark"
                className="w-full px-3 py-2 border rounded-xl dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 dark:text-gray-300 mb-1">
                City / Village
              </label>
              <input
                type="text"
                value={profile.city || ""}
                onChange={(e) => handleChange("city", e.target.value)}
                placeholder="City or Town"
                className="w-full px-3 py-2 border rounded-xl dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 dark:text-gray-300 mb-1">
                District
              </label>
              <input
                type="text"
                value={profile.district || ""}
                onChange={(e) => handleChange("district", e.target.value)}
                placeholder="District"
                className="w-full px-3 py-2 border rounded-xl dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 dark:text-gray-300 mb-1">
                State
              </label>
              <input
                type="text"
                value={profile.state || ""}
                onChange={(e) => handleChange("state", e.target.value)}
                placeholder="State"
                className="w-full px-3 py-2 border rounded-xl dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
            </div>

            {/* Optional Passphrase Input */}
            <div className="sm:col-span-2 pt-2 border-t border-gray-200 dark:border-gray-700">
              <label className="block font-semibold text-gray-800 dark:text-gray-200 mb-1">
                File Passphrase (Optional, 8+ characters)
              </label>
              <p className="text-[11px] text-gray-500 mb-1.5">
                If entered, the exported file will be strongly encrypted (AES-256-GCM + PBKDF2-SHA256). You will enter this passphrase when importing into the extension. Leave empty for an unencrypted file.
              </p>
              <input
                type="password"
                value={passphrase}
                onChange={(e) => setPassphrase(e.target.value)}
                placeholder="Enter 8+ character passphrase (or leave empty)"
                className="w-full px-3 py-2 border rounded-xl dark:bg-gray-700 dark:border-gray-600 dark:text-white font-mono text-xs"
              />
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-950/40 border border-red-300 dark:border-red-800 rounded-xl text-red-700 dark:text-red-300 text-xs">
              ⚠️ {error}
            </div>
          )}

          {warnings.length > 0 && (
            <div className="p-3 bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 rounded-xl text-amber-700 dark:text-amber-300 text-xs space-y-1">
              <p className="font-semibold">Notice for skipped fields:</p>
              <ul className="list-disc pl-5">
                {warnings.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {success && (
            <div className="p-3 bg-green-50 dark:bg-green-950/40 border border-green-300 dark:border-green-800 rounded-xl text-green-700 dark:text-green-300 text-xs">
              ✓ <strong>sahayak-details.json</strong> downloaded successfully! Open the Sahayak AutoFill browser extension and click "Import file".
            </div>
          )}

          {syncSuccess && (
            <div className="p-3 bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-300 dark:border-indigo-800 rounded-xl text-indigo-700 dark:text-indigo-300 text-xs">
              ⚡ <strong>Directly Synced to Extension!</strong> Open the Sahayak AutoFill extension in your browser to encrypt and save with your passphrase.
            </div>
          )}

          {/* Action buttons */}
          <div className="flex flex-wrap justify-end gap-3 pt-3 border-t border-gray-100 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-xl text-xs font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleDirectSync}
              disabled={syncing}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-md transition flex items-center gap-1.5"
            >
              <span>⚡</span>
              {syncing ? "Syncing..." : "1-Click Sync to Extension"}
            </button>
            <button
              type="submit"
              disabled={exporting}
              className="px-4 py-2 bg-gray-800 hover:bg-gray-900 dark:bg-gray-700 dark:hover:bg-gray-600 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-md transition flex items-center gap-1.5"
            >
              <span>📥</span>
              {exporting ? "Exporting..." : "Download JSON File"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ExportModal;


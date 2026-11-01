
import { MessageCircle, X } from "lucide-react";
import { useTranslation } from "react-i18next";

export default function ChatButton({ open, onClick }) {
  const { t } = useTranslation();

  return (
    <button
      type="button"
      className="sh-chat-button"
      onClick={onClick}
      aria-label={open ? t("home_close_chat") : t("home_open_chat")}
      aria-expanded={open}
      aria-controls="sahayak-chat-panel"
      title={open ? t("home_close_chat") : t("home_open_chat")}
    >
      {open ? (
        <X size={25} strokeWidth={2} aria-hidden="true" />
      ) : (
        <MessageCircle size={25} strokeWidth={2} aria-hidden="true" />
      )}
    </button>
  );
}

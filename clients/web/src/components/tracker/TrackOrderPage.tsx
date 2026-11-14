import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "../../store";
import { restoreOrder, resetOrder } from "../../store/slices/orderSlice";
import { LiveStatusTracker } from "./LiveStatusTracker";
import { Search, ArrowLeft, PackageCheck, Mail, MessageSquare, AlertCircle } from "lucide-react";

interface TrackOrderPageProps {
  onBack: () => void;
  initialOrderId?: string;
}

export const TrackOrderPage: React.FC<TrackOrderPageProps> = ({ onBack, initialOrderId }) => {
  const dispatch = useDispatch();
  const { dict } = useSelector((state: RootState) => state.language);
  const { activeOrderId } = useSelector((state: RootState) => state.order);
  const [searchInput, setSearchInput] = useState(initialOrderId || "");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
    if (initialOrderId && !activeOrderId) {
      dispatch(restoreOrder(initialOrderId));
    }
  }, [initialOrderId, activeOrderId, dispatch]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanId = searchInput.trim();
    if (!cleanId) {
      setErrorMsg(dict.trackPage.invalidIdError);
      return;
    }
    setErrorMsg(null);
    dispatch(restoreOrder(cleanId));
  };

  const handleReset = () => {
    dispatch(resetOrder());
    setSearchInput("");
    setErrorMsg(null);
  };

  return (
    <div className="track-page-container">
      <div className="track-page-content">
        {/* Back Link */}
        <button
          type="button"
          onClick={onBack}
          className="legal-back-btn"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>{dict.legal.backButton}</span>
        </button>

        {/* Page Header */}
        <div className="track-header text-center" style={{ textAlign: "center", marginBottom: "36px" }}>
          <div className="legal-card-icon" style={{ margin: "0 auto 16px", background: "rgba(56, 189, 248, 0.1)", border: "1px solid rgba(56, 189, 248, 0.3)", color: "var(--accent-blue)" }}>
            <PackageCheck className="w-6 h-6" />
          </div>
          <h1 className="legal-title" style={{ fontSize: "2rem" }}>
            {dict.trackPage.title}
          </h1>
          <p className="legal-subtitle" style={{ maxWidth: "560px", margin: "8px auto 0" }}>
            {dict.trackPage.subtitle}
          </p>
        </div>

        {/* Tracking Search Card */}
        <div className="track-search-card">
          <form onSubmit={handleSearch} className="track-search-form">
            <input
              id="track-order-page-input"
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder={dict.trackPage.inputPlaceholder}
              className="track-search-input"
            />
            <button
              type="submit"
              className="track-search-btn"
            >
              <Search className="w-4 h-4" />
              <span>{dict.trackPage.searchBtn}</span>
            </button>
          </form>

          {errorMsg && (
            <div style={{ marginTop: "12px", fontSize: "0.82rem", color: "#f87171", display: "flex", alignItems: "center", gap: "6px" }}>
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {activeOrderId && (
            <div style={{ marginTop: "16px", paddingTop: "14px", borderTop: "1px solid var(--border-color)", display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "0.85rem", color: "var(--text-muted)" }}>
              <span>
                {dict.trackPage.activeOrderLabel} <strong style={{ color: "var(--accent-blue)", fontFamily: "var(--font-mono)" }}>{activeOrderId}</strong>
              </span>
              <button
                type="button"
                onClick={handleReset}
                style={{ background: "none", border: "none", color: "var(--accent-blue)", textDecoration: "underline", cursor: "pointer", fontSize: "0.85rem" }}
              >
                {dict.trackPage.searchAnotherBtn}
              </button>
            </div>
          )}
        </div>

        {/* Order Display Area */}
        {activeOrderId ? (
          <div className="generator-tracker-area" style={{ marginTop: "32px" }}>
            <LiveStatusTracker
              onAdjustParameters={() => {
                dispatch(resetOrder());
                if (onBack) {
                  onBack();
                } else if (typeof window !== "undefined") {
                  window.location.href = "/#generador";
                }
              }}
            />
          </div>
        ) : (
          /* Helper Tips Card */
          <div className="track-search-card" style={{ background: "rgba(17, 24, 39, 0.5)" }}>
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "#fff", marginBottom: "14px" }}>
              {dict.trackPage.helpTitle}
            </h3>
            <div className="track-tips-grid">
              <div className="track-tip-card">
                <Mail className="w-5 h-5 text-sky-400 shrink-0" style={{ color: "var(--accent-blue)" }} />
                <div>
                  <strong style={{ display: "block", color: "#fff", marginBottom: "4px" }}>{dict.trackPage.helpEmailTitle}</strong>
                  {dict.trackPage.helpEmailDesc}
                </div>
              </div>
              <div className="track-tip-card">
                <MessageSquare className="w-5 h-5 text-emerald-400 shrink-0" style={{ color: "var(--accent-emerald)" }} />
                <div>
                  <strong style={{ display: "block", color: "#fff", marginBottom: "4px" }}>{dict.trackPage.helpWhatsappTitle}</strong>
                  {dict.trackPage.helpWhatsappDesc}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TrackOrderPage;

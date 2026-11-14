import React, { useState } from "react";
import { useSelector } from "react-redux";
import { RootState } from "../../store";
import {
  Copy,
  Check,
  ExternalLink,
  MessageSquare,
  Mail,
  Phone,
  Building2,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Send,
} from "lucide-react";

export interface PlaybookCompany {
  index: number;
  company_name: string;
  clean_name?: string;
  tax_id?: string;
  tax_id_type?: string;
  country?: string;
  city?: string;
  website?: string;
  decision_maker_name?: string;
  decision_maker_title?: string;
  email?: string;
  phone?: string;
  recommended_angle?: string;
  touches?: {
    touch1_linkedin?: string;
    touch2_email?: {
      subject: string;
      body: string;
    };
    touch3_followup?: {
      subject: string;
      body: string;
    };
    touch4_social_proof?: {
      subject: string;
      body: string;
    };
    touch5_breakup?: {
      subject: string;
      body: string;
    };
  };
  triggers?: {
    contracts_won?: string;
    entity?: string;
    intent?: string;
    expansion?: string;
  };
}

interface OutreachPlaybookProps {
  companies: PlaybookCompany[];
}

export const OutreachPlaybook: React.FC<OutreachPlaybookProps> = ({ companies }) => {
  const { dict } = useSelector((state: RootState) => state.language);
  const pb = dict.playbook;
  const [expandedIndex, setExpandedIndex] = useState<number>(0);
  const [activeTab, setActiveTab] = useState<{ [key: number]: number }>({});
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  if (!companies || companies.length === 0) {
    return (
      <div className="playbook-empty-state" data-testid="outreach-playbook">
        <Sparkles className="playbook-empty-icon" />
        <p className="playbook-empty-title">{pb.emptyTitle}</p>
        <p className="playbook-empty-subtitle">
          {pb.emptySubtitle}
        </p>
      </div>
    );
  }

  const handleCopy = (text: string, key: string) => {
    if (navigator?.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    }
  };

  const getCleanPhoneDigits = (rawPhone?: string): string => {
    if (!rawPhone) return "";
    return rawPhone.replace(/\D/g, "");
  };

  const openWhatsApp = (phone?: string, text?: string) => {
    const digits = getCleanPhoneDigits(phone);
    if (!digits) return;
    const url = `https://wa.me/${digits}?text=${encodeURIComponent(text || "")}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const getCountryFlag = (country?: string) => {
    const c = (country || "CO").toUpperCase();
    if (c === "EC") return "🇪🇨";
    if (c === "DO") return "🇩🇴";
    if (c === "MULTI") return "🌎";
    return "🇨🇴";
  };

  return (
    <div className="playbook-wrapper" data-testid="outreach-playbook">
      {/* Header Banner */}
      <div className="playbook-header-banner">
        <div className="playbook-header-content">
          <div className="playbook-header-title-row">
            <Send className="w-5 h-5 text-sky-400" />
            <h4 className="playbook-header-title">
              {pb.title}
            </h4>
          </div>
          <p className="playbook-header-subtitle">
            {pb.subtitle}
          </p>
        </div>
        <div className="playbook-badge-count">
          <span className="playbook-badge-num">{companies.length}</span> {pb.badgeSuffix}
        </div>
      </div>

      <div className="playbook-companies-list">
        {companies.map((comp, idx) => {
          const isExpanded = expandedIndex === idx;
          const currentTouchTab = activeTab[idx] || 1; // 1 to 5
          const flag = getCountryFlag(comp.country);

          const touches = comp.touches || {};
          const t1 = touches.touch1_linkedin || "";
          const t2 = touches.touch2_email || { subject: "", body: "" };
          const t3 = touches.touch3_followup || { subject: "", body: "" };
          const t4 = touches.touch4_social_proof || { subject: "", body: "" };
          const t5 = touches.touch5_breakup || { subject: "", body: "" };

          return (
            <div
              key={idx}
              className={`playbook-company-card ${isExpanded ? "expanded" : ""}`}
            >
              {/* Accordion Header */}
              <button
                type="button"
                onClick={() => setExpandedIndex(isExpanded ? -1 : idx)}
                className="playbook-card-header"
              >
                <div className="playbook-company-left">
                  <div className="playbook-index-pill">{idx + 1}</div>
                  <div className="playbook-company-meta">
                    <div className="playbook-company-title-row">
                      <span className="playbook-flag">{flag}</span>
                      <span className="playbook-company-name">
                        {comp.company_name}
                      </span>
                      {comp.tax_id && (
                        <span className="playbook-tax-id">
                          {comp.tax_id_type || "NIT"}: {comp.tax_id}
                        </span>
                      )}
                    </div>
                    <div className="playbook-company-subline">
                      <span>{comp.city}</span>
                      <span className="playbook-dot">•</span>
                      <span className="playbook-dm-name">
                        {comp.decision_maker_name || "Contacto Registrado"} (
                        {comp.decision_maker_title || "Representante Legal"})
                      </span>
                    </div>
                  </div>
                </div>

                <div className="playbook-card-header-actions">
                  {comp.triggers?.intent && (
                    <span className="playbook-intent-tag">
                      {comp.triggers.intent}
                    </span>
                  )}
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  )}
                </div>
              </button>

              {/* Expanded Card Body */}
              {isExpanded && (
                <div className="playbook-card-body">
                  {/* Account Intelligence Strip */}
                  <div className="playbook-intel-grid">
                    <div className="playbook-intel-card">
                      <div className="playbook-intel-label">
                        <Mail className="w-3.5 h-3.5 text-sky-400" />
                        <span>{pb.verifiedEmail}</span>
                      </div>
                      <div className="playbook-intel-value font-mono">
                        {comp.email || pb.notRegistered}
                      </div>
                    </div>

                    <div className="playbook-intel-card">
                      <div className="playbook-intel-label">
                        <Phone className="w-3.5 h-3.5 text-emerald-400" />
                        <span>{pb.directPhone}</span>
                      </div>
                      <div className="playbook-intel-value font-mono playbook-phone-row">
                        <span>{comp.phone || pb.notRegistered}</span>
                        {comp.phone && (
                          <button
                            type="button"
                            onClick={() =>
                              openWhatsApp(
                                comp.phone,
                                `Hola ${comp.decision_maker_name || ""}, te contacto de parte de nuestro equipo comercial.`
                              )
                            }
                            className="playbook-whatsapp-link"
                            title="Abrir WhatsApp"
                          >
                            WhatsApp
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="playbook-intel-card">
                      <div className="playbook-intel-label">
                        <Building2 className="w-3.5 h-3.5 text-purple-400" />
                        <span>{pb.companyWebsite}</span>
                      </div>
                      <div className="playbook-intel-value">
                        {comp.website && comp.website.startsWith("http") ? (
                          <a
                            href={comp.website}
                            target="_blank"
                            rel="noreferrer"
                            className="playbook-website-link"
                          >
                            <span className="truncate">{comp.website}</span>
                            <ExternalLink className="w-3 h-3 shrink-0" />
                          </a>
                        ) : (
                          <span className="text-slate-400">{comp.website || pb.notAvailable}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Trigger Angle Alert */}
                  {comp.recommended_angle && (
                    <div className="playbook-angle-box">
                      <Sparkles className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="playbook-angle-heading">{pb.recommendedAngle} </span>
                        <span className="playbook-angle-text">{comp.recommended_angle}</span>
                        {comp.triggers?.contracts_won && (
                          <span className="playbook-angle-contracts">
                            {pb.contractsWon} {comp.triggers.contracts_won} • {comp.triggers.entity}
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Touch Navigation Tabs */}
                  <div className="playbook-touch-tabs">
                    {[
                      { num: 1, label: pb.touch1Tab },
                      { num: 2, label: pb.touch2Tab },
                      { num: 3, label: pb.touch3Tab },
                      { num: 4, label: pb.touch4Tab },
                      { num: 5, label: pb.touch5Tab },
                    ].map((tab) => (
                      <button
                        key={tab.num}
                        type="button"
                        onClick={() =>
                          setActiveTab((prev) => ({ ...prev, [idx]: tab.num }))
                        }
                        className={`playbook-touch-tab-btn ${currentTouchTab === tab.num ? "active" : ""}`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>

                  {/* Touch Content Panel */}
                  <div className="playbook-touch-panel">
                    {/* Touch 1: LinkedIn */}
                    {currentTouchTab === 1 && (
                      <div className="playbook-touch-section">
                        <div className="playbook-touch-title-row">
                          <span className="playbook-touch-title">
                            {pb.touch1Title}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleCopy(t1, `t1_${idx}`)}
                            className="playbook-btn-copy"
                          >
                            {copiedKey === `t1_${idx}` ? (
                              <>
                                <Check className="w-3.5 h-3.5 text-emerald-400" />
                                <span>{pb.copied}</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3.5 h-3.5" />
                                <span>{pb.copyNote}</span>
                              </>
                            )}
                          </button>
                        </div>
                        <div className="playbook-touch-body select-all">
                          {t1 || pb.noNoteAvailable}
                        </div>
                      </div>
                    )}

                    {/* Touch 2: Cold Email */}
                    {currentTouchTab === 2 && (
                      <div className="playbook-touch-section">
                        <div className="playbook-subject-row">
                          <div className="playbook-subject-label">
                            <span className="playbook-subject-tag">{pb.subjectLabel}</span>
                            <span className="playbook-subject-text">{t2.subject}</span>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleCopy(t2.subject, `t2_sub_${idx}`)}
                            className="playbook-btn-copy-sm"
                          >
                            {copiedKey === `t2_sub_${idx}` ? (
                              <Check className="w-3 h-3 text-emerald-400" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                            <span>{pb.copySubject}</span>
                          </button>
                        </div>

                        <div className="playbook-touch-body select-all">
                          {t2.body || pb.bodyNotAvailable}
                        </div>

                        <div className="playbook-touch-actions">
                          <button
                            type="button"
                            onClick={() => handleCopy(`${pb.subjectLabel}${t2.subject}\n\n${t2.body}`, `t2_all_${idx}`)}
                            className="playbook-btn-copy-full"
                          >
                            {copiedKey === `t2_all_${idx}` ? (
                              <Check className="w-3.5 h-3.5" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                            <span>{pb.copyFullEmail}</span>
                          </button>

                          {comp.phone && (
                            <button
                              type="button"
                              onClick={() => openWhatsApp(comp.phone, t2.body)}
                              className="playbook-btn-whatsapp"
                            >
                              <MessageSquare className="w-3.5 h-3.5" />
                              <span>{pb.sendWhatsapp}</span>
                            </button>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Touch 3: Follow-up */}
                    {currentTouchTab === 3 && (
                      <div className="playbook-touch-section">
                        <div className="playbook-subject-row">
                          <div className="playbook-subject-label">
                            <span className="playbook-subject-tag">{pb.subjectFollowupLabel}</span>
                            <span className="playbook-subject-text">{t3.subject}</span>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleCopy(t3.subject, `t3_sub_${idx}`)}
                            className="playbook-btn-copy-sm"
                          >
                            {copiedKey === `t3_sub_${idx}` ? (
                              <Check className="w-3 h-3 text-emerald-400" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                            <span>{pb.copySubject}</span>
                          </button>
                        </div>

                        <div className="playbook-touch-body select-all">
                          {t3.body || pb.bodyNotAvailable}
                        </div>

                        <div className="playbook-touch-actions">
                          <button
                            type="button"
                            onClick={() => handleCopy(`${pb.subjectFollowupLabel}${t3.subject}\n\n${t3.body}`, `t3_all_${idx}`)}
                            className="playbook-btn-copy-full"
                          >
                            {copiedKey === `t3_all_${idx}` ? (
                              <Check className="w-3.5 h-3.5" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                            <span>{pb.copyFollowup}</span>
                          </button>

                          {comp.phone && (
                            <button
                              type="button"
                              onClick={() => openWhatsApp(comp.phone, t3.body)}
                              className="playbook-btn-whatsapp"
                            >
                              <MessageSquare className="w-3.5 h-3.5" />
                              <span>{pb.sendWhatsapp}</span>
                            </button>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Touch 4: Social Proof */}
                    {currentTouchTab === 4 && (
                      <div className="playbook-touch-section">
                        <div className="playbook-subject-row">
                          <div className="playbook-subject-label">
                            <span className="playbook-subject-tag">{pb.subjectLabel}</span>
                            <span className="playbook-subject-text">{t4.subject}</span>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleCopy(t4.subject, `t4_sub_${idx}`)}
                            className="playbook-btn-copy-sm"
                          >
                            {copiedKey === `t4_sub_${idx}` ? (
                              <Check className="w-3 h-3 text-emerald-400" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                            <span>{pb.copySubject}</span>
                          </button>
                        </div>

                        <div className="playbook-touch-body select-all">
                          {t4.body || pb.bodyNotAvailable}
                        </div>

                        <div className="playbook-touch-actions">
                          <button
                            type="button"
                            onClick={() => handleCopy(`${pb.subjectLabel}${t4.subject}\n\n${t4.body}`, `t4_all_${idx}`)}
                            className="playbook-btn-copy-full"
                          >
                            {copiedKey === `t4_all_${idx}` ? (
                              <Check className="w-3.5 h-3.5" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                            <span>{pb.copySocialProof}</span>
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Touch 5: Breakup */}
                    {currentTouchTab === 5 && (
                      <div className="playbook-touch-section">
                        <div className="playbook-subject-row">
                          <div className="playbook-subject-label">
                            <span className="playbook-subject-tag">{pb.subjectLabel}</span>
                            <span className="playbook-subject-text">{t5.subject}</span>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleCopy(t5.subject, `t5_sub_${idx}`)}
                            className="playbook-btn-copy-sm"
                          >
                            {copiedKey === `t5_sub_${idx}` ? (
                              <Check className="w-3 h-3 text-emerald-400" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                            <span>{pb.copySubject}</span>
                          </button>
                        </div>

                        <div className="playbook-touch-body select-all">
                          {t5.body || pb.bodyNotAvailable}
                        </div>

                        <div className="playbook-touch-actions">
                          <button
                            type="button"
                            onClick={() => handleCopy(`${pb.subjectLabel}${t5.subject}\n\n${t5.body}`, `t5_all_${idx}`)}
                            className="playbook-btn-copy-full"
                          >
                            {copiedKey === `t5_all_${idx}` ? (
                              <Check className="w-3.5 h-3.5" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                            <span>{pb.copyBreakup}</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

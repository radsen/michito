import React from "react";
import { useSelector } from "react-redux";
import { RootState } from "../../store";
import { CheckCircle2, Globe, MailCheck, FileText, Scale, ShieldCheck } from "lucide-react";

export const DeliverablesStandards: React.FC = () => {
  const { dict } = useSelector((state: RootState) => state.language);
  const d = dict.deliverables;

  return (
    <section id="entregables" className="deliverables-section">
      <div className="section-container">
        <div className="section-header">
          <span className="section-kicker">{d.kicker}</span>
          <h2 className="section-title">{d.title}</h2>
          <p className="section-subtitle">{d.subtitle}</p>
        </div>

        {/* 4 Pillars Grid */}
        <div className="deliverables-grid">
          <div className="deliverable-card">
            <div className="deliverable-tag">{d.comp1Tag}</div>
            <div className="deliverable-val">{d.comp1Val}</div>
            <h3 className="deliverable-title">{d.comp1Title}</h3>
            <p className="deliverable-desc">{d.comp1Desc}</p>
          </div>

          <div className="deliverable-card">
            <div className="deliverable-tag">{d.comp2Tag}</div>
            <div className="deliverable-val">{d.comp2Val}</div>
            <h3 className="deliverable-title">{d.comp2Title}</h3>
            <p className="deliverable-desc">{d.comp2Desc}</p>
          </div>

          <div className="deliverable-card">
            <div className="deliverable-tag">{d.comp3Tag}</div>
            <div className="deliverable-val">{d.comp3Val}</div>
            <h3 className="deliverable-title">{d.comp3Title}</h3>
            <p className="deliverable-desc">{d.comp3Desc}</p>
          </div>

          <div className="deliverable-card featured-card">
            <div className="deliverable-tag highlight">{d.comp4Tag}</div>
            <div className="deliverable-val text-sky-400">{d.comp4Val}</div>
            <h3 className="deliverable-title">{d.comp4Title}</h3>
            <p className="deliverable-desc">{d.comp4Desc}</p>
          </div>
        </div>

        {/* Scope & Liability Disclaimer Box */}
        <div className="scope-disclaimer-box">
          <div className="disclaimer-header">
            <span className="disclaimer-badge">{d.disclaimerBadge}</span>
            <h3 className="disclaimer-title">{d.disclaimerTitle}</h3>
          </div>
          <div className="disclaimer-body">
            <p>{d.disclaimerP1}</p>
            <p className="mt-3">{d.disclaimerP2}</p>
            <div className="guarantee-pill">
              <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
              <span>{d.replacementGuarantee}</span>
            </div>
          </div>
        </div>

        {/* Regulatory & Habeas Data Banner */}
        <div className="habeas-data-banner">
          <div className="habeas-icon">
            <Scale className="w-6 h-6 text-sky-400" />
          </div>
          <div className="habeas-text">
            <h4>{d.habeasDataTitle}</h4>
            <p>{d.habeasDataDesc}</p>
          </div>
        </div>
      </div>
    </section>
  );
};


import React from "react";
import { useSelector } from "react-redux";
import { RootState } from "../../store";
import {
  Building2,
  Globe,
  MailCheck,
  Sparkles,
  ShieldCheck,
  ArrowRight,
} from "lucide-react";

interface DeliverablesStandardsProps {
  onNavigateTerms?: () => void;
}

export const DeliverablesStandards: React.FC<DeliverablesStandardsProps> = ({ onNavigateTerms }) => {
  const { currentLanguage, dict } = useSelector((state: RootState) => state.language);
  const d = dict.deliverables;
  const isEn = currentLanguage === "en_US";

  const cards = [
    {
      icon: Building2,
      iconColor: "text-sky-400",
      iconBg: "bg-sky-500/10 border-sky-500/25",
      tag: d.comp1Tag,
      title: d.comp1Title,
      val: d.comp1Val,
      desc: d.comp1Desc,
    },
    {
      icon: Globe,
      iconColor: "text-purple-400",
      iconBg: "bg-purple-500/10 border-purple-500/25",
      tag: d.comp2Tag,
      title: d.comp2Title,
      val: d.comp2Val,
      desc: d.comp2Desc,
    },
    {
      icon: MailCheck,
      iconColor: "text-emerald-400",
      iconBg: "bg-emerald-500/10 border-emerald-500/25",
      tag: d.comp3Tag,
      title: d.comp3Title,
      val: d.comp3Val,
      desc: d.comp3Desc,
    },
    {
      icon: Sparkles,
      iconColor: "text-amber-400",
      iconBg: "bg-amber-500/10 border-amber-500/25",
      tag: d.comp4Tag,
      title: d.comp4Title,
      val: d.comp4Val,
      desc: d.comp4Desc,
      featured: true,
    },
  ];

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
          {cards.map((c, i) => {
            const Icon = c.icon;
            return (
              <div
                key={i}
                className={`deliverable-card ${c.featured ? "featured-card" : ""}`}
              >
                <div className="deliverable-card-top">
                  <div className={`deliverable-icon-box ${c.iconColor} ${c.iconBg}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className={`deliverable-tag ${c.featured ? "highlight" : ""}`}>
                    {c.tag}
                  </span>
                </div>

                <div className="deliverable-card-body">
                  <h3 className="deliverable-title">{c.title}</h3>
                  <div className="deliverable-val-pill">{c.val}</div>
                  <p className="deliverable-desc">{c.desc}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Sleek Trust Guarantee Bar & Link to Dedicated Legal Page */}
        <div className="deliverable-trust-bar">
          <div className="deliverable-trust-main">
            <div className="deliverable-trust-badge-pill">
              <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{isEn ? "Fair Replacement Guarantee" : "Garantía de Reposición 2 por 1"}</span>
            </div>
            <p className="deliverable-trust-desc">
              {isEn
                ? "If any corporate inbox exhibits a verifiable hard bounce within 7 days of delivery, it is replaced 2-for-1 at zero additional cost."
                : "Si algún buzón presenta rebote comprobable en los primeros 7 días, se repone 2 por 1 sin costo adicional."}
            </p>
          </div>
          {onNavigateTerms && (
            <button
              type="button"
              onClick={onNavigateTerms}
              className="deliverable-terms-btn group"
            >
              <span>{isEn ? "Terms & Habeas Data" : "Términos y Habeas Data"}</span>
              <ArrowRight className="w-4 h-4 text-sky-400 group-hover:translate-x-0.5 transition-transform" />
            </button>
          )}
        </div>
      </div>
    </section>
  );
};

export default DeliverablesStandards;

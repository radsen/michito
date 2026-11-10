import React from "react";
import { useSelector } from "react-redux";
import { RootState } from "../../store";
import { ShieldCheck, ArrowRight } from "lucide-react";

interface DeliverablesStandardsProps {
  onNavigateTerms?: () => void;
}

export const DeliverablesStandards: React.FC<DeliverablesStandardsProps> = ({ onNavigateTerms }) => {
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

        {/* Sleek Trust Guarantee Bar & Link to Dedicated Legal Page */}
        <div className="deliverable-trust-bar">
          <div className="flex items-center gap-3">
            <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
            <span className="text-xs sm:text-sm text-slate-300">
              <strong>Garantía de Reposición:</strong> Si algún buzón presenta rebote comprobable en los primeros 7 días, se repone 2 por 1 sin costo adicional.
            </span>
          </div>
          {onNavigateTerms && (
            <button
              type="button"
              onClick={onNavigateTerms}
              className="deliverable-terms-link"
            >
              <span>Términos y Habeas Data</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </section>
  );
};

export default DeliverablesStandards;

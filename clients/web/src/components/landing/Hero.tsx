import React from "react";
import { useSelector } from "react-redux";
import { RootState } from "../../store";
import { ShieldCheck, Building, TrendingUp, PenTool, ArrowRight, ArrowDown } from "lucide-react";

export const Hero: React.FC = () => {
  const { dict } = useSelector((state: RootState) => state.language);
  const h = dict.hero;

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <section className="hero-section">
      <div className="hero-container">
        <div className="hero-badge">
          <span>{h.badge}</span>
        </div>

        <h1 className="hero-title">
          {h.titlePrefix}{" "}
          <span className="hero-highlight">{h.titleHighlight}</span>{" "}
          {h.titleSuffix}
        </h1>

        <p className="hero-subtitle">{h.subtitle}</p>

        <div className="hero-cta-group">
          <button onClick={() => scrollTo("generador")} className="hero-primary-btn">
            <span>{h.primaryCta}</span>
            <ArrowRight className="w-5 h-5" />
          </button>
          <button onClick={() => scrollTo("como-funciona")} className="hero-secondary-btn">
            <ArrowDown className="w-4 h-4 text-sky-400" />
            <span>{h.secondaryCta}</span>
          </button>
        </div>

        {/* 4 Metric Cards Strip matching index.html */}
        <div className="hero-stats-grid four-col">
          <div className="stat-card">
            <div className="stat-icon-wrapper text-emerald-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div className="stat-info">
              <h4 className="stat-value">{h.stat1}</h4>
              <p className="stat-desc">{h.stat1Desc}</p>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon-wrapper text-blue-400">
              <Building className="w-6 h-6" />
            </div>
            <div className="stat-info">
              <h4 className="stat-value">{h.stat2}</h4>
              <p className="stat-desc">{h.stat2Desc}</p>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon-wrapper text-amber-400">
              <TrendingUp className="w-6 h-6" />
            </div>
            <div className="stat-info">
              <h4 className="stat-value">{h.stat3}</h4>
              <p className="stat-desc">{h.stat3Desc}</p>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon-wrapper text-purple-400">
              <PenTool className="w-6 h-6" />
            </div>
            <div className="stat-info">
              <h4 className="stat-value">{h.stat4}</h4>
              <p className="stat-desc">{h.stat4Desc}</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

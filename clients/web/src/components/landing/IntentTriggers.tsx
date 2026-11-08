import React from "react";
import { useSelector } from "react-redux";
import { RootState } from "../../store";
import { Landmark, TrendingUp, MapPin } from "lucide-react";

export const IntentTriggers: React.FC = () => {
  const { dict } = useSelector((state: RootState) => state.language);
  const t = dict.triggers;

  return (
    <section id="senales" className="triggers-section">
      <div className="section-container">
        <div className="section-header">
          <span className="section-kicker">{t.kicker}</span>
          <h2 className="section-title">{t.title}</h2>
          <p className="section-subtitle">{t.subtitle}</p>
        </div>

        <div className="triggers-grid">
          <div className="trigger-card">
            <div className="trigger-card-top">
              <span className="trigger-num">01</span>
              <div className="trigger-icon-box text-amber-400 bg-amber-500/10 border-amber-500/20">
                <Landmark className="w-6 h-6" />
              </div>
            </div>
            <h3 className="trigger-title">{t.trigger1Title}</h3>
            <p className="trigger-desc">{t.trigger1Desc}</p>
            <div className="trigger-pill">
              <span>{t.trigger1Tag}</span>
            </div>
          </div>

          <div className="trigger-card">
            <div className="trigger-card-top">
              <span className="trigger-num">02</span>
              <div className="trigger-icon-box text-blue-400 bg-blue-500/10 border-blue-500/20">
                <TrendingUp className="w-6 h-6" />
              </div>
            </div>
            <h3 className="trigger-title">{t.trigger2Title}</h3>
            <p className="trigger-desc">{t.trigger2Desc}</p>
            <div className="trigger-pill">
              <span>{t.trigger2Tag}</span>
            </div>
          </div>

          <div className="trigger-card">
            <div className="trigger-card-top">
              <span className="trigger-num">03</span>
              <div className="trigger-icon-box text-emerald-400 bg-emerald-500/10 border-emerald-500/20">
                <MapPin className="w-6 h-6" />
              </div>
            </div>
            <h3 className="trigger-title">{t.trigger3Title}</h3>
            <p className="trigger-desc">{t.trigger3Desc}</p>
            <div className="trigger-pill">
              <span>{t.trigger3Tag}</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

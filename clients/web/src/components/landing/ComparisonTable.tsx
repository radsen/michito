import React from "react";
import { useSelector } from "react-redux";
import { RootState } from "../../store";
import { XCircle, CheckCircle } from "lucide-react";

export const ComparisonTable: React.FC = () => {
  const { dict } = useSelector((state: RootState) => state.language);

  return (
    <section id="comparativa" className="comparison-section">
      <div className="section-container">
        <div className="section-header">
          <h2 className="section-title">{dict.comparison.title}</h2>
          <p className="section-subtitle">{dict.comparison.subtitle}</p>
        </div>

        <div className="comparison-grid">
          {/* Traditional Card */}
          <div className="comparison-card traditional-card">
            <div className="card-badge-bad">Desactualizado & Costoso</div>
            <h3 className="card-title">{dict.comparison.traditionalTitle}</h3>
            <ul className="comparison-list">
              <li>
                <XCircle className="w-5 h-5 text-rose-500 shrink-0" />
                <span>{dict.comparison.traditional1}</span>
              </li>
              <li>
                <XCircle className="w-5 h-5 text-rose-500 shrink-0" />
                <span>{dict.comparison.traditional2}</span>
              </li>
              <li>
                <XCircle className="w-5 h-5 text-rose-500 shrink-0" />
                <span>{dict.comparison.traditional3}</span>
              </li>
              <li>
                <XCircle className="w-5 h-5 text-rose-500 shrink-0" />
                <span>{dict.comparison.traditional4}</span>
              </li>
            </ul>
          </div>

          {/* Michito Card */}
          <div className="comparison-card michito-card">
            <div className="card-badge-good">Arquitectura On-Demand</div>
            <h3 className="card-title">{dict.comparison.michitoTitle}</h3>
            <ul className="comparison-list">
              <li>
                <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />
                <span>{dict.comparison.michito1}</span>
              </li>
              <li>
                <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />
                <span>{dict.comparison.michito2}</span>
              </li>
              <li>
                <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />
                <span>{dict.comparison.michito3}</span>
              </li>
              <li>
                <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />
                <span>{dict.comparison.michito4}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
};


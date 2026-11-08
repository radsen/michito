import React from "react";
import { useSelector } from "react-redux";
import { RootState } from "../../store";
import { ShieldCheck, Scale, Lock } from "lucide-react";

export const Footer: React.FC = () => {
  const { dict } = useSelector((state: RootState) => state.language);
  const f = dict.footer;

  return (
    <footer className="footer-container">
      <div className="footer-content">
        <div className="footer-brand">
          <div className="footer-logo">
            <span className="brand-logo-badge">導人</span>
            <span className="brand-name">MICHITO</span>
          </div>
          <p className="footer-tagline">{f.tagline}</p>
          <div className="footer-badges">
            <span className="footer-pill">
              <ShieldCheck className="w-3.5 h-3.5" /> Fuentes Institucionales Públicas
            </span>
            <span className="footer-pill">
              <Scale className="w-3.5 h-3.5" /> Ley 1581 (CO) &bull; Ley 172-13 (DO)
            </span>
          </div>
        </div>

        <div className="footer-links-grid">
          <div className="footer-column">
            <h4>Infraestructura & Motor</h4>
            <ul>
              <li>Michito Intent Engine™</li>
              <li>Handshake Socket MX en Vivo</li>
              <li>Auditoría HTTP de Presencia Web</li>
              <li>Underwriting Financiero NIIF</li>
            </ul>
          </div>
          <div className="footer-column">
            <h4>Ecosistema Chiketto</h4>
            <ul>
              <li>Espacios Corporativos & Sedes</li>
              <li>Mantenimiento & Flotas Corporativas</li>
              <li>Soluciones de Bienestar & Salud B2B</li>
              <li>Inteligencia Comercial On-Demand</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="footer-bottom">
        <p>{f.copyright}</p>
        <div className="footer-legal">
          <span className="text-xs text-slate-500">{f.regulatoryNote}</span>
          <span>•</span>
          <a href="#entregables">{f.privacy}</a>
          <span>•</span>
          <a href="#entregables">{f.terms}</a>
        </div>
      </div>
    </footer>
  );
};

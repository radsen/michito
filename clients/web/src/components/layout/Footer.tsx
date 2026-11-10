import React from "react";
import { useSelector } from "react-redux";
import { RootState } from "../../store";
import { ShieldCheck, Scale, Search } from "lucide-react";

interface FooterProps {
  onNavigate?: (path: string) => void;
}

export const Footer: React.FC<FooterProps> = ({ onNavigate }) => {
  const { dict } = useSelector((state: RootState) => state.language);
  const f = dict.footer;

  const handleNavigate = (path: string, e: React.MouseEvent) => {
    e.preventDefault();
    if (onNavigate) {
      onNavigate(path);
    } else {
      window.location.href = path;
    }
  };

  return (
    <footer className="footer-container">
      <div className="footer-content">
        <div className="footer-brand">
          <div
            className="footer-logo cursor-pointer"
            onClick={(e) => handleNavigate("/", e)}
          >
            <div className="brand-logo-badge">
              <span className="brand-logo-letter">M</span>
            </div>
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
            <h4>Acceso & Servicio</h4>
            <ul>
              <li>
                <a
                  href="/rastrear"
                  onClick={(e) => handleNavigate("/rastrear", e)}
                  className="footer-link footer-link-highlight"
                >
                  <Search className="w-3.5 h-3.5" />
                  <span>Rastrear Orden Existente</span>
                </a>
              </li>
              <li>
                <a
                  href="/terminos"
                  onClick={(e) => handleNavigate("/terminos", e)}
                  className="footer-link"
                >
                  Garantía & Reposición
                </a>
              </li>
              <li>
                <a
                  href="/terminos"
                  onClick={(e) => handleNavigate("/terminos", e)}
                  className="footer-link"
                >
                  Cumplimiento Habeas Data
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div className="footer-bottom">
        <p>{f.copyright}</p>
        <div className="footer-legal">
          <span className="text-xs text-slate-500">{f.regulatoryNote}</span>
          <span>•</span>
          <a
            href="/terminos"
            onClick={(e) => handleNavigate("/terminos", e)}
            className="footer-legal-link"
          >
            {f.privacy}
          </a>
          <span>•</span>
          <a
            href="/terminos"
            onClick={(e) => handleNavigate("/terminos", e)}
            className="footer-legal-link"
          >
            {f.terms}
          </a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;

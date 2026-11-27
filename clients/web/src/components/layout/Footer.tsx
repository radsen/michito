import React from "react";
import { useSelector } from "react-redux";
import { RootState } from "../../store";
import { ShieldCheck, Search } from "lucide-react";

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
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>{f.complianceBadge}</span>
            </span>
          </div>
        </div>

        <div className="footer-links-grid">
          <div className="footer-column">
            <h4>{f.colPlatform}</h4>
            <ul>
              <li>
                <a
                  href="/#generador"
                  onClick={(e) => handleNavigate("/#generador", e)}
                  className="footer-link"
                >
                  {f.linkConfigure}
                </a>
              </li>
              <li>
                <a
                  href="/#como-funciona"
                  onClick={(e) => handleNavigate("/#como-funciona", e)}
                  className="footer-link"
                >
                  {f.linkHowItWorks}
                </a>
              </li>
              <li>
                <a
                  href="/#precios"
                  onClick={(e) => handleNavigate("/#precios", e)}
                  className="footer-link"
                >
                  {f.linkPricing}
                </a>
              </li>
            </ul>
          </div>
          <div className="footer-column">
            <h4>{f.colService}</h4>
            <ul>
              <li>
                <a
                  href="/track"
                  onClick={(e) => handleNavigate("/track", e)}
                  className="footer-link footer-link-highlight"
                >
                  <Search className="w-3.5 h-3.5" />
                  <span>{f.linkTrack}</span>
                </a>
              </li>
              <li>
                <a
                  href="/terms#garantia"
                  onClick={(e) => handleNavigate("/terms", e)}
                  className="footer-link"
                >
                  {f.linkWarranty}
                </a>
              </li>
              <li>
                <a
                  href="/terms#habeas-data"
                  onClick={(e) => handleNavigate("/terms", e)}
                  className="footer-link"
                >
                  {f.linkPrivacy}
                </a>
              </li>
            </ul>
          </div>
          <div className="footer-column">
            <h4>{f.colCoverage}</h4>
            <ul>
              <li>
                <span className="text-xs text-slate-400">🇨🇴 Colombia (SECOP / RUES)</span>
              </li>
              <li>
                <span className="text-xs text-slate-400">🇩🇴 Rep. Dominicana (DGCP)</span>
              </li>
              <li>
                <span className="text-xs text-slate-400">🇪🇨 Ecuador (SERCOP / SRI)</span>
              </li>
              <li>
                <a
                  href="/terms#arco"
                  onClick={(e) => handleNavigate("/terms", e)}
                  className="footer-link text-xs text-sky-400 hover:text-sky-300"
                >
                  {f.linkOptOut}
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div className="footer-bottom">
        <p>{f.copyright}</p>
      </div>
    </footer>
  );
};

export default Footer;

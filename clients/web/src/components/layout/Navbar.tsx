import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "../../store";
import { toggleLanguage } from "../../store/slices/languageSlice";
import { setMobileNavOpen } from "../../store/slices/uiSlice";
import {
  Menu,
  X,
  Workflow,
  ShieldCheck,
  Tag,
} from "lucide-react";

interface NavbarProps {
  onNavigate?: (path: string) => void;
  currentPath?: string;
}

export const Navbar: React.FC<NavbarProps> = ({ onNavigate, currentPath = "/" }) => {
  const dispatch = useDispatch();
  const { currentLanguage, dict } = useSelector((state: RootState) => state.language);
  const { isMobileNavOpen } = useSelector((state: RootState) => state.ui);

  const handleNavClick = (sectionId: string) => {
    dispatch(setMobileNavOpen(false));
    if (onNavigate && currentPath !== "/") {
      onNavigate(`/#${sectionId}`);
    } else {
      const el = document.getElementById(sectionId);
      if (el) {
        el.scrollIntoView({ behavior: "smooth" });
      }
    }
  };

  const handleLogoClick = () => {
    dispatch(setMobileNavOpen(false));
    if (onNavigate && currentPath !== "/") {
      onNavigate("/");
    } else {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  return (
    <header className="navbar-container">
      <div className="navbar-content">
        {/* Brand Logo - Aligned Left */}
        <div className="navbar-brand" onClick={handleLogoClick}>
          <div className="brand-logo-badge">
            <span className="brand-logo-letter">M</span>
          </div>
          <div className="brand-titles">
            <span className="brand-name">MICHITO</span>
            <span className="brand-sub">B2B Intent Engine</span>
          </div>
        </div>

        {/* Navigation & Controls - Aligned Right */}
        <div className="navbar-right">
          {/* Desktop Navigation */}
          <nav className="desktop-nav">
            <button
              type="button"
              onClick={() => handleNavClick("como-funciona")}
              className="nav-item-btn"
            >
              <span>{dict.nav.howItWorks}</span>
            </button>

            <button
              type="button"
              onClick={() => handleNavClick("entregables")}
              className="nav-item-btn"
            >
              <span>{dict.nav.guarantee}</span>
            </button>

            <button
              type="button"
              onClick={() => handleNavClick("precios")}
              className="nav-item-btn"
            >
              <span>{dict.nav.pricing}</span>
            </button>
          </nav>

          {/* Action Buttons - Standardized 36px Height */}
          <div className="navbar-actions">
            <button
              type="button"
              onClick={() => dispatch(toggleLanguage())}
              className="lang-switcher-btn"
              title="Switch Language / Cambiar Idioma"
            >
              <span>{currentLanguage === "es_CO" ? "🇨🇴 ES" : "🇺🇸 EN"}</span>
            </button>

            <button
              type="button"
              onClick={() => handleNavClick("generador")}
              className="nav-cta-btn"
            >
              <span>{dict.nav.cta}</span>
            </button>

            {/* Mobile hamburger */}
            <button
              type="button"
              className="mobile-hamburger-btn"
              onClick={() => dispatch(setMobileNavOpen(!isMobileNavOpen))}
              aria-label="Toggle navigation"
            >
              {isMobileNavOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer */}
      {isMobileNavOpen && (
        <div className="mobile-drawer">
          <button onClick={() => handleNavClick("como-funciona")} className="mobile-nav-link">
            <Workflow className="w-4 h-4 text-sky-400" />
            <span>{dict.nav.howItWorks}</span>
          </button>
          <button onClick={() => handleNavClick("entregables")} className="mobile-nav-link">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>{dict.nav.guarantee}</span>
          </button>
          <button onClick={() => handleNavClick("precios")} className="mobile-nav-link">
            <Tag className="w-4 h-4 text-sky-400" />
            <span>{dict.nav.pricing}</span>
          </button>

          <button onClick={() => handleNavClick("generador")} className="mobile-drawer-cta">
            {dict.nav.cta}
          </button>
        </div>
      )}
    </header>
  );
};

export default Navbar;

import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "../../store";
import { toggleLanguage } from "../../store/slices/languageSlice";
import { setMobileNavOpen } from "../../store/slices/uiSlice";
import { Globe, Menu, X, Zap } from "lucide-react";

export const Navbar: React.FC = () => {
  const dispatch = useDispatch();
  const { currentLanguage, dict } = useSelector((state: RootState) => state.language);
  const { isMobileNavOpen } = useSelector((state: RootState) => state.ui);

  const scrollTo = (id: string) => {
    dispatch(setMobileNavOpen(false));
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <header className="navbar-container">
      <div className="navbar-content">
        <div className="navbar-brand" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
          <span className="brand-logo-badge">導人</span>
          <div className="brand-titles">
            <span className="brand-name">MICHITO</span>
            <span className="brand-sub">B2B Intent Engine</span>
          </div>
        </div>

        {/* Desktop Navigation */}
        <nav className="desktop-nav">
          <button onClick={() => scrollTo("senales")} className="nav-link">
            {dict.nav.signals}
          </button>
          <button onClick={() => scrollTo("como-funciona")} className="nav-link">
            {dict.nav.howItWorks}
          </button>
          <button onClick={() => scrollTo("verticales")} className="nav-link">
            {dict.nav.verticals}
          </button>
          <button onClick={() => scrollTo("entregables")} className="nav-link">
            {dict.nav.deliverables}
          </button>
          <button onClick={() => scrollTo("precios")} className="nav-link">
            {dict.nav.pricing}
          </button>
          <button onClick={() => scrollTo("generador")} className="nav-link">
            {dict.nav.generator}
          </button>
        </nav>

        {/* Action Controls */}
        <div className="navbar-actions">
          <button
            onClick={() => dispatch(toggleLanguage())}
            className="lang-switcher-btn"
            title="Switch Language"
          >
            <Globe className="w-4 h-4" />
            <span>{currentLanguage === "es_CO" ? "🇨🇴 ES" : "🇺🇸 EN"}</span>
          </button>

          <button onClick={() => scrollTo("generador")} className="nav-cta-btn">
            <Zap className="w-4 h-4 fill-current" />
            <span>{dict.nav.cta}</span>
          </button>

          {/* Mobile hamburger */}
          <button
            className="mobile-hamburger-btn"
            onClick={() => dispatch(setMobileNavOpen(!isMobileNavOpen))}
            aria-label="Toggle navigation"
          >
            {isMobileNavOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {isMobileNavOpen && (
        <div className="mobile-drawer">
          <button onClick={() => scrollTo("senales")} className="mobile-nav-link">
            {dict.nav.signals}
          </button>
          <button onClick={() => scrollTo("como-funciona")} className="mobile-nav-link">
            {dict.nav.howItWorks}
          </button>
          <button onClick={() => scrollTo("verticales")} className="mobile-nav-link">
            {dict.nav.verticals}
          </button>
          <button onClick={() => scrollTo("entregables")} className="mobile-nav-link">
            {dict.nav.deliverables}
          </button>
          <button onClick={() => scrollTo("precios")} className="mobile-nav-link">
            {dict.nav.pricing}
          </button>
          <button onClick={() => scrollTo("generador")} className="mobile-nav-link">
            {dict.nav.generator}
          </button>
          <button onClick={() => scrollTo("generador")} className="mobile-drawer-cta">
            {dict.nav.cta}
          </button>
        </div>
      )}
    </header>
  );
};


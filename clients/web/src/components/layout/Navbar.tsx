import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "../../store";
import { toggleLanguage } from "../../store/slices/languageSlice";
import { setMobileNavOpen } from "../../store/slices/uiSlice";
import {
  Menu,
  X,
  Search,
  Workflow,
  Building2,
  ShieldCheck,
  Tag,
} from "lucide-react";

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

  const handleTrackOrder = () => {
    dispatch(setMobileNavOpen(false));
    scrollTo("generador");
    setTimeout(() => {
      const btn = document.getElementById("open-order-lookup-btn");
      if (btn) btn.click();
      const input = document.getElementById("order-lookup-input");
      if (input) input.focus();
    }, 250);
  };

  return (
    <header className="navbar-container">
      <div className="navbar-content">
        {/* Brand Logo - Aligned Left */}
        <div className="navbar-brand" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
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
          {/* Desktop Navigation in Logical Top-to-Bottom Order */}
          <nav className="desktop-nav">
            <button
              type="button"
              onClick={() => scrollTo("como-funciona")}
              className="nav-item-btn"
            >
              <span>{dict.nav.howItWorks}</span>
            </button>

            <button
              type="button"
              onClick={() => scrollTo("verticales")}
              className="nav-item-btn"
            >
              <span>{dict.nav.verticals}</span>
            </button>

            <button
              type="button"
              onClick={() => scrollTo("entregables")}
              className="nav-item-btn"
            >
              <span>{dict.nav.guarantee}</span>
            </button>

            <button
              type="button"
              onClick={() => scrollTo("precios")}
              className="nav-item-btn"
            >
              <span>{dict.nav.pricing}</span>
            </button>

            <button
              type="button"
              onClick={handleTrackOrder}
              className="nav-item-btn nav-track-btn"
              title="Consultar estado de una orden por ID"
            >
              <Search className="w-3.5 h-3.5" />
              <span>{dict.nav.trackOrder}</span>
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
              onClick={() => scrollTo("generador")}
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
          <button onClick={() => scrollTo("como-funciona")} className="mobile-nav-link">
            <Workflow className="w-4 h-4 text-sky-400" />
            <span>{dict.nav.howItWorks}</span>
          </button>
          <button onClick={() => scrollTo("verticales")} className="mobile-nav-link">
            <Building2 className="w-4 h-4 text-sky-400" />
            <span>{dict.nav.verticals}</span>
          </button>
          <button onClick={() => scrollTo("entregables")} className="mobile-nav-link">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>{dict.nav.guarantee}</span>
          </button>
          <button onClick={() => scrollTo("precios")} className="mobile-nav-link">
            <Tag className="w-4 h-4 text-sky-400" />
            <span>{dict.nav.pricing}</span>
          </button>
          <button onClick={handleTrackOrder} className="mobile-nav-link text-sky-400 font-semibold">
            <Search className="w-4 h-4" />
            <span>{dict.nav.trackOrder}</span>
          </button>

          <button onClick={() => scrollTo("generador")} className="mobile-drawer-cta">
            {dict.nav.cta}
          </button>
        </div>
      )}
    </header>
  );
};

export default Navbar;

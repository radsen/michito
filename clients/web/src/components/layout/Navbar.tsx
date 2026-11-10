import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "../../store";
import { toggleLanguage } from "../../store/slices/languageSlice";
import { setMobileNavOpen } from "../../store/slices/uiSlice";
import { Menu, X, Search } from "lucide-react";

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
    scrollTo("generador");
    setTimeout(() => {
      const btn = document.getElementById("open-order-lookup-btn");
      if (btn) btn.click();
    }, 250);
  };

  return (
    <header className="navbar-container">
      <div className="navbar-content">
        {/* Brand Logo */}
        <div className="navbar-brand" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
          <div className="brand-logo-badge">
            <span className="brand-logo-letter">M</span>
          </div>
          <div className="brand-titles">
            <span className="brand-name">MICHITO</span>
            <span className="brand-sub">B2B Intent Engine</span>
          </div>
        </div>

        {/* Clean Streamlined Desktop Navigation */}
        <nav className="desktop-nav">
          <button onClick={() => scrollTo("como-funciona")} className="nav-link">
            {dict.nav.howItWorks}
          </button>
          <button onClick={() => scrollTo("precios")} className="nav-link">
            {dict.nav.pricing}
          </button>
          <button
            onClick={handleTrackOrder}
            className="nav-link nav-track-link"
            title="Consultar estado de una orden por ID de referencia"
          >
            <Search className="w-3.5 h-3.5" />
            <span>Rastrear Orden</span>
          </button>
        </nav>

        {/* Action Controls */}
        <div className="navbar-actions">
          <button
            onClick={() => dispatch(toggleLanguage())}
            className="lang-switcher-btn"
            title="Switch Language / Cambiar Idioma"
          >
            <span>{currentLanguage === "es_CO" ? "🇨🇴 ES" : "🇺🇸 EN"}</span>
          </button>

          <button onClick={() => scrollTo("generador")} className="nav-cta-btn">
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
          <button onClick={() => scrollTo("como-funciona")} className="mobile-nav-link">
            {dict.nav.howItWorks}
          </button>
          <button onClick={() => scrollTo("precios")} className="mobile-nav-link">
            {dict.nav.pricing}
          </button>
          <button onClick={handleTrackOrder} className="mobile-nav-link text-sky-400 font-semibold flex items-center gap-1.5">
            <Search className="w-4 h-4" />
            <span>Rastrear Orden</span>
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

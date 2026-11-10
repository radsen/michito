import React, { useState, useRef, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "../../store";
import { toggleLanguage } from "../../store/slices/languageSlice";
import { setMobileNavOpen } from "../../store/slices/uiSlice";
import { selectCampaign } from "../../store/slices/campaignSlice";
import {
  Menu,
  X,
  Search,
  ChevronDown,
  Workflow,
  Radio,
  ShieldCheck,
  Scale,
  Building2,
  Truck,
  Sparkles,
  ArrowRight,
} from "lucide-react";

export const Navbar: React.FC = () => {
  const dispatch = useDispatch();
  const { currentLanguage, dict } = useSelector((state: RootState) => state.language);
  const { isMobileNavOpen } = useSelector((state: RootState) => state.ui);

  const [activeDropdown, setActiveDropdown] = useState<"platform" | "sectors" | null>(null);
  const navRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (navRef.current && !navRef.current.contains(event.target as Node)) {
        setActiveDropdown(null);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setActiveDropdown(null);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  const toggleDropdown = (name: "platform" | "sectors") => {
    setActiveDropdown((prev) => (prev === name ? null : name));
  };

  const scrollTo = (id: string) => {
    setActiveDropdown(null);
    dispatch(setMobileNavOpen(false));
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  const handleSelectSector = (campaignId: string) => {
    dispatch(selectCampaign(campaignId));
    setActiveDropdown(null);
    dispatch(setMobileNavOpen(false));
    const el = document.getElementById("generador");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  const handleTrackOrder = () => {
    setActiveDropdown(null);
    dispatch(setMobileNavOpen(false));
    scrollTo("generador");
    setTimeout(() => {
      const btn = document.getElementById("open-order-lookup-btn");
      if (btn) btn.click();
    }, 250);
  };

  return (
    <header className="navbar-container" ref={navRef}>
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

        {/* Structured Desktop Navigation with Dropdowns */}
        <nav className="desktop-nav">
          {/* Plataforma Dropdown */}
          <div className="nav-dropdown-wrapper">
            <button
              type="button"
              onClick={() => toggleDropdown("platform")}
              className={`nav-item-btn ${activeDropdown === "platform" ? "active" : ""}`}
              aria-expanded={activeDropdown === "platform"}
            >
              <span>{dict.nav.platform}</span>
              <ChevronDown className={`w-3.5 h-3.5 chevron-icon ${activeDropdown === "platform" ? "rotate" : ""}`} />
            </button>

            {activeDropdown === "platform" && (
              <div className="nav-dropdown-menu" role="menu">
                <button
                  type="button"
                  onClick={() => scrollTo("como-funciona")}
                  className="dropdown-menu-item"
                  role="menuitem"
                >
                  <div className="dropdown-item-icon">
                    <Workflow className="w-4 h-4 text-sky-400" />
                  </div>
                  <div className="dropdown-item-text">
                    <span className="dropdown-item-title">{dict.nav.howItWorks}</span>
                    <span className="dropdown-item-desc">{dict.nav.howItWorksDesc}</span>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => scrollTo("senales")}
                  className="dropdown-menu-item"
                  role="menuitem"
                >
                  <div className="dropdown-item-icon">
                    <Radio className="w-4 h-4 text-sky-400" />
                  </div>
                  <div className="dropdown-item-text">
                    <span className="dropdown-item-title">{dict.nav.signals}</span>
                    <span className="dropdown-item-desc">{dict.nav.signalsDesc}</span>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => scrollTo("entregables")}
                  className="dropdown-menu-item"
                  role="menuitem"
                >
                  <div className="dropdown-item-icon">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="dropdown-item-text">
                    <span className="dropdown-item-title">{dict.nav.deliverables}</span>
                    <span className="dropdown-item-desc">{dict.nav.deliverablesDesc}</span>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => scrollTo("comparativa")}
                  className="dropdown-menu-item"
                  role="menuitem"
                >
                  <div className="dropdown-item-icon">
                    <Scale className="w-4 h-4 text-amber-400" />
                  </div>
                  <div className="dropdown-item-text">
                    <span className="dropdown-item-title">{dict.nav.comparison}</span>
                    <span className="dropdown-item-desc">{dict.nav.comparisonDesc}</span>
                  </div>
                </button>
              </div>
            )}
          </div>

          {/* Sectores Dropdown */}
          <div className="nav-dropdown-wrapper">
            <button
              type="button"
              onClick={() => toggleDropdown("sectors")}
              className={`nav-item-btn ${activeDropdown === "sectors" ? "active" : ""}`}
              aria-expanded={activeDropdown === "sectors"}
            >
              <span>{dict.nav.sectors}</span>
              <ChevronDown className={`w-3.5 h-3.5 chevron-icon ${activeDropdown === "sectors" ? "rotate" : ""}`} />
            </button>

            {activeDropdown === "sectors" && (
              <div className="nav-dropdown-menu" role="menu">
                <button
                  type="button"
                  onClick={() => handleSelectSector("tinkko_enterprise_offices")}
                  className="dropdown-menu-item"
                  role="menuitem"
                >
                  <div className="dropdown-item-icon">
                    <Building2 className="w-4 h-4 text-sky-400" />
                  </div>
                  <div className="dropdown-item-text">
                    <div className="flex items-center gap-1.5">
                      <span className="dropdown-item-title">{dict.nav.sectorOffices}</span>
                      <span className="text-xs">🇨🇴</span>
                    </div>
                    <span className="dropdown-item-desc">{dict.nav.sectorOfficesDesc}</span>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => handleSelectSector("industrial_packaging_b2b")}
                  className="dropdown-menu-item"
                  role="menuitem"
                >
                  <div className="dropdown-item-icon">
                    <Truck className="w-4 h-4 text-sky-400" />
                  </div>
                  <div className="dropdown-item-text">
                    <div className="flex items-center gap-1.5">
                      <span className="dropdown-item-title">{dict.nav.sectorLogistics}</span>
                      <span className="text-xs">🇨🇴</span>
                    </div>
                    <span className="dropdown-item-desc">{dict.nav.sectorLogisticsDesc}</span>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => handleSelectSector("facility_services_b2b")}
                  className="dropdown-menu-item"
                  role="menuitem"
                >
                  <div className="dropdown-item-icon">
                    <Sparkles className="w-4 h-4 text-sky-400" />
                  </div>
                  <div className="dropdown-item-text">
                    <div className="flex items-center gap-1.5">
                      <span className="dropdown-item-title">{dict.nav.sectorFacilities}</span>
                      <span className="text-xs">🇩🇴</span>
                    </div>
                    <span className="dropdown-item-desc">{dict.nav.sectorFacilitiesDesc}</span>
                  </div>
                </button>

                <div className="dropdown-menu-divider" />

                <button
                  type="button"
                  onClick={() => scrollTo("verticales")}
                  className="dropdown-menu-item dropdown-footer-link"
                  role="menuitem"
                >
                  <span className="dropdown-item-title text-sky-400 flex items-center justify-between w-full">
                    <span>{dict.nav.verticalsDesc}</span>
                    <ArrowRight className="w-3.5 h-3.5 ml-2" />
                  </span>
                </button>
              </div>
            )}
          </div>

          {/* Direct Link: Precios */}
          <button
            type="button"
            onClick={() => scrollTo("precios")}
            className="nav-item-btn"
          >
            <span>{dict.nav.pricing}</span>
          </button>

          {/* Direct Link: Rastrear Orden */}
          <button
            type="button"
            onClick={handleTrackOrder}
            className="nav-item-btn nav-track-btn"
            title="Consultar estado de una orden por ID de referencia"
          >
            <Search className="w-3.5 h-3.5" />
            <span>{dict.nav.trackOrder}</span>
          </button>
        </nav>

        {/* Action Controls - Perfectly aligned 36px height buttons */}
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

      {/* Mobile Drawer */}
      {isMobileNavOpen && (
        <div className="mobile-drawer">
          <div className="mobile-drawer-section">
            <span className="mobile-drawer-header">{dict.nav.platform}</span>
            <button onClick={() => scrollTo("como-funciona")} className="mobile-nav-link">
              <Workflow className="w-4 h-4 text-sky-400" />
              <span>{dict.nav.howItWorks}</span>
            </button>
            <button onClick={() => scrollTo("senales")} className="mobile-nav-link">
              <Radio className="w-4 h-4 text-sky-400" />
              <span>{dict.nav.signals}</span>
            </button>
            <button onClick={() => scrollTo("entregables")} className="mobile-nav-link">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>{dict.nav.deliverables}</span>
            </button>
            <button onClick={() => scrollTo("comparativa")} className="mobile-nav-link">
              <Scale className="w-4 h-4 text-amber-400" />
              <span>{dict.nav.comparison}</span>
            </button>
          </div>

          <div className="mobile-drawer-section">
            <span className="mobile-drawer-header">{dict.nav.sectors}</span>
            <button onClick={() => handleSelectSector("tinkko_enterprise_offices")} className="mobile-nav-link">
              <Building2 className="w-4 h-4 text-sky-400" />
              <span>{dict.nav.sectorOffices} 🇨🇴</span>
            </button>
            <button onClick={() => handleSelectSector("industrial_packaging_b2b")} className="mobile-nav-link">
              <Truck className="w-4 h-4 text-sky-400" />
              <span>{dict.nav.sectorLogistics} 🇨🇴</span>
            </button>
            <button onClick={() => handleSelectSector("facility_services_b2b")} className="mobile-nav-link">
              <Sparkles className="w-4 h-4 text-sky-400" />
              <span>{dict.nav.sectorFacilities} 🇩🇴</span>
            </button>
            <button onClick={() => scrollTo("verticales")} className="mobile-nav-link text-sky-400">
              <ArrowRight className="w-4 h-4" />
              <span>{dict.nav.verticalsDesc}</span>
            </button>
          </div>

          <div className="mobile-drawer-section">
            <button onClick={() => scrollTo("precios")} className="mobile-nav-link font-semibold">
              <span>{dict.nav.pricing}</span>
            </button>
            <button onClick={handleTrackOrder} className="mobile-nav-link text-sky-400 font-semibold">
              <Search className="w-4 h-4" />
              <span>{dict.nav.trackOrder}</span>
            </button>
          </div>

          <button onClick={() => scrollTo("generador")} className="mobile-drawer-cta">
            {dict.nav.cta}
          </button>
        </div>
      )}
    </header>
  );
};

export default Navbar;

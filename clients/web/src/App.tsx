import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "./store";
import { setPartner } from "./store/slices/partnerSlice";
import { setPartnerDiscountRate } from "./store/slices/pricingSlice";
import { selectCampaign } from "./store/slices/campaignSlice";
import { useLazyGetPartnerQuery } from "./store/api/michitoApi";
import { Navbar } from "./components/layout/Navbar";
import { Hero } from "./components/landing/Hero";
import { ComparisonTable } from "./components/landing/ComparisonTable";
import { HowItWorks } from "./components/landing/HowItWorks";
import { DeliverablesStandards } from "./components/landing/DeliverablesStandards";
import { PricingMatrix } from "./components/pricing/PricingMatrix";
import { OrderGenerator } from "./components/order/OrderGenerator";
import { TrackOrderPage } from "./components/tracker/TrackOrderPage";
import { TermsPage } from "./components/legal/TermsPage";
import { WompiCheckoutModal } from "./components/payment/WompiCheckoutModal";
import { Footer } from "./components/layout/Footer";
import { MobileStickyCta } from "./components/layout/MobileStickyCta";

export const App: React.FC = () => {
  const dispatch = useDispatch();
  const partner = useSelector((state: RootState) => state.partner);
  const [triggerGetPartner] = useLazyGetPartnerQuery();

  const [currentPath, setCurrentPath] = useState<string>(() => {
    try {
      const p = window.location.pathname;
      if (p === "/rastrear" || p === "/terminos") return p;
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get("order_id")) return "/rastrear";
    } catch {
      // fallback
    }
    return "/";
  });

  useEffect(() => {
    const onPopState = () => {
      setCurrentPath(window.location.pathname || "/");
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigate = (path: string) => {
    if (path.startsWith("/#")) {
      const hash = path.substring(2);
      if (window.location.pathname !== "/") {
        window.history.pushState({}, "", "/");
        setCurrentPath("/");
      }
      setTimeout(() => {
        const el = document.getElementById(hash);
        if (el) {
          el.scrollIntoView({ behavior: "smooth" });
        }
      }, 60);
      return;
    }

    window.history.pushState({}, "", path);
    setCurrentPath(path);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  useEffect(() => {
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const refParam =
        urlParams.get("ref") ||
        urlParams.get("partner") ||
        urlParams.get("referral");
      if (refParam) {
        triggerGetPartner(refParam)
          .unwrap()
          .then((data) => {
            if (data?.partner && data.partner.partner_id !== "direct") {
              dispatch(
                setPartner({
                  partnerId: data.partner.partner_id,
                  name: data.partner.name,
                  commissionRate: data.partner.commission_rate,
                  discountRate: data.partner.discount_rate,
                  badgeText: data.partner.badge_text,
                  defaultCampaignId: data.partner.default_campaign_id,
                  description: data.partner.description,
                })
              );
              if (data.partner.discount_rate > 0) {
                dispatch(setPartnerDiscountRate(data.partner.discount_rate));
              }
              if (data.partner.default_campaign_id) {
                dispatch(selectCampaign(data.partner.default_campaign_id));
              }
            }
          })
          .catch((err) => {
            console.warn("Could not resolve affiliate partner:", err);
          });
      }
    } catch (e) {
      console.warn("Error parsing partner referral query:", e);
    }
  }, [dispatch, triggerGetPartner]);

  return (
    <div className="app-root">
      {partner.isAffiliate && (
        <div className="partner-banner" data-testid="partner-banner">
          <span className="partner-banner-badge">ALIANZA OFICIAL</span>
          <span className="partner-banner-text">{partner.badgeText || partner.name}</span>
          {partner.discountRate > 0 && (
            <span className="partner-banner-discount">
              • {(partner.discountRate * 100).toFixed(0)}% OFF APLICADO
            </span>
          )}
        </div>
      )}

      <Navbar onNavigate={navigate} currentPath={currentPath} />

      <main>
        {currentPath === "/rastrear" ? (
          <TrackOrderPage
            onBack={() => navigate("/")}
            initialOrderId={new URLSearchParams(window.location.search).get("order_id") || undefined}
          />
        ) : currentPath === "/terminos" ? (
          <TermsPage onBack={() => navigate("/")} />
        ) : (
          <>
            <Hero />
            <HowItWorks />
            <ComparisonTable />
            <DeliverablesStandards onNavigateTerms={() => navigate("/terminos")} />
            <PricingMatrix />
            <OrderGenerator />
          </>
        )}
      </main>

      <Footer onNavigate={navigate} />
      {currentPath === "/" && <MobileStickyCta />}
      <WompiCheckoutModal />
    </div>
  );
};

export default App;

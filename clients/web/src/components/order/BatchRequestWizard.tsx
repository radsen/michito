import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "../../store";
import {
  setBuyerInfo,
  startOrderSubmission,
  orderCreatedSuccess,
  orderFailed,
  resetOrder,
} from "../../store/slices/orderSlice";
import { setVolume, setCurrency } from "../../store/slices/pricingSlice";
import { selectCity } from "../../store/slices/campaignSlice";
import {
  useCreateOrderMutation,
  useProfileIntentMutation,
  useGetPricingCatalogQuery,
  useGetTrmRatesQuery,
} from "../../store/api/michitoApi";
import { SUPPORTED_COUNTRIES } from "../../config/countries";
import {
  Sparkles,
  Building2,
  Users,
  ShieldCheck,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  RotateCcw,
  AlertCircle,
  HelpCircle,
  Sliders,
  ChevronDown,
  ChevronUp,
  Mail,
  Phone,
  User,
  MapPin,
  Check,
  Loader2,
  ExternalLink,
  ShoppingBag,
  Briefcase,
} from "lucide-react";

interface BatchRequestWizardProps {
  onBack?: () => void;
  onNavigateTrack?: (orderId: string) => void;
}

export const BatchRequestWizard: React.FC<BatchRequestWizardProps> = ({
  onBack,
  onNavigateTrack,
}) => {
  const dispatch = useDispatch();
  const { currentLanguage, dict } = useSelector((state: RootState) => state.language);
  const w = dict.wizard;
  const isEn = currentLanguage === "en_US";
  const { currency, trmRates } = useSelector((state: RootState) => state.pricing);
  const partner = useSelector((state: RootState) => state.partner);
  const { buyerName: reduxBuyerName, buyerEmail: reduxBuyerEmail, buyerPhone: reduxBuyerPhone } = useSelector((state: RootState) => state.order);

  const [currentStep, setCurrentStep] = useState<number>(1);

  // Step 1: Goal & Intent
  const [directionality, setDirectionality] = useState<"vendor_to_clients" | "client_to_vendors">("vendor_to_clients");
  const [searchMode, setSearchMode] = useState<"natural" | "guided">("natural");
  const [naturalBrief, setNaturalBrief] = useState<string>("");
  const [step1Error, setStep1Error] = useState<string | null>(null);
  const [selectedCountry, setSelectedCountry] = useState<string>("CO");
  const [selectedCity, setSelectedCity] = useState<string>("Bogotá");
  const [selectedSectorName, setSelectedSectorName] = useState<string>(
    isEn ? "Technology, Software & Cloud" : "Tecnología, Software y Cloud"
  );

  // Step 2: Batch Size, Tier & Geo-scope
  const [selectedVolume, setSelectedVolume] = useState<number>(100);
  const [selectedTier, setSelectedTier] = useState<number>(2);
  const [geoScope, setGeoScope] = useState<string>("metro_area");
  const [showAdvancedFilters, setShowAdvancedFilters] = useState<boolean>(false);
  const [targetRolesText, setTargetRolesText] = useState<string>(w.step2.targetRolesDefault);
  const [negativeExclusionsText, setNegativeExclusionsText] = useState<string>("");

  // Step 3: Contact Info
  const [buyerName, setBuyerName] = useState<string>(reduxBuyerName || "");
  const [buyerEmail, setBuyerEmail] = useState<string>(reduxBuyerEmail || "");
  const [buyerPhone, setBuyerPhone] = useState<string>(reduxBuyerPhone || "");
  const [clientErrors, setClientErrors] = useState<{ name?: string; email?: string; phone?: string }>({});

  // Step 4: Submission & State Tracking
  const [submittedOrderId, setSubmittedOrderId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isRecovering, setIsRecovering] = useState<boolean>(false);

  // RTK Query
  const [createOrderMutation, { isLoading: isSubmitting }] = useCreateOrderMutation();
  const [profileIntentMutation, { isLoading: isProfiling }] = useProfileIntentMutation();
  const { data: pricingCatalog } = useGetPricingCatalogQuery(currency || "COP");

  // Auto-populate phone prefix based on country
  useEffect(() => {
    if (!buyerPhone) {
      if (selectedCountry === "CO") setBuyerPhone("+57 ");
      else if (selectedCountry === "DO") setBuyerPhone("+1809 ");
      else if (selectedCountry === "EC") setBuyerPhone("+593 ");
    }
  }, [selectedCountry]);

  // Pre-set cities per country
  const countryCities: Record<string, string[]> = {
    CO: ["Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena", "Bucaramanga", "Pereira", "Manizales"],
    DO: ["Santo Domingo", "Santiago de los Caballeros", "Punta Cana"],
    EC: ["Quito", "Guayaquil", "Cuenca", "Ambato", "Manta"],
  };

  const industriesList = [
    { name: isEn ? "Technology, Software & Cloud" : "Tecnología, Software y Cloud", ciiu: "6201" },
    { name: isEn ? "Textile Manufacturing, Apparel & Footwear" : "Manufactura Textil, Confección y Calzado", ciiu: "1410" },
    { name: isEn ? "Wholesale Food Distribution" : "Distribución Mayorista de Alimentos", ciiu: "4631" },
    { name: isEn ? "Construction & Civil Engineering" : "Construcción y Obras Civiles", ciiu: "4111" },
    { name: isEn ? "Healthcare, Medical Supplies & Clinics" : "Salud, Insumos Médicos y Clínicas", ciiu: "8610" },
    { name: isEn ? "Private Security & Surveillance" : "Seguridad Privada y Vigilancia", ciiu: "8010" },
    { name: isEn ? "Logistics, Freight & Transport" : "Logística, Carga y Transporte", ciiu: "4923" },
    { name: isEn ? "B2B Services & Consulting" : "Servicios B2B y Consultoría", ciiu: "7020" },
  ];

  // Quick suggestion pills for natural brief
  const suggestionPills = [
    { label: w.step1.suggestions.softwareLabel, text: w.step1.suggestions.softwareText, country: "CO", city: "Bogotá" },
    { label: w.step1.suggestions.textileLabel, text: w.step1.suggestions.textileText, country: "CO", city: "Medellín" },
    { label: w.step1.suggestions.foodLabel, text: w.step1.suggestions.foodText, country: "CO", city: "Cali" },
    { label: w.step1.suggestions.constructionLabel, text: w.step1.suggestions.constructionText, country: "DO", city: "Santo Domingo" },
    { label: w.step1.suggestions.securityLabel, text: w.step1.suggestions.securityText, country: "EC", city: "Guayaquil" },
  ];

  // Price calculations based on pricing catalog or baseline fallbacks
  const getUnitRateCop = (tier: number) => {
    if (tier === 1) return 1500;
    if (tier === 2) return 6200;
    return 15000;
  };

  const getDiscountPercent = (volume: number) => {
    if (volume >= 1000) return 32;
    if (volume >= 500) return 25;
    if (volume >= 250) return 18;
    if (volume >= 100) return 10;
    if (volume >= 50) return 5;
    return 0;
  };

  const discountPct = getDiscountPercent(selectedVolume);
  const baseRateCop = getUnitRateCop(selectedTier);
  const discountedRateCop = Math.round(baseRateCop * (1 - discountPct / 100));
  const estimatedSubtotalCop = discountedRateCop * selectedVolume;

  // Validation
  const validateContactInfo = (): boolean => {
    const errors: { name?: string; email?: string; phone?: string } = {};
    if (!buyerName.trim() || buyerName.trim().length < 2) {
      errors.name = w.step3.errName;
    }
    const emailPattern = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;
    if (!buyerEmail.trim() || !emailPattern.test(buyerEmail.trim())) {
      errors.email = w.step3.errEmail;
    }
    const digits = buyerPhone.replace(/\D/g, "");
    if (!buyerPhone.trim() || digits.length < 7) {
      errors.phone = w.step3.errPhone;
    }
    setClientErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Step 1 Submission
  const handleProceedFromStep1 = () => {
    if (searchMode === "natural") {
      if (!naturalBrief.trim()) {
        setStep1Error(w.step1.errBrief);
        return;
      }
      setStep1Error(null);
      // Fast heuristic extraction
      const lower = naturalBrief.toLowerCase();
      if (lower.includes("dominicana") || lower.includes("santo domingo")) {
        setSelectedCountry("DO");
        setSelectedCity("Santo Domingo");
      } else if (lower.includes("ecuador") || lower.includes("quito") || lower.includes("guayaquil")) {
        setSelectedCountry("EC");
        setSelectedCity(lower.includes("guayaquil") ? "Guayaquil" : "Quito");
      } else if (lower.includes("medellin") || lower.includes("medellín")) {
        setSelectedCountry("CO");
        setSelectedCity("Medellín");
      } else if (lower.includes("cali")) {
        setSelectedCountry("CO");
        setSelectedCity("Cali");
      } else if (lower.includes("barranquilla")) {
        setSelectedCountry("CO");
        setSelectedCity("Barranquilla");
      } else if (lower.includes("bogota") || lower.includes("bogotá")) {
        setSelectedCountry("CO");
        setSelectedCity("Bogotá");
      }
    } else {
      setStep1Error(null);
    }
    dispatch(selectCity(selectedCity));
    setCurrentStep(2);
  };

  // Final Order Submission (Sub-50ms via BackgroundTasks)
  const handleSubmitOrder = async () => {
    if (!validateContactInfo()) return;
    setSubmitError(null);
    dispatch(setBuyerInfo({ name: buyerName.trim(), email: buyerEmail.trim().toLowerCase(), phone: buyerPhone.trim() }));
    dispatch(startOrderSubmission());

    const rolesList = targetRolesText
      .split(",")
      .map((r) => r.trim())
      .filter((r) => r.length > 0);

    const exclusionsList = negativeExclusionsText
      .split(",")
      .map((e) => e.trim())
      .filter((e) => e.length > 0);

    const payload = {
      client: {
        name: buyerName.trim(),
        email: buyerEmail.trim().toLowerCase(),
        phone: buyerPhone.trim(),
        channel: "web_portal",
        referral_partner: partner?.partnerId || "direct",
      },
      request: {
        campaign_id: "universal_prospecting",
        country: selectedCountry,
        city: selectedCity,
        limit: selectedVolume,
        tier: selectedTier,
        currency: selectedCountry === "EC" ? "USD" : selectedCountry === "DO" ? "DOP" : "COP",
        offer_description: searchMode === "natural" ? naturalBrief.trim() : `${selectedSectorName} en ${selectedCity}`,
        target_roles: rolesList.length > 0 ? rolesList : ["Gerente General", "Director Comercial"],
        target_ciiu_codes: [],
        keywords_include: searchMode === "natural" ? [naturalBrief.trim()] : [selectedSectorName],
        keywords_exclude: exclusionsList,
        directionality: directionality,
        rfq_specifications: directionality === "client_to_vendors" ? naturalBrief : undefined,
        geographic_scope: geoScope,
      },
    };

    try {
      const res = await createOrderMutation(payload).unwrap();
      if (res && res.status === "success") {
        setSubmittedOrderId(res.order_id);
        dispatch(
          orderCreatedSuccess({
            orderId: res.order_id,
            status: res.order_status,
            totalAmountInCents: res.amount_in_cents_cop || estimatedSubtotalCop * 100,
            totalLeadsTarget: selectedVolume,
          })
        );
        setCurrentStep(4);
      } else {
        const errorMsg = res?.message || "No se pudo registrar la solicitud. Por favor intenta nuevamente.";
        setSubmitError(errorMsg);
        dispatch(orderFailed(errorMsg));
      }
    } catch (err: any) {
      console.warn("Order submission network hiccup:", err);
      // Graceful error recovery: Do not show broken failure; provide clear recovery path
      const detail = err?.data?.detail || err?.message || "Hubo una pequeña demora en la respuesta del servidor.";
      setSubmitError(detail);
      setIsRecovering(true);
    }
  };

  const handleReset = () => {
    dispatch(resetOrder());
    setSubmittedOrderId(null);
    setSubmitError(null);
    setCurrentStep(1);
  };

  return (
    <div className="wizard-container" style={{ maxWidth: 860, margin: "0 auto", padding: "24px 16px" }}>
      {/* Step Header Indicator */}
      <div className="wizard-progress-bar" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32, position: "relative" }}>
        {[
          { num: 1, label: w.steps.step1 },
          { num: 2, label: w.steps.step2 },
          { num: 3, label: w.steps.step3 },
        ].map((s) => (
          <div
            key={s.num}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              opacity: currentStep === s.num ? 1 : currentStep > s.num ? 0.9 : 0.45,
              fontWeight: currentStep === s.num ? 600 : 400,
              color: currentStep === s.num ? "#38bdf8" : currentStep > s.num ? "#10b981" : "#94a3b8",
            }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                background: currentStep > s.num ? "#10b981" : currentStep === s.num ? "#0284c7" : "#1e293b",
                color: "#ffffff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              {currentStep > s.num ? <Check style={{ width: 14, height: 14 }} /> : s.num}
            </div>
            <span style={{ fontSize: "0.875rem" }}>{s.label}</span>
          </div>
        ))}
      </div>

      {/* STEP 1: OBJECTIVE & BRIEF */}
      {currentStep === 1 && (
        <div className="wizard-card" style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 16, padding: "32px 24px" }}>
          <div style={{ marginBottom: 24 }}>
            <span style={{ fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: 1, color: "#38bdf8", fontWeight: 700 }}>
              {w.step1.kicker}
            </span>
            <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f8fafc", marginTop: 4, marginBottom: 8 }}>
              {w.step1.title}
            </h2>
            <p style={{ color: "#94a3b8", fontSize: "0.9rem" }}>
              {w.step1.subtitle}
            </p>
          </div>

          {/* Goal Toggle (Quiero Vender vs Quiero Comprar) */}
          <div style={{ marginBottom: 24 }}>
            <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#cbd5e1", marginBottom: 8 }}>
              {w.step1.objectiveLabel}
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <button
                type="button"
                onClick={() => setDirectionality("vendor_to_clients")}
                style={{
                  padding: "14px 16px",
                  borderRadius: 12,
                  border: directionality === "vendor_to_clients" ? "2px solid #0284c7" : "1px solid #334155",
                  background: directionality === "vendor_to_clients" ? "rgba(2, 132, 199, 0.15)" : "#1e293b",
                  color: "#f8fafc",
                  textAlign: "left",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                }}
              >
                <Briefcase style={{ width: 22, height: 22, color: "#38bdf8", flexShrink: 0 }} />
                <div>
                  <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>{w.step1.vendorTitle}</div>
                  <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>{w.step1.vendorDesc}</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setDirectionality("client_to_vendors")}
                style={{
                  padding: "14px 16px",
                  borderRadius: 12,
                  border: directionality === "client_to_vendors" ? "2px solid #10b981" : "1px solid #334155",
                  background: directionality === "client_to_vendors" ? "rgba(16, 185, 129, 0.15)" : "#1e293b",
                  color: "#f8fafc",
                  textAlign: "left",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                }}
              >
                <ShoppingBag style={{ width: 22, height: 22, color: "#34d399", flexShrink: 0 }} />
                <div>
                  <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>{w.step1.buyerTitle}</div>
                  <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>{w.step1.buyerDesc}</div>
                </div>
              </button>
            </div>
          </div>

          {/* Natural Search Mode */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <label style={{ fontSize: "0.85rem", fontWeight: 600, color: "#cbd5e1" }}>
                {w.step1.briefLabel}
              </label>
              <button
                type="button"
                onClick={() => setSearchMode(searchMode === "natural" ? "guided" : "natural")}
                style={{ background: "none", border: "none", color: "#38bdf8", fontSize: "0.78rem", cursor: "pointer", textDecoration: "underline" }}
              >
                {searchMode === "natural" ? w.step1.switchToGuided : w.step1.switchToNatural}
              </button>
            </div>

            {searchMode === "natural" ? (
              <>
                <textarea
                  rows={3}
                  value={naturalBrief}
                  onChange={(e) => {
                    setNaturalBrief(e.target.value);
                    if (step1Error) setStep1Error(null);
                  }}
                  placeholder={w.step1.briefPlaceholder}
                  style={{
                    width: "100%",
                    padding: "12px 16px",
                    borderRadius: 12,
                    background: "#020617",
                    border: step1Error ? "1px solid #f43f5e" : "1px solid #334155",
                    color: "#f8fafc",
                    fontSize: "0.95rem",
                    resize: "vertical",
                  }}
                />
                {step1Error && (
                  <span style={{ fontSize: "0.75rem", color: "#f43f5e", marginTop: 4, display: "block" }}>
                    {step1Error}
                  </span>
                )}

                {/* Quick suggestions */}
                <div style={{ marginTop: 12 }}>
                  <span style={{ fontSize: "0.75rem", color: "#64748b", display: "block", marginBottom: 6 }}>
                    {w.step1.popularExamples}
                  </span>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {suggestionPills.map((p, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => {
                          setNaturalBrief(p.text);
                          setSelectedCountry(p.country);
                          setSelectedCity(p.city);
                          if (step1Error) setStep1Error(null);
                        }}
                        style={{
                          background: "#1e293b",
                          border: "1px solid #334155",
                          borderRadius: 20,
                          padding: "4px 12px",
                          color: "#cbd5e1",
                          fontSize: "0.75rem",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                      >
                        {p.label}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              /* Guided Dropdowns */
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
                <div>
                  <label style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: 4 }}>{w.step1.countryLabel}</label>
                  <select
                    value={selectedCountry}
                    onChange={(e) => {
                      const c = e.target.value;
                      setSelectedCountry(c);
                      setSelectedCity((countryCities[c] || [])[0] || "");
                    }}
                    style={{ width: "100%", padding: "10px", borderRadius: 8, background: "#020617", color: "#fff", border: "1px solid #334155" }}
                  >
                    {Object.values(SUPPORTED_COUNTRIES).filter((c) => countryCities[c.code]).map((c) => (
                      <option key={c.code} value={c.code}>{c.name} {c.flag}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: 4 }}>{w.step1.cityLabel}</label>
                  <select
                    value={selectedCity}
                    onChange={(e) => setSelectedCity(e.target.value)}
                    style={{ width: "100%", padding: "10px", borderRadius: 8, background: "#020617", color: "#fff", border: "1px solid #334155" }}
                  >
                    {(countryCities[selectedCountry] || []).map((ct) => (
                      <option key={ct} value={ct}>{ct}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: 4 }}>{w.step1.sectorLabel}</label>
                  <select
                    value={selectedSectorName}
                    onChange={(e) => setSelectedSectorName(e.target.value)}
                    style={{ width: "100%", padding: "10px", borderRadius: 8, background: "#020617", color: "#fff", border: "1px solid #334155" }}
                  >
                    {industriesList.map((ind) => (
                      <option key={ind.ciiu} value={ind.name}>{ind.name}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}
          </div>

          {/* Reassuring Radar Banner */}
          <div style={{ background: "rgba(56, 189, 248, 0.1)", border: "1px solid rgba(56, 189, 248, 0.25)", borderRadius: 12, padding: "12px 16px", marginBottom: 28, display: "flex", alignItems: "center", gap: 12 }}>
            <Sparkles style={{ width: 20, height: 20, color: "#38bdf8", flexShrink: 0 }} />
            <div style={{ fontSize: "0.825rem", color: "#e2e8f0" }}>
              <strong>{w.step1.auditBannerBold}</strong>{" "}
              {w.step1.auditBannerTemplate.replace(
                "{country}",
                selectedCountry === "DO"
                  ? w.step1.countryNames.DO
                  : selectedCountry === "EC"
                  ? w.step1.countryNames.EC
                  : w.step1.countryNames.CO
              )}
            </div>
          </div>

          {/* Navigation Buttons */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            {onBack ? (
              <button
                type="button"
                onClick={onBack}
                style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontSize: "0.875rem" }}
              >
                <ArrowLeft style={{ width: 16, height: 16 }} />
                <span>{w.step1.backToHome}</span>
              </button>
            ) : <div />}

            <button
              type="button"
              onClick={handleProceedFromStep1}
              style={{
                background: "linear-gradient(135deg, #0284c7 0%, #0369a1 100%)",
                border: "none",
                borderRadius: 12,
                padding: "12px 24px",
                color: "#ffffff",
                fontWeight: 600,
                fontSize: "0.95rem",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <span>{w.step1.continueBtn}</span>
              <ArrowRight style={{ width: 18, height: 18 }} />
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: VOLUME & TIER */}
      {currentStep === 2 && (
        <div className="wizard-card" style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 16, padding: "32px 24px" }}>
          <div style={{ marginBottom: 24 }}>
            <span style={{ fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: 1, color: "#38bdf8", fontWeight: 700 }}>
              {w.step2.kicker}
            </span>
            <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f8fafc", marginTop: 4, marginBottom: 8 }}>
              {w.step2.title}
            </h2>
            <p style={{ color: "#94a3b8", fontSize: "0.9rem" }}>
              {w.step2.subtitle}
            </p>
          </div>

          {/* Volume Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 12, marginBottom: 28 }}>
            {[
              { vol: 50, label: `50 ${w.step2.accounts}`, badge: w.step2.volumes.v50.badge, sub: w.step2.volumes.v50.sub },
              { vol: 100, label: `100 ${w.step2.accounts}`, badge: w.step2.volumes.v100.badge, sub: w.step2.volumes.v100.sub },
              { vol: 250, label: `250 ${w.step2.accounts}`, badge: w.step2.volumes.v250.badge, sub: w.step2.volumes.v250.sub },
              { vol: 500, label: `500 ${w.step2.accounts}`, badge: w.step2.volumes.v500.badge, sub: w.step2.volumes.v500.sub },
              { vol: 1000, label: `${isEn ? "1,000" : "1.000"} ${w.step2.accounts}`, badge: w.step2.volumes.v1000.badge, sub: w.step2.volumes.v1000.sub },
            ].map((v) => (
              <button
                key={v.vol}
                type="button"
                onClick={() => setSelectedVolume(v.vol)}
                style={{
                  padding: "16px 12px",
                  borderRadius: 12,
                  border: selectedVolume === v.vol ? "2px solid #38bdf8" : "1px solid #334155",
                  background: selectedVolume === v.vol ? "rgba(56, 189, 248, 0.15)" : "#1e293b",
                  color: "#f8fafc",
                  cursor: "pointer",
                  textAlign: "center",
                }}
              >
                <div style={{ fontWeight: 700, fontSize: "1.1rem", color: selectedVolume === v.vol ? "#38bdf8" : "#f8fafc" }}>
                  {v.label}
                </div>
                <div style={{ fontSize: "0.7rem", color: "#10b981", fontWeight: 700, marginTop: 4 }}>
                  {v.badge}
                </div>
                <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: 4 }}>
                  {v.sub}
                </div>
              </button>
            ))}
          </div>

          {/* Tier Selection */}
          <div style={{ marginBottom: 28 }}>
            <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#cbd5e1", marginBottom: 12 }}>
              {w.step2.tierLabel}
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
              {[
                { tier: 1, title: w.step2.tiers.t1.title, desc: w.step2.tiers.t1.desc, rate: w.step2.tiers.t1.rate },
                { tier: 2, title: w.step2.tiers.t2.title, desc: w.step2.tiers.t2.desc, rate: w.step2.tiers.t2.rate },
                { tier: 3, title: w.step2.tiers.t3.title, desc: w.step2.tiers.t3.desc, rate: w.step2.tiers.t3.rate },
              ].map((t) => (
                <button
                  key={t.tier}
                  type="button"
                  onClick={() => setSelectedTier(t.tier)}
                  style={{
                    padding: "16px",
                    borderRadius: 12,
                    border: selectedTier === t.tier ? "2px solid #0284c7" : "1px solid #334155",
                    background: selectedTier === t.tier ? "rgba(2, 132, 199, 0.15)" : "#1e293b",
                    color: "#f8fafc",
                    textAlign: "left",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: "0.95rem", color: selectedTier === t.tier ? "#38bdf8" : "#f8fafc" }}>
                    {t.title}
                  </div>
                  <div style={{ fontSize: "0.78rem", color: "#94a3b8", marginTop: 6, lineHeight: 1.4 }}>
                    {t.desc}
                  </div>
                  <div style={{ fontSize: "0.825rem", color: "#38bdf8", fontWeight: 700, marginTop: 10 }}>
                    {w.step2.startingAt} {t.rate} {w.step2.perAccount}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Collapsible Advanced Filters */}
          <div style={{ marginBottom: 28, background: "#020617", borderRadius: 12, border: "1px solid #334155" }}>
            <button
              type="button"
              onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
              style={{
                width: "100%",
                padding: "14px 16px",
                background: "none",
                border: "none",
                color: "#cbd5e1",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                cursor: "pointer",
                fontSize: "0.875rem",
                fontWeight: 600,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Sliders style={{ width: 16, height: 16, color: "#38bdf8" }} />
                <span>{w.step2.advancedFiltersToggle}</span>
              </div>
              {showAdvancedFilters ? <ChevronUp style={{ width: 18, height: 18 }} /> : <ChevronDown style={{ width: 18, height: 18 }} />}
            </button>

            {showAdvancedFilters && (
              <div style={{ padding: "0 16px 16px 16px", borderTop: "1px solid #1e293b", marginTop: 8 }}>
                <div style={{ marginBottom: 12, paddingTop: 12 }}>
                  <label style={{ fontSize: "0.78rem", color: "#94a3b8", display: "block", marginBottom: 4 }}>
                    {w.step2.targetRolesLabel}
                  </label>
                  <input
                    type="text"
                    value={targetRolesText}
                    onChange={(e) => setTargetRolesText(e.target.value)}
                    style={{ width: "100%", padding: "8px 12px", borderRadius: 8, background: "#0f172a", border: "1px solid #334155", color: "#fff", fontSize: "0.85rem" }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: "0.78rem", color: "#94a3b8", display: "block", marginBottom: 4 }}>
                    {w.step2.exclusionsLabel}
                  </label>
                  <input
                    type="text"
                    value={negativeExclusionsText}
                    onChange={(e) => setNegativeExclusionsText(e.target.value)}
                    placeholder={w.step2.exclusionsPlaceholder}
                    style={{ width: "100%", padding: "8px 12px", borderRadius: 8, background: "#0f172a", border: "1px solid #334155", color: "#fff", fontSize: "0.85rem" }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Pricing Recap Pill */}
          <div style={{ background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.25)", borderRadius: 12, padding: "14px 18px", marginBottom: 28, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>{w.step2.recapTitle}</div>
              <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#10b981" }}>
                ${estimatedSubtotalCop.toLocaleString(isEn ? "en-US" : "es-CO")} COP{" "}
                <span style={{ fontSize: "0.8rem", fontWeight: 400, color: "#94a3b8" }}>
                  ({discountPct}% {w.step2.discountApplied})
                </span>
              </div>
            </div>
            <div style={{ textAlign: "right", fontSize: "0.75rem", color: "#64748b" }}>
              {w.step2.recapNote}
            </div>
          </div>

          {/* Navigation Buttons */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <button
              type="button"
              onClick={() => setCurrentStep(1)}
              style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontSize: "0.875rem" }}
            >
              <ArrowLeft style={{ width: 16, height: 16 }} />
              <span>{w.step2.back}</span>
            </button>

            <button
              type="button"
              onClick={() => setCurrentStep(3)}
              style={{
                background: "linear-gradient(135deg, #0284c7 0%, #0369a1 100%)",
                border: "none",
                borderRadius: 12,
                padding: "12px 24px",
                color: "#ffffff",
                fontWeight: 600,
                fontSize: "0.95rem",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <span>{w.step2.continueBtn}</span>
              <ArrowRight style={{ width: 18, height: 18 }} />
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: CONTACT INFORMATION */}
      {currentStep === 3 && (
        <div className="wizard-card" style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 16, padding: "32px 24px" }}>
          <div style={{ marginBottom: 24 }}>
            <span style={{ fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: 1, color: "#38bdf8", fontWeight: 700 }}>
              {w.step3.kicker}
            </span>
            <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f8fafc", marginTop: 4, marginBottom: 8 }}>
              {w.step3.title}
            </h2>
            <p style={{ color: "#94a3b8", fontSize: "0.9rem" }}>
              {w.step3.subtitle}
            </p>
          </div>

          {submitError && (
            <div style={{ background: "rgba(225, 29, 72, 0.15)", border: "1px solid rgba(225, 29, 72, 0.4)", borderRadius: 12, padding: "14px 16px", marginBottom: 20, display: "flex", alignItems: "center", gap: 12 }}>
              <AlertCircle style={{ width: 20, height: 20, color: "#f43f5e", flexShrink: 0 }} />
              <div style={{ fontSize: "0.85rem", color: "#fda4af" }}>
                {submitError}
              </div>
            </div>
          )}

          {/* Contact Fields */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16, marginBottom: 28 }}>
            <div>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#cbd5e1", marginBottom: 6 }}>
                {w.step3.nameLabel}
              </label>
              <div style={{ position: "relative" }}>
                <input
                  type="text"
                  value={buyerName}
                  onChange={(e) => {
                    setBuyerName(e.target.value);
                    if (clientErrors.name) setClientErrors({ ...clientErrors, name: undefined });
                  }}
                  placeholder={w.step3.namePlaceholder}
                  autoComplete="name"
                  style={{
                    width: "100%",
                    padding: "12px 16px 12px 40px",
                    borderRadius: 12,
                    background: "#020617",
                    border: clientErrors.name ? "1px solid #f43f5e" : "1px solid #334155",
                    color: "#f8fafc",
                    fontSize: "0.95rem",
                  }}
                />
                <User style={{ position: "absolute", left: 14, top: 14, width: 16, height: 16, color: "#64748b" }} />
              </div>
              {clientErrors.name && (
                <span style={{ fontSize: "0.75rem", color: "#f43f5e", marginTop: 4, display: "block" }}>{clientErrors.name}</span>
              )}
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#cbd5e1", marginBottom: 6 }}>
                {w.step3.emailLabel}
              </label>
              <div style={{ position: "relative" }}>
                <input
                  type="email"
                  value={buyerEmail}
                  onChange={(e) => {
                    setBuyerEmail(e.target.value);
                    if (clientErrors.email) setClientErrors({ ...clientErrors, email: undefined });
                  }}
                  placeholder={w.step3.emailPlaceholder}
                  autoComplete="email"
                  style={{
                    width: "100%",
                    padding: "12px 16px 12px 40px",
                    borderRadius: 12,
                    background: "#020617",
                    border: clientErrors.email ? "1px solid #f43f5e" : "1px solid #334155",
                    color: "#f8fafc",
                    fontSize: "0.95rem",
                  }}
                />
                <Mail style={{ position: "absolute", left: 14, top: 14, width: 16, height: 16, color: "#64748b" }} />
              </div>
              {clientErrors.email && (
                <span style={{ fontSize: "0.75rem", color: "#f43f5e", marginTop: 4, display: "block" }}>{clientErrors.email}</span>
              )}
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#cbd5e1", marginBottom: 6 }}>
                {w.step3.phoneLabel}
              </label>
              <div style={{ position: "relative" }}>
                <input
                  type="tel"
                  value={buyerPhone}
                  onChange={(e) => {
                    setBuyerPhone(e.target.value);
                    if (clientErrors.phone) setClientErrors({ ...clientErrors, phone: undefined });
                  }}
                  placeholder={w.step3.phonePlaceholder}
                  autoComplete="tel"
                  style={{
                    width: "100%",
                    padding: "12px 16px 12px 40px",
                    borderRadius: 12,
                    background: "#020617",
                    border: clientErrors.phone ? "1px solid #f43f5e" : "1px solid #334155",
                    color: "#f8fafc",
                    fontSize: "0.95rem",
                  }}
                />
                <Phone style={{ position: "absolute", left: 14, top: 14, width: 16, height: 16, color: "#64748b" }} />
              </div>
              {clientErrors.phone && (
                <span style={{ fontSize: "0.75rem", color: "#f43f5e", marginTop: 4, display: "block" }}>{clientErrors.phone}</span>
              )}
            </div>
          </div>

          {/* Navigation Buttons */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <button
              type="button"
              onClick={() => setCurrentStep(2)}
              disabled={isSubmitting}
              style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontSize: "0.875rem" }}
            >
              <ArrowLeft style={{ width: 16, height: 16 }} />
              <span>{w.step3.back}</span>
            </button>

            <button
              type="button"
              onClick={handleSubmitOrder}
              disabled={isSubmitting}
              style={{
                background: isSubmitting ? "#334155" : "linear-gradient(135deg, #10b981 0%, #059669 100%)",
                border: "none",
                borderRadius: 12,
                padding: "14px 28px",
                color: "#ffffff",
                fontWeight: 700,
                fontSize: "1rem",
                cursor: isSubmitting ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                gap: 10,
                boxShadow: "0 4px 14px rgba(16, 185, 129, 0.35)",
              }}
            >
              {isSubmitting ? (
                <>
                  <Loader2 style={{ width: 18, height: 18, animation: "spin 1s linear infinite" }} />
                  <span>{w.step3.submitting}</span>
                </>
              ) : (
                <>
                  <ShieldCheck style={{ width: 20, height: 20 }} />
                  <span>{w.step3.submitBtn}</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: SUCCESS & ASYNC HANDOFF CARD */}
      {currentStep === 4 && (
        <div className="wizard-card" style={{ background: "#0f172a", border: "1px solid #10b981", borderRadius: 16, padding: "40px 28px", textAlign: "center" }}>
          <div style={{ width: 64, height: 64, borderRadius: "50%", background: "rgba(16, 185, 129, 0.15)", border: "2px solid #10b981", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px auto" }}>
            <CheckCircle2 style={{ width: 36, height: 36, color: "#10b981" }} />
          </div>

          <span style={{ fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: 1, color: "#10b981", fontWeight: 700 }}>
            {w.step4.badge}
          </span>
          <h2 style={{ fontSize: "1.75rem", fontWeight: 700, color: "#f8fafc", marginTop: 6, marginBottom: 12 }}>
            {w.step4.title}
          </h2>

          <div style={{ display: "inline-block", background: "#1e293b", padding: "6px 14px", borderRadius: 20, fontSize: "0.85rem", color: "#38bdf8", fontWeight: 600, marginBottom: 20 }}>
            {w.step4.orderPrefix}{submittedOrderId || w.step4.orderFallback}
          </div>

          <p style={{ color: "#cbd5e1", fontSize: "0.95rem", lineHeight: 1.6, maxWidth: 560, margin: "0 auto 28px auto" }}>
            {w.step4.descP1} <strong>{selectedCity}</strong> {w.step4.descP2}
            <br /><br />
            <strong>{w.step4.descP3}</strong> {w.step4.descP4} <strong>{buyerEmail}</strong> {w.step4.descP5}
          </p>

          {/* Action Buttons */}
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 12 }}>
            {submittedOrderId && onNavigateTrack && (
              <button
                type="button"
                onClick={() => onNavigateTrack(submittedOrderId)}
                style={{
                  background: "linear-gradient(135deg, #0284c7 0%, #0369a1 100%)",
                  border: "none",
                  borderRadius: 12,
                  padding: "12px 22px",
                  color: "#ffffff",
                  fontWeight: 600,
                  fontSize: "0.9rem",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <span>{w.step4.viewTracking}</span>
                <ExternalLink style={{ width: 16, height: 16 }} />
              </button>
            )}

            <button
              type="button"
              onClick={handleReset}
              style={{
                background: "#1e293b",
                border: "1px solid #334155",
                borderRadius: 12,
                padding: "12px 22px",
                color: "#e2e8f0",
                fontWeight: 600,
                fontSize: "0.9rem",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <RotateCcw style={{ width: 16, height: 16 }} />
              <span>{w.step4.orderAnother}</span>
            </button>

            {onBack && (
              <button
                type="button"
                onClick={onBack}
                style={{
                  background: "none",
                  border: "1px solid #334155",
                  borderRadius: 12,
                  padding: "12px 22px",
                  color: "#94a3b8",
                  fontSize: "0.9rem",
                  cursor: "pointer",
                }}
              >
                {w.step4.backHome}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

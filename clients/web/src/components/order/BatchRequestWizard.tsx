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
  const { currency, trmRates } = useSelector((state: RootState) => state.pricing);
  const partner = useSelector((state: RootState) => state.partner);
  const { buyerName: reduxBuyerName, buyerEmail: reduxBuyerEmail, buyerPhone: reduxBuyerPhone } = useSelector((state: RootState) => state.order);

  const [currentStep, setCurrentStep] = useState<number>(1);

  // Step 1: Goal & Intent
  const [directionality, setDirectionality] = useState<"vendor_to_clients" | "client_to_vendors">("vendor_to_clients");
  const [searchMode, setSearchMode] = useState<"natural" | "guided">("natural");
  const [naturalBrief, setNaturalBrief] = useState<string>("Empresas de tecnología, desarrollo de software y servicios cloud en Bogotá");
  const [selectedCountry, setSelectedCountry] = useState<string>("CO");
  const [selectedCity, setSelectedCity] = useState<string>("Bogotá");
  const [selectedSectorName, setSelectedSectorName] = useState<string>("Tecnología, Software y Cloud");

  // Step 2: Batch Size, Tier & Geo-scope
  const [selectedVolume, setSelectedVolume] = useState<number>(100);
  const [selectedTier, setSelectedTier] = useState<number>(2);
  const [geoScope, setGeoScope] = useState<string>("metro_area");
  const [showAdvancedFilters, setShowAdvancedFilters] = useState<boolean>(false);
  const [targetRolesText, setTargetRolesText] = useState<string>("Gerente General, Director Comercial, Representante Legal");
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
    { name: "Tecnología, Software y Cloud", ciiu: "6201" },
    { name: "Manufactura Textil, Confección y Calzado", ciiu: "1410" },
    { name: "Distribución Mayorista de Alimentos", ciiu: "4631" },
    { name: "Construcción y Obras Civiles", ciiu: "4111" },
    { name: "Salud, Insumos Médicos y Clínicas", ciiu: "8610" },
    { name: "Seguridad Privada y Vigilancia", ciiu: "8010" },
    { name: "Logística, Carga y Transporte", ciiu: "4923" },
    { name: "Servicios B2B y Consultoría", ciiu: "7020" },
  ];

  // Quick suggestion pills for natural brief
  const suggestionPills = [
    { label: "Software en Bogotá 🇨🇴", text: "Empresas de tecnología, desarrollo de software y servicios cloud en Bogotá", country: "CO", city: "Bogotá" },
    { label: "Textil en Medellín 🇨🇴", text: "Empresas de manufactura textil, confección y calzado en Medellín", country: "CO", city: "Medellín" },
    { label: "Alimentos en Cali 🇨🇴", text: "Empresas distribuidoras de alimentos al por mayor e insumos para restaurantes en Cali", country: "CO", city: "Cali" },
    { label: "Construcción en Santo Domingo 🇩🇴", text: "Empresas constructoras y contratistas de obras civiles en Santo Domingo", country: "DO", city: "Santo Domingo" },
    { label: "Seguridad en Guayaquil 🇪🇨", text: "Empresas de seguridad privada y vigilancia física en Guayaquil", country: "EC", city: "Guayaquil" },
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
      errors.name = "Por favor ingresa tu nombre o el de tu empresa (mínimo 2 caracteres).";
    }
    const emailPattern = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;
    if (!buyerEmail.trim() || !emailPattern.test(buyerEmail.trim())) {
      errors.email = "Por favor ingresa un correo corporativo válido.";
    }
    const digits = buyerPhone.replace(/\D/g, "");
    if (!buyerPhone.trim() || digits.length < 7) {
      errors.phone = "Por favor ingresa un número de celular o WhatsApp válido (mínimo 7 dígitos).";
    }
    setClientErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Step 1 Submission
  const handleProceedFromStep1 = () => {
    if (searchMode === "natural" && naturalBrief.trim()) {
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
          { num: 1, label: "1. ¿Qué buscas?" },
          { num: 2, label: "2. Tamaño y Nivel" },
          { num: 3, label: "3. Datos de Notificación" },
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
              PASO 1 DE 3
            </span>
            <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f8fafc", marginTop: 4, marginBottom: 8 }}>
              ¿Qué tipo de empresas necesitas encontrar?
            </h2>
            <p style={{ color: "#94a3b8", fontSize: "0.9rem" }}>
              Michito auditará en tiempo real los registros mercantiles oficiales y validará buzones institucionales sin rebote.
            </p>
          </div>

          {/* Goal Toggle (Quiero Vender vs Quiero Comprar) */}
          <div style={{ marginBottom: 24 }}>
            <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#cbd5e1", marginBottom: 8 }}>
              ¿Cuál es tu objetivo principal?
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
                  <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>Quiero Conseguir Clientes</div>
                  <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Empresas compradoras y decisores C-Level</div>
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
                  <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>Quiero Conseguir Proveedores</div>
                  <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Fabricantes, talleres y contratistas (Reverse RFQ)</div>
                </div>
              </button>
            </div>
          </div>

          {/* Natural Search Mode */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <label style={{ fontSize: "0.85rem", fontWeight: 600, color: "#cbd5e1" }}>
                Describe qué empresas buscas (o usa los ejemplos):
              </label>
              <button
                type="button"
                onClick={() => setSearchMode(searchMode === "natural" ? "guided" : "natural")}
                style={{ background: "none", border: "none", color: "#38bdf8", fontSize: "0.78rem", cursor: "pointer", textDecoration: "underline" }}
              >
                {searchMode === "natural" ? "Prefiero elegir con menús desplegables" : "Prefiero escribir en lenguaje natural"}
              </button>
            </div>

            {searchMode === "natural" ? (
              <>
                <textarea
                  rows={3}
                  value={naturalBrief}
                  onChange={(e) => setNaturalBrief(e.target.value)}
                  placeholder="Ejemplo: Empresas de manufactura textil, confección y calzado en Medellín"
                  style={{
                    width: "100%",
                    padding: "12px 16px",
                    borderRadius: 12,
                    background: "#020617",
                    border: "1px solid #334155",
                    color: "#f8fafc",
                    fontSize: "0.95rem",
                    resize: "vertical",
                  }}
                />

                {/* Quick suggestions */}
                <div style={{ marginTop: 12 }}>
                  <span style={{ fontSize: "0.75rem", color: "#64748b", display: "block", marginBottom: 6 }}>
                    Ejemplos populares para probar en 1 clic:
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
                  <label style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: 4 }}>País</label>
                  <select
                    value={selectedCountry}
                    onChange={(e) => {
                      const c = e.target.value;
                      setSelectedCountry(c);
                      setSelectedCity(countryCities[c][0]);
                    }}
                    style={{ width: "100%", padding: "10px", borderRadius: 8, background: "#020617", color: "#fff", border: "1px solid #334155" }}
                  >
                    <option value="CO">Colombia 🇨🇴</option>
                    <option value="DO">República Dominicana 🇩🇴</option>
                    <option value="EC">Ecuador 🇪🇨</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: 4 }}>Ciudad</label>
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
                  <label style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block", marginBottom: 4 }}>Sector</label>
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
              <strong>Auditoría en Tiempo Real:</strong> Michito conectará con los registros oficiales de{" "}
              {selectedCountry === "DO" ? "República Dominicana 🇩🇴" : selectedCountry === "EC" ? "Ecuador 🇪🇨" : "Colombia 🇨🇴"}{" "}
              sin costo por adelantado ($0 anticipo).
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
                <span>Volver al Inicio</span>
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
              <span>Continuar a Tamaño del Lote</span>
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
              PASO 2 DE 3
            </span>
            <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f8fafc", marginTop: 4, marginBottom: 8 }}>
              ¿Cuántas cuentas verificadas necesitas?
            </h2>
            <p style={{ color: "#94a3b8", fontSize: "0.9rem" }}>
              Entre mayor sea el lote, mayor es el descuento por volumen. Solo pagas tras la auditoría sobre cuentas que pasen el 100% de los filtros.
            </p>
          </div>

          {/* Volume Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 12, marginBottom: 28 }}>
            {[
              { vol: 50, label: "50 cuentas", badge: "0% OFF", sub: "Prueba Inicial" },
              { vol: 100, label: "100 cuentas", badge: "10% OFF", sub: "⭐ Más Popular" },
              { vol: 250, label: "250 cuentas", badge: "18% OFF", sub: "Equipo Comercial" },
              { vol: 500, label: "500 cuentas", badge: "25% OFF", sub: "Cobertura Regional" },
              { vol: 1000, label: "1.000 cuentas", badge: "32% OFF", sub: "Lote Nacional" },
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
              Nivel de Inteligencia de los Contactos:
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
              {[
                { tier: 1, title: "Tier 1: Directorio Base", desc: "Mailbox verificado corporativo, Representante Legal estatutario y NIT/RUC.", rate: "$1.500 COP" },
                { tier: 2, title: "Tier 2: Decisor C-Level ⭐", desc: "Tomador de decisión verificado con celular directo, correo 0-rebotes y LinkedIn.", rate: "$6.200 COP" },
                { tier: 3, title: "Tier 3: Auditoría Financiera", desc: "Dossier con balances NIIF, cálculo de EBITDA, márgenes y scoring judicial.", rate: "$15.000 COP" },
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
                    Desde {t.rate} / cuenta
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
                <span>Filtros Avanzados (Opcional para Equipos Comerciales)</span>
              </div>
              {showAdvancedFilters ? <ChevronUp style={{ width: 18, height: 18 }} /> : <ChevronDown style={{ width: 18, height: 18 }} />}
            </button>

            {showAdvancedFilters && (
              <div style={{ padding: "0 16px 16px 16px", borderTop: "1px solid #1e293b", marginTop: 8 }}>
                <div style={{ marginBottom: 12, paddingTop: 12 }}>
                  <label style={{ fontSize: "0.78rem", color: "#94a3b8", display: "block", marginBottom: 4 }}>
                    Cargos directivos deseados (separados por coma):
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
                    Exclusiones de clientes actuales o competidores (NITs o dominios):
                  </label>
                  <input
                    type="text"
                    value={negativeExclusionsText}
                    onChange={(e) => setNegativeExclusionsText(e.target.value)}
                    placeholder="Ejemplo: 900123456, competidor.com"
                    style={{ width: "100%", padding: "8px 12px", borderRadius: 8, background: "#0f172a", border: "1px solid #334155", color: "#fff", fontSize: "0.85rem" }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Pricing Recap Pill */}
          <div style={{ background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.25)", borderRadius: 12, padding: "14px 18px", marginBottom: 28, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Inversión Estimada Post-Auditoría:</div>
              <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#10b981" }}>
                ${estimatedSubtotalCop.toLocaleString("es-CO")} COP{" "}
                <span style={{ fontSize: "0.8rem", fontWeight: 400, color: "#94a3b8" }}>
                  ({discountPct}% de descuento aplicado)
                </span>
              </div>
            </div>
            <div style={{ textAlign: "right", fontSize: "0.75rem", color: "#64748b" }}>
              $0 anticipo • Factura con IVA al aprobar
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
              <span>Atrás</span>
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
              <span>Continuar a Datos de Contacto</span>
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
              PASO 3 DE 3
            </span>
            <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f8fafc", marginTop: 4, marginBottom: 8 }}>
              ¿A dónde te notificamos cuando tu lote esté verificado?
            </h2>
            <p style={{ color: "#94a3b8", fontSize: "0.9rem" }}>
              Te enviaremos el reporte de auditoría y la cotización ajustada por correo y WhatsApp. No necesitas esperar en la web.
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
                Tu Nombre o Razón Social
              </label>
              <div style={{ position: "relative" }}>
                <input
                  type="text"
                  value={buyerName}
                  onChange={(e) => {
                    setBuyerName(e.target.value);
                    if (clientErrors.name) setClientErrors({ ...clientErrors, name: undefined });
                  }}
                  placeholder="Ejemplo: Andrés Solano / Inversiones Alfa"
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
                Correo Electrónico Corporativo (Para recibir el resumen y cotización)
              </label>
              <div style={{ position: "relative" }}>
                <input
                  type="email"
                  value={buyerEmail}
                  onChange={(e) => {
                    setBuyerEmail(e.target.value);
                    if (clientErrors.email) setClientErrors({ ...clientErrors, email: undefined });
                  }}
                  placeholder="andres@empresa.com"
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
                Celular o WhatsApp (Para notificarte cuando el lote esté listo)
              </label>
              <div style={{ position: "relative" }}>
                <input
                  type="tel"
                  value={buyerPhone}
                  onChange={(e) => {
                    setBuyerPhone(e.target.value);
                    if (clientErrors.phone) setClientErrors({ ...clientErrors, phone: undefined });
                  }}
                  placeholder="+57 300 123 4567"
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
              <span>Atrás</span>
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
                  <span>Registrando solicitud...</span>
                </>
              ) : (
                <>
                  <ShieldCheck style={{ width: 20, height: 20 }} />
                  <span>Solicitar Auditoría y Cotización ($0 Anticipo)</span>
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
            SOLICITUD RECIBIDA CON ÉXITO
          </span>
          <h2 style={{ fontSize: "1.75rem", fontWeight: 700, color: "#f8fafc", marginTop: 6, marginBottom: 12 }}>
            ¡Tu auditoría B2B está en marcha!
          </h2>

          <div style={{ display: "inline-block", background: "#1e293b", padding: "6px 14px", borderRadius: 20, fontSize: "0.85rem", color: "#38bdf8", fontWeight: 600, marginBottom: 20 }}>
            Orden #{submittedOrderId || "ord_en_proceso"}
          </div>

          <p style={{ color: "#cbd5e1", fontSize: "0.95rem", lineHeight: 1.6, maxWidth: 560, margin: "0 auto 28px auto" }}>
            Nuestro motor está auditando empresas activas en los registros oficiales de <strong>{selectedCity}</strong> y verificando buzones en servidores MX sin rebote.
            <br /><br />
            <strong>No necesitas quedarte esperando en esta página.</strong> Te notificaremos a <strong>{buyerEmail}</strong> y a tu WhatsApp cuando tu lote esté verificado con tu cotización justa.
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
                <span>Ver Rastreo en Vivo de la Orden</span>
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
              <span>Solicitar Otro Lote</span>
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
                Volver al Inicio
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

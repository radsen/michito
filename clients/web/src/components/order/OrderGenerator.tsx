import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "../../store";
import { selectCampaign, selectCity } from "../../store/slices/campaignSlice";
import { setTier, setVolume, setCurrency } from "../../store/slices/pricingSlice";
import { setBuyerInfo, startOrderSubmission, orderCreatedSuccess, orderFailed, restoreOrder, resetOrder } from "../../store/slices/orderSlice";
import { useGetCampaignsQuery, useCreateOrderMutation, useProfileIntentMutation } from "../../store/api/michitoApi";
import { LiveStatusTracker } from "../tracker/LiveStatusTracker";
import { WompiCheckoutModal } from "../payment/WompiCheckoutModal";
import { SUPPORTED_CURRENCIES, formatCurrencyAmount, formatUnitCurrency, SupportedCurrency } from "../../config/currencies";
import {
  Zap,
  Loader2,
  Sparkles,
  ShieldCheck,
  MapPin,
  Hash,
  Building2,
  User,
  Mail,
  Phone,
  Search,
  X,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  ArrowRight,
} from "lucide-react";

export const OrderGenerator: React.FC = () => {
  const dispatch = useDispatch();
  const { dict } = useSelector((state: RootState) => state.language);
  const { selectedCampaignId } = useSelector((state: RootState) => state.campaign);
  const {
    tier,
    volume,
    currency,
    unitPrice,
    unitPriceCop,
    discountPercent,
    subtotal,
    subtotalCop,
    total,
    totalCop,
  } = useSelector((state: RootState) => state.pricing);
  const { activeOrderId } = useSelector((state: RootState) => state.order);
  const partner = useSelector((state: RootState) => state.partner);
  const g = dict.generator;

  const curConfig = SUPPORTED_CURRENCIES[currency] || SUPPORTED_CURRENCIES.COP;

  // Campaigns catalog matching index.html
  const CAMPAIGN_OPTIONS = [
    {
      id: "tinkko_enterprise_offices",
      name: "🇨🇴 Espacios & Sedes Corporativas (Medellín / Bogotá)",
      country: "CO",
      currency: "COP",
      defaultCity: "Medellín",
    },
    {
      id: "eventos_ferias_b2b",
      name: "🇨🇴 Ferias Comerciales & Misiones de Compradores Internacionales",
      country: "CO",
      currency: "COP",
      defaultCity: "Medellín",
    },
    {
      id: "tinkko_dr_offices",
      name: "🇩🇴 Oficinas Corporativas República Dominicana (Santo Domingo / Santiago)",
      country: "DO",
      currency: "DOP",
      defaultCity: "Santo Domingo",
    },
    {
      id: "hebi",
      name: "🇨🇴 Gestión de Cartera B2B & Debida Diligencia de Contratistas",
      country: "CO",
      currency: "COP",
      defaultCity: "Bogotá",
    },
    {
      id: "chiketto",
      name: "🇨🇴 Software Empresarial, APIs & Facturación Electrónica DIAN",
      country: "CO",
      currency: "COP",
      defaultCity: "Bogotá",
    },
    {
      id: "blueoil",
      name: "🇨🇴 Suministro de Combustibles, Lubricantes & Flotas Pesadas",
      country: "CO",
      currency: "COP",
      defaultCity: "Medellín",
    },
    {
      id: "facility_services_b2b",
      name: "🇨🇴 Facility Management, Aseo Corporativo & Seguridad",
      country: "CO",
      currency: "COP",
      defaultCity: "Medellín",
    },
    {
      id: "warehouse_aburra_norte",
      name: "🇨🇴 Parques Industriales, Lotes & Bodegas Logísticas",
      country: "CO",
      currency: "COP",
      defaultCity: "Medellín",
    },
  ];

  const SUGGESTED_CITIES_BY_COUNTRY: Record<string, string[]> = {
    CO: [
      "🇨🇴 Toda Colombia",
      "Antioquia",
      "Bogotá D.C.",
      "Valle del Cauca",
      "Santander",
      "Costa Caribe",
      "Eje Cafetero",
      "Medellín",
      "Cali",
      "Barranquilla",
    ],
    DO: ["🇩🇴 Todo el País", "Santo Domingo", "Santiago", "Punta Cana", "La Romana"],
  };

  const currentCamp = CAMPAIGN_OPTIONS.find((c) => c.id === selectedCampaignId) || CAMPAIGN_OPTIONS[0];
  const suggestedCities = SUGGESTED_CITIES_BY_COUNTRY[currentCamp.country] || SUGGESTED_CITIES_BY_COUNTRY.CO;

  const [targetCity, setTargetCity] = useState(currentCamp.defaultCity);
  const [buyerName, setLocalName] = useState("Demo Lead Buyer");
  const [buyerEmail, setLocalEmail] = useState("buyer@demo.com");
  const [buyerPhone, setLocalPhone] = useState("+573001234567");
  const [formError, setFormError] = useState<string | null>(null);

  // Exclusions State
  const [isExclusionsOpen, setIsExclusionsOpen] = useState(false);
  const [exclusionsText, setExclusionsText] = useState("");

  const parsedExclusions = exclusionsText
    .split(/[\n,;]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);

  // 2-Step Guided Stepper States
  const [currentStep, setCurrentStep] = useState<1 | 2>(1);
  const [searchMode, setSearchMode] = useState<"direct" | "ai">("direct");

  // Stage 1 AI Intent Discovery States
  const [aiQuery, setAiQuery] = useState("");
  const [discoveryResult, setDiscoveryResult] = useState<any>(null);
  const [profileIntentMutation, { isLoading: isProfiling }] = useProfileIntentMutation();

  const handleProfileIntent = async (overrideQuery?: string) => {
    const q = (overrideQuery || aiQuery).trim();
    if (!q) return;
    setFormError(null);
    try {
      const res = await profileIntentMutation({ query: q }).unwrap();
      if (res && res.status === "success") {
        setDiscoveryResult(res);
        dispatch(selectCampaign(res.campaign_id));
        setTargetCity(res.city);
        dispatch(selectCity(res.city));
        const safeTier = (res.recommended_tier === 1 || res.recommended_tier === 3 ? res.recommended_tier : 2) as (1 | 2 | 3);
        dispatch(setTier(safeTier));
        dispatch(setVolume(res.recommended_limit));
      }
    } catch (err: any) {
      console.warn("AI Intent discovery error:", err);
    }
  };

  const handleProceedToStep2 = () => {
    if (!targetCity.trim()) {
      setFormError("Por favor ingresa la ciudad o territorio objetivo.");
      return;
    }
    setFormError(null);
    setCurrentStep(2);
  };

  useEffect(() => {
    const camp = CAMPAIGN_OPTIONS.find((c) => c.id === selectedCampaignId);
    if (camp) {
      setTargetCity(camp.defaultCity);
    }
  }, [selectedCampaignId]);

  const [createOrderMutation, { isLoading: isSubmitting }] = useCreateOrderMutation();

  const handleCampaignChange = (newId: string) => {
    dispatch(selectCampaign(newId));
    const camp = CAMPAIGN_OPTIONS.find((c) => c.id === newId);
    if (camp) {
      setTargetCity(camp.defaultCity);
      dispatch(selectCity(camp.defaultCity));
      if (camp.currency && camp.currency !== currency) {
        dispatch(setCurrency(camp.currency as SupportedCurrency));
      }
    }
  };

  const handleCityChange = (newCity: string) => {
    setTargetCity(newCity);
    dispatch(selectCity(newCity));
  };

  const formatCop = (val: number) => {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      maximumFractionDigits: 0,
    }).format(val);
  };

  const handleSubmitOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!buyerName.trim() || !buyerEmail.trim() || !targetCity.trim()) {
      setFormError("Por favor completa la ciudad, nombre y correo corporativo.");
      return;
    }

    dispatch(setBuyerInfo({ name: buyerName, email: buyerEmail, phone: buyerPhone }));
    dispatch(startOrderSubmission());

    try {
      const payload = {
        client: {
          name: buyerName,
          email: buyerEmail,
          phone: buyerPhone || "+573000000000",
          channel: "web_portal",
          referral_partner: partner.isAffiliate ? partner.partnerId : "direct",
        },
        request: {
          campaign_id: selectedCampaignId,
          country: currentCamp.country,
          city: targetCity,
          limit: volume,
          tier: tier,
          exclusions: parsedExclusions.length > 0 ? parsedExclusions : undefined,
          keywords_exclude: parsedExclusions.length > 0 ? parsedExclusions : undefined,
        },
      };

      const res = await createOrderMutation(payload).unwrap();
      if (res.status === "success") {
        dispatch(
          orderCreatedSuccess({
            orderId: res.order_id,
            status: res.order_status,
            totalAmountInCents: res.amount_in_cents || totalCop * 100,
            totalLeadsTarget: volume,
          })
        );
      } else {
        dispatch(orderFailed(res.message || "No se pudo crear la orden."));
      }
    } catch (err: any) {
      const msg = err?.data?.detail || "Error de conexión al generar la orden.";
      setFormError(msg);
      dispatch(orderFailed(msg));
    }
  };

  return (
    <section id="generador" className="generator-section">
      <div className="section-container">
        <div className="section-header">
          <span className="section-kicker">{g.kicker}</span>
          <h2 className="section-title">{g.title}</h2>
          <p className="section-subtitle">{g.subtitle}</p>
        </div>

        <div className="generator-layout">
          {/* Form Card */}
          <div className="generator-card">
            {activeOrderId && (
              <div className="active-order-floating-banner" data-testid="active-order-banner">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-xs sm:text-sm font-semibold text-white">
                    Prospección activa: <strong className="font-mono text-sky-400">{activeOrderId}</strong>
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      document.querySelector(".generator-tracker-area")?.scrollIntoView({ behavior: "smooth" });
                    }}
                    className="active-order-action-link"
                  >
                    Ver Estado
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (window.confirm("¿Deseas iniciar una nueva búsqueda? Tu orden anterior no se borrará.")) {
                        dispatch(resetOrder());
                      }
                    }}
                    className="active-order-reset-link"
                  >
                    Nueva Orden
                  </button>
                </div>
              </div>
            )}

            {/* Guided 2-Step Stepper Header */}
            <div className="generator-stepper-header">
              <button
                type="button"
                onClick={() => setCurrentStep(1)}
                className={`stepper-pill ${currentStep === 1 ? "active" : "done"}`}
              >
                <span className="stepper-circle">{currentStep === 2 ? "✓" : "1"}</span>
                <span>1. {g.step1Heading?.replace(/^1\.\s*/, "") || "Qué Empresas Buscas"}</span>
              </button>
              <div className="stepper-divider-line" />
              <button
                type="button"
                onClick={handleProceedToStep2}
                className={`stepper-pill ${currentStep === 2 ? "active" : ""}`}
              >
                <span className="stepper-circle">2</span>
                <span>2. {g.buyerSection}</span>
              </button>
            </div>

            {currentStep === 1 ? (
              <div className="generator-step-1">
                <div className="card-header-box">
                  <h3 className="generator-card-title">{g.step1Heading}</h3>
                  <p className="generator-card-sub">{g.step1Sub}</p>

                  {partner.isAffiliate && (
                    <div className="partner-attribution-notice" data-testid="partner-order-notice">
                      <span className="partner-notice-text">Alianza Oficial: <strong>{partner.name}</strong></span>
                      {partner.discountRate > 0 && (
                        <span className="partner-notice-discount">
                          • {(partner.discountRate * 100).toFixed(0)}% dto. preferencial aplicado
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Mode Switcher Tabs */}
                <div className="generator-mode-tabs">
                  <button
                    type="button"
                    onClick={() => setSearchMode("direct")}
                    className={`generator-mode-tab ${searchMode === "direct" ? "active" : ""}`}
                  >
                    <span>📋 Selección Directa</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setSearchMode("ai")}
                    className={`generator-mode-tab ${searchMode === "ai" ? "active" : ""}`}
                  >
                    <Sparkles className="w-3.5 h-3.5 text-sky-400" />
                    <span>Búsqueda con IA (Michito Engine™)</span>
                  </button>
                </div>

                {searchMode === "ai" ? (
                  /* AI Natural Language Intent Hero */
                  <div className="ai-intent-hero">
                    <div className="ai-intent-header">
                      <span className="ai-intent-badge">
                        <Sparkles className="w-3.5 h-3.5 text-sky-400" />
                        Michito Intent Engine™
                      </span>
                      <h3 className="ai-intent-title">¿A qué empresas le quieres vender hoy?</h3>
                      <p className="ai-intent-subtitle">
                        Describe tu oferta o tu cliente ideal en una frase. Nuestra IA configurará el lote óptimo en tiempo real.
                      </p>
                    </div>

                    <div className="ai-intent-input-wrap">
                      <input
                        type="text"
                        value={aiQuery}
                        onChange={(e) => setAiQuery(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            handleProfileIntent();
                          }
                        }}
                        placeholder="Ej: Vendo software y busco firmas de abogados en Bogotá con más de 10 empleados..."
                        className="ai-intent-input"
                        disabled={isProfiling}
                      />
                      <button
                        type="button"
                        onClick={() => handleProfileIntent()}
                        disabled={isProfiling || !aiQuery.trim()}
                        className="ai-intent-submit-btn"
                      >
                        {isProfiling ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span>Analizando...</span>
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-4 h-4" />
                            <span>Descubrir con IA</span>
                          </>
                        )}
                      </button>
                    </div>

                    {/* Quick Suggestion Pills */}
                    <div className="ai-pills-container">
                      <span className="ai-pills-label">O explora búsquedas frecuentes:</span>
                      <div className="ai-pills-grid">
                        {[
                          { label: "Oficinas & Sedes Corporativas (Medellín)", query: "Busco empresas medianas y corporativas para arriendo de oficinas y coworking en Medellín" },
                          { label: "Logística y Flotas Pesadas (Bogotá)", query: "Empresas de transporte de carga pesada y distribución logística en Bogotá para suministro de combustible" },
                          { label: "Ferias Comerciales B2B (Medellín)", query: "Expositores de ferias comerciales y compradores internacionales en Medellín" },
                          { label: "Software & Facturación DIAN (Bogotá)", query: "Clínicas, IPS y empresas de servicios en Bogotá con facturación electrónica DIAN" },
                          { label: "Bodegas y Parques Industriales (Cali)", query: "Empresas buscando bodegas y centros de distribución logística en parques industriales en Cali" },
                        ].map((pill, idx) => (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => {
                              setAiQuery(pill.query);
                              handleProfileIntent(pill.query);
                            }}
                            className="ai-quick-pill"
                          >
                            <span>{pill.label}</span>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Discovery Match Card */}
                    {discoveryResult && (
                      <div className="discovery-card">
                        <div className="discovery-match-header">
                          <div>
                            <span className="discovery-match-badge">
                              <CheckCircle2 className="w-4 h-4" />
                              {discoveryResult.estimated_matches} Empresas Encontradas en {discoveryResult.city}
                            </span>
                            <p className="text-xs text-slate-300 mt-1 font-medium">
                              {discoveryResult.summary_message}
                            </p>
                          </div>
                          <div className="text-right">
                            <span className="text-xs text-slate-400 block">Lote Sugerido:</span>
                            <strong className="text-sm font-bold text-emerald-400">
                              {discoveryResult.recommended_limit} Contactos Directos ({formatCop(discoveryResult.pricing.total_cop)} COP)
                            </strong>
                          </div>
                        </div>

                        {discoveryResult.sample_preview && (
                          <div className="discovery-sample-preview">
                            <div className="discovery-sample-title">Ejemplo de cuenta calificada en este lote:</div>
                            <div className="discovery-sample-company">{discoveryResult.sample_preview.company_name}</div>
                            <div className="discovery-sample-person">
                              {discoveryResult.sample_preview.masked_decision_maker}
                            </div>
                            <div className="discovery-sample-badges">
                              <span className="discovery-sample-badge">✓ NIT Vigente en Cámara de Comercio</span>
                              <span className="discovery-sample-badge">✓ Mailbox MX Corporativo Verificado</span>
                              <span className="discovery-sample-badge">✓ Huella HTTP y Dominio Activo</span>
                              <span className="discovery-sample-badge">✓ Solvencia Financiera Aprobada</span>
                            </div>
                            {discoveryResult.sample_preview.signals && (
                              <div className="discovery-sample-signals">
                                <strong>Señal de Compra:</strong> {discoveryResult.sample_preview.signals}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  /* Direct Selection Configuration */
                  <div className="direct-selection-wrapper">
                    {/* Campaign Picker */}
                    <div className="form-group">
                      <label className="form-label">
                        <Building2 className="form-label-icon text-sky-400" />
                        <span>{g.campaignLabel}</span>
                      </label>
                      <select
                        value={selectedCampaignId}
                        onChange={(e) => handleCampaignChange(e.target.value)}
                        className="form-select"
                      >
                        {CAMPAIGN_OPTIONS.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Enrichment Tier Selector */}
                    <div className="form-group">
                      <label className="form-label">{g.tierLabel}</label>
                      <div className="tier-pills-selector">
                        <button
                          type="button"
                          onClick={() => dispatch(setTier(1))}
                          className={`tier-pill ${tier === 1 ? "active" : ""}`}
                        >
                          Directorio Base ({formatUnitCurrency(curConfig.tierPrices[1], currency)})
                        </button>
                        <button
                          type="button"
                          onClick={() => dispatch(setTier(2))}
                          className={`tier-pill ${tier === 2 ? "active" : ""}`}
                        >
                          Contactos Directos ({formatUnitCurrency(curConfig.tierPrices[2], currency)}) ⭐
                        </button>
                        <button
                          type="button"
                          onClick={() => dispatch(setTier(3))}
                          className={`tier-pill ${tier === 3 ? "active" : ""}`}
                        >
                          Auditoría Completa ({formatUnitCurrency(curConfig.tierPrices[3], currency)})
                        </button>
                      </div>
                    </div>

                    {/* Target City & Account Volume Row */}
                    <div className="form-row-2">
                      <div className="form-group">
                        <label className="form-label">
                          <MapPin className="form-label-icon text-emerald-400" />
                          <span>{g.cityLabel}</span>
                        </label>
                        <input
                          type="text"
                          required
                          value={targetCity}
                          onChange={(e) => handleCityChange(e.target.value)}
                          placeholder={g.cityPlaceholder}
                          className="form-input"
                        />
                        <div className="city-quick-pills">
                          {suggestedCities.map((city) => (
                            <button
                              key={city}
                              type="button"
                              onClick={() => handleCityChange(city)}
                              className={`city-pill ${targetCity.toLowerCase() === city.toLowerCase() ? "active" : ""}`}
                            >
                              {city}
                            </button>
                          ))}
                        </div>
                        <span className="form-hint">
                          Ingresa cualquier ciudad o territorio de cobertura comercial.
                        </span>
                      </div>

                      <div className="form-group">
                        <label className="form-label">
                          <Hash className="form-label-icon text-purple-400" />
                          <span>{g.volumeLabel} <strong className="text-sky-400">{volume} cuentas</strong></span>
                        </label>
                        <div className="volume-presets-grid">
                          <button
                            type="button"
                            onClick={() => dispatch(setVolume(10))}
                            className={`preset-btn ${volume === 10 ? "active" : ""}`}
                          >
                            10
                          </button>
                          <button
                            type="button"
                            onClick={() => dispatch(setVolume(25))}
                            className={`preset-btn ${volume === 25 ? "active" : ""}`}
                          >
                            25 <span className="discount-tag">-6%</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => dispatch(setVolume(50))}
                            className={`preset-btn ${volume === 50 ? "active" : ""}`}
                          >
                            50 <span className="discount-tag">-12%</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => dispatch(setVolume(100))}
                            className={`preset-btn ${volume === 100 ? "active" : ""}`}
                          >
                            100 <span className="discount-tag">-20%</span>
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Volume Slider for Custom Quantities */}
                    <div className="form-group slider-group">
                      <div className="slider-header">
                        <span className="text-xs text-slate-400">Ajuste fino de volumen:</span>
                        <span className="slider-value-badge">{volume} cuentas</span>
                      </div>
                      <input
                        type="range"
                        min="10"
                        max="500"
                        step="5"
                        value={volume}
                        onChange={(e) => dispatch(setVolume(parseInt(e.target.value, 10)))}
                        className="volume-slider"
                      />
                      <div className="slider-ticks">
                        <span>10 (Rápido)</span>
                        <span>25 (Rec.)</span>
                        <span>50</span>
                        <span>100</span>
                        <span>250</span>
                        <span>500+</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Collapsible Customer & Domain Exclusion Drawer */}
                <div className="exclusions-section">
                  <button
                    type="button"
                    onClick={() => setIsExclusionsOpen(!isExclusionsOpen)}
                    className="exclusions-toggle-btn"
                    aria-expanded={isExclusionsOpen}
                  >
                    <div className="exclusions-toggle-title">
                      <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>Excluir Clientes Actuales o Competidores (Opcional)</span>
                      {parsedExclusions.length > 0 && (
                        <span className="exclusions-count-badge">
                          {parsedExclusions.length} {parsedExclusions.length === 1 ? "exclusión activa" : "exclusiones activas"}
                        </span>
                      )}
                    </div>
                    {isExclusionsOpen ? (
                      <ChevronUp className="w-4 h-4 text-slate-400 shrink-0" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" />
                    )}
                  </button>

                  {isExclusionsOpen && (
                    <div className="exclusions-drawer">
                      <p className="exclusions-hint">
                        Ingresa dominios web o NITs que ya sean tus clientes o desees omitir (ej: hebisend.com, tinkko.com, 900123456). Se excluirán automáticamente del lote con costo cero.
                      </p>
                      <textarea
                        value={exclusionsText}
                        onChange={(e) => setExclusionsText(e.target.value)}
                        placeholder="Pega dominios o NITs separados por coma o salto de línea (ej: cliente1.com, 901234567, empresa.co)..."
                        className="exclusions-textarea"
                        rows={3}
                      />
                      {parsedExclusions.length > 0 && (
                        <div className="exclusions-preview-tags">
                          {parsedExclusions.slice(0, 6).map((item, idx) => (
                            <span key={idx} className="exclusion-tag">
                              {item}
                            </span>
                          ))}
                          {parsedExclusions.length > 6 && (
                            <span className="exclusion-tag-more">+{parsedExclusions.length - 6} más</span>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Price Calculation Box */}
                <div className="calc-summary-box">
                  <div className="calc-row">
                    <span>
                      Precio por cuenta (
                      {tier === 1
                        ? "Directorio Base"
                        : tier === 2
                        ? "Contactos Directos"
                        : "Auditoría Completa"}
                      ):
                    </span>
                    <span>{formatCurrencyAmount(unitPrice, currency)}</span>
                  </div>
                  <div className="calc-row">
                    <span>Subtotal ({volume} cuentas):</span>
                    <span>{formatCurrencyAmount(subtotal, currency)}</span>
                  </div>
                  {discountPercent > 0 && (
                    <div className="calc-row text-emerald-400">
                      <span className="flex items-center gap-1">
                        <Sparkles className="w-3.5 h-3.5" /> Descuento por volumen (-{discountPercent}%):
                      </span>
                      <span>-{formatCurrencyAmount(subtotal - total, currency)}</span>
                    </div>
                  )}
                  <div className="calc-row-total">
                    <span>{g.summaryTotal}</span>
                    <span className="total-cop">{formatCurrencyAmount(total, currency)}</span>
                  </div>
                  {currency !== "COP" && (
                    <div className="text-xs text-slate-400 mt-1 text-right">
                      Equivalente en liquidación segura Wompi: {formatCop(totalCop)} COP
                    </div>
                  )}
                  <div className="fair-billing-pill">
                    <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>{g.fairBillingNote}</span>
                  </div>
                </div>

                {formError && (
                  <div className="form-error-banner" style={{ marginTop: "16px" }}>
                    <span>{formError}</span>
                  </div>
                )}

                <button
                  type="button"
                  onClick={handleProceedToStep2}
                  className="generator-submit-btn"
                  style={{ marginTop: "24px" }}
                >
                  <span>Continuar a Datos de Entrega</span>
                  <ArrowRight className="w-5 h-5 ml-2" />
                </button>
              </div>
            ) : (
              /* Step 2: Buyer Delivery Info & Validation */
              <form onSubmit={handleSubmitOrder} className="generator-step-2">
                <div className="card-header-box">
                  <h3 className="generator-card-title">2. {g.buyerSection}</h3>
                  <p className="generator-card-sub">{g.buyerSectionSub}</p>
                </div>

                {/* Selected Order Recap */}
                <div className="generator-recap-box">
                  <div className="recap-item">
                    <span className="recap-label">Vertical / Perfil</span>
                    <span className="recap-value">{currentCamp.name}</span>
                  </div>
                  <div className="recap-item">
                    <span className="recap-label">Ciudad / Territorio</span>
                    <span className="recap-value">{targetCity}</span>
                  </div>
                  <div className="recap-item">
                    <span className="recap-label">Lote Seleccionado</span>
                    <span className="recap-value">
                      {volume} cuentas ({tier === 1 ? "Directorio Base" : tier === 2 ? "Contactos Directos" : "Auditoría Completa"})
                    </span>
                  </div>
                  {parsedExclusions.length > 0 && (
                    <div className="recap-item">
                      <span className="recap-label">Exclusiones Activas</span>
                      <span className="recap-value text-amber-300 font-medium">
                        {parsedExclusions.length} {parsedExclusions.length === 1 ? "cuenta excluida" : "cuentas excluidas"}
                      </span>
                    </div>
                  )}
                  <div className="recap-item">
                    <span className="recap-label">Inversión Estimada</span>
                    <span className="recap-value text-emerald-400">{formatCurrencyAmount(total, currency)}</span>
                  </div>
                </div>

                <div className="buyer-fields-grid">
                  <div className="form-group">
                    <label className="form-label">
                      <User className="form-label-icon" />
                      <span>{g.buyerName}</span>
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="Ej: Juan Carlos Pérez"
                      value={buyerName}
                      onChange={(e) => setLocalName(e.target.value)}
                      className="form-input"
                    />
                    <span className="form-hint">{g.buyerNameHint}</span>
                  </div>
                  <div className="form-group">
                    <label className="form-label">
                      <Mail className="form-label-icon" />
                      <span>{g.buyerEmail}</span>
                    </label>
                    <input
                      type="email"
                      required
                      placeholder="director@empresa.com"
                      value={buyerEmail}
                      onChange={(e) => setLocalEmail(e.target.value)}
                      className="form-input"
                    />
                    <span className="form-hint">{g.buyerEmailHint}</span>
                  </div>
                  <div className="form-group">
                    <label className="form-label">
                      <Phone className="form-label-icon" />
                      <span>{g.buyerPhone}</span>
                    </label>
                    <input
                      type="tel"
                      required
                      placeholder="+57 300 123 4567"
                      value={buyerPhone}
                      onChange={(e) => setLocalPhone(e.target.value)}
                      className="form-input"
                    />
                    <span className="form-hint">{g.buyerPhoneHint}</span>
                  </div>
                </div>

                <div className="fair-billing-pill" style={{ marginTop: "16px" }}>
                  <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>{g.fairBillingNote}</span>
                </div>

                {formError && (
                  <div className="form-error-banner" style={{ marginTop: "16px" }}>
                    <span>{formError}</span>
                  </div>
                )}

                <div className="generator-step-actions">
                  <button
                    type="button"
                    onClick={() => setCurrentStep(1)}
                    className="generator-back-btn"
                  >
                    ← Modificar Búsqueda
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="generator-submit-btn"
                    style={{ flex: 1 }}
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        <span>Iniciando calificación asíncrona...</span>
                      </>
                    ) : (
                      <>
                        <Zap className="w-5 h-5 fill-current" />
                        <span>{g.submitBtn}</span>
                      </>
                    )}
                  </button>
                </div>

                <p className="generator-disclaimer">{g.disclaimer}</p>
              </form>
            )}
          </div>

          {/* Live Tracker & Results (mounts upon submission) */}
          {activeOrderId && (
            <div className="generator-tracker-area">
              <LiveStatusTracker />
            </div>
          )}
        </div>
      </div>

      <WompiCheckoutModal />
    </section>
  );
};

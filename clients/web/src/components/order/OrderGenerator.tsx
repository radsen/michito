import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "../../store";
import { selectCampaign, selectCity } from "../../store/slices/campaignSlice";
import { setTier, setVolume, setCurrency } from "../../store/slices/pricingSlice";
import {
  setBuyerInfo,
  startOrderSubmission,
  orderCreatedSuccess,
  orderFailed,
  resetOrder,
} from "../../store/slices/orderSlice";
import {
  useCreateOrderMutation,
  useProfileIntentMutation,
  useSearchRolesQuery,
  useRecordRoleUsageMutation,
  useGetCampaignPresetsQuery,
  useCreateCustomTaxonomyMutation,
  LocationAllocationPayload,
  CreateOrderPayload,
} from "../../store/api/michitoApi";
import { LiveStatusTracker } from "../tracker/LiveStatusTracker";
import { TagPillInput } from "../common/TagPillInput";
import { GeoQuotaAllocator } from "../common/GeoQuotaAllocator";
import { SectorSelector } from "../common/SectorSelector";
import {
  SUPPORTED_CURRENCIES,
  formatCurrencyAmount,
  formatUnitCurrency,
  SupportedCurrency,
} from "../../config/currencies";
import {
  Zap,
  Loader2,
  Sparkles,
  ShieldCheck,
  MapPin,
  Hash,
  Building2,
  Layers,
  User,
  Mail,
  Phone,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  ArrowRight,
  Target,
  SlidersHorizontal,
  Compass,
  FileText,
  RotateCcw,
  Share2,
  Copy,
  Check,
  ShoppingCart,
  TrendingUp,
} from "lucide-react";

interface PresetTemplate {
  id: string;
  name: string;
  country: string;
  currency: SupportedCurrency;
  defaultCity: string;
  isMultiCountry: boolean;
  offerDescription: string;
  sectors: string[];
  roles: string[];
  keywords: string[];
  locations: LocationAllocationPayload[];
}

const PRESET_TEMPLATES: PresetTemplate[] = [
  {
    id: "tinkko_enterprise_offices",
    name: "🇨🇴 Espacios & Sedes Corporativas (Medellín / Bogotá)",
    country: "CO",
    currency: "COP",
    defaultCity: "Medellín",
    isMultiCountry: false,
    offerDescription:
      "Suministro de oficinas corporativas amobladas, sedes satélite y espacios de coworking llave en mano para empresas en expansión.",
    sectors: ["real_estate_coworking", "services_consulting"],
    roles: ["Gerente General", "Director de Operaciones", "Director de Recursos Humanos", "Gerente Administrativo"],
    keywords: ["oficinas corporativas", "coworking", "espacio de trabajo", "sede comercial"],
    locations: [
      { country: "CO", region: "Antioquia", city: "Medellín", allocated_leads: 15 },
      { country: "CO", region: "Bogotá D.C.", city: "Bogotá", allocated_leads: 10 },
    ],
  },
  {
    id: "chiketto",
    name: "🇨🇴 Software Empresarial & Facturación DIAN",
    country: "CO",
    currency: "COP",
    defaultCity: "Bogotá",
    isMultiCountry: false,
    offerDescription:
      "Software ERP en la nube, APIs de facturación y nómina electrónica DIAN y sincronización contable automatizada.",
    sectors: ["tech_software", "finance_fintech"],
    roles: ["Gerente General", "Gerente Financiero (CFO)", "Director de Tecnología (CTO)", "Contador General"],
    keywords: ["facturación electrónica", "nómina", "software ERP", "DIAN"],
    locations: [
      { country: "CO", region: "Bogotá D.C.", city: "Bogotá", allocated_leads: 15 },
      { country: "CO", region: "Antioquia", city: "Medellín", allocated_leads: 10 },
    ],
  },
  {
    id: "chiketto_school_ids",
    name: "🇨🇴 Colegios, Carnets & Identificaciones Escolares (Chiketto)",
    country: "CO",
    currency: "COP",
    defaultCity: "Medellín",
    isMultiCountry: false,
    offerDescription:
      "Servicio especializado de impresión y suministro de carnets estudiantiles en PVC de alta durabilidad, identificaciones escolares, cordones institucionales y sistemas de carnetización para colegios y academias.",
    sectors: ["education_schools"],
    roles: ["Rector / Rectora de Institución Educativa", "Coordinador Administrativo & Compras Escolares", "Director de Colegio", "Jefe de Compras"],
    keywords: ["colegios", "carnets estudiantiles", "identificaciones escolares", "institucion educativa"],
    locations: [
      { country: "CO", region: "Antioquia", city: "Medellín", allocated_leads: 15 },
      { country: "CO", region: "Bogotá D.C.", city: "Bogotá", allocated_leads: 10 },
    ],
  },
  {
    id: "blueoil",
    name: "🇨🇴 Combustibles & Flotas Pesadas",
    country: "CO",
    currency: "COP",
    defaultCity: "Medellín",
    isMultiCountry: false,
    offerDescription:
      "Suministro mayorista de combustible diésel, lubricantes industriales y abastecimiento directo en patio para empresas de transporte pesado y logística.",
    sectors: ["energy_fuel", "logistics_transport"],
    roles: ["Director de Operaciones", "Jefe de Compras", "Jefe de Flota", "Gerente de Logística"],
    keywords: ["transporte pesado", "flota de camiones", "combustible diésel", "logística"],
    locations: [
      { country: "CO", region: "Antioquia", city: "Medellín", allocated_leads: 15 },
      { country: "CO", region: "Valle del Cauca", city: "Cali", allocated_leads: 10 },
    ],
  },
  {
    id: "facility_services_b2b",
    name: "🇨🇴 Facility Services & Aseo Corporativo",
    country: "CO",
    currency: "COP",
    defaultCity: "Medellín",
    isMultiCountry: false,
    offerDescription:
      "Servicios integrales de aseo institucional, desinfección, mantenimiento locativo, vigilancia privada y seguridad física corporativa.",
    sectors: ["facilities_security", "services_consulting"],
    roles: ["Gerente de Operaciones", "Gerente Administrativo", "Director de Facilities", "Jefe de Mantenimiento"],
    keywords: ["aseo corporativo", "seguridad privada", "facility management", "mantenimiento"],
    locations: [
      { country: "CO", region: "Antioquia", city: "Medellín", allocated_leads: 15 },
      { country: "CO", region: "Bogotá D.C.", city: "Bogotá", allocated_leads: 10 },
    ],
  },
  {
    id: "warehouse_aburra_norte",
    name: "🇨🇴 Parques Industriales & Bodegas",
    country: "CO",
    currency: "COP",
    defaultCity: "Medellín",
    isMultiCountry: false,
    offerDescription:
      "Arriendo y comercialización de bodegas industriales, centros de distribución logística y lotes empresariales de alto metraje.",
    sectors: ["real_estate_coworking", "logistics_transport"],
    roles: ["Gerente de Logística", "Director de Operaciones", "Gerente General", "Jefe de Almacén"],
    keywords: ["bodegas industriales", "parque empresarial", "centro de distribución"],
    locations: [
      { country: "CO", region: "Antioquia", city: "Medellín", allocated_leads: 15 },
      { country: "CO", region: "Antioquia", city: "Bello", allocated_leads: 10 },
    ],
  },
  {
    id: "hebi",
    name: "🇨🇴 Gestión de Cartera B2B & Cobranza",
    country: "CO",
    currency: "COP",
    defaultCity: "Bogotá",
    isMultiCountry: false,
    offerDescription:
      "Recuperación de cartera vencida B2B, gestión de cobranza prejudicial y auditoría de riesgo crediticio para contratistas y distribuidores.",
    sectors: ["finance_fintech", "legal_compliance"],
    roles: ["Gerente Financiero (CFO)", "Director Jurídico", "Jefe de Cartera", "Gerente General"],
    keywords: ["cobranza", "cartera vencida", "debida diligencia", "riesgo crediticio"],
    locations: [
      { country: "CO", region: "Bogotá D.C.", city: "Bogotá", allocated_leads: 15 },
      { country: "CO", region: "Antioquia", city: "Medellín", allocated_leads: 10 },
    ],
  },
  {
    id: "eventos_ferias_b2b",
    name: "🌎 Cross-Border / Ferias Comerciales & Misiones B2B",
    country: "MULTI",
    currency: "USD",
    defaultCity: "Medellín, Santo Domingo, Quito",
    isMultiCountry: true,
    offerDescription:
      "Prospección internacional para eventos feriales, misiones comerciales y compradores corporativos en Colombia, República Dominicana y Ecuador.",
    sectors: ["services_consulting", "logistics_transport"],
    roles: ["Director Comercial", "Gerente de Exportaciones", "Director de Mercadeo", "Gerente General"],
    keywords: ["ferias comerciales", "misiones comerciales", "compradores internacionales"],
    locations: [
      { country: "CO", region: "Antioquia", city: "Medellín", allocated_leads: 10 },
      { country: "DO", region: "Distrito Nacional", city: "Santo Domingo", allocated_leads: 8 },
      { country: "EC", region: "Pichincha", city: "Quito", allocated_leads: 7 },
    ],
  },
  {
    id: "tinkko_dr_offices",
    name: "🇩🇴 Oficinas Corporativas República Dominicana",
    country: "DO",
    currency: "DOP",
    defaultCity: "Santo Domingo",
    isMultiCountry: false,
    offerDescription:
      "Espacios de oficina corporativa y sedes empresariales en Santo Domingo y Santiago de los Caballeros para empresas e instituciones.",
    sectors: ["real_estate_coworking"],
    roles: ["Gerente General", "Director de Operaciones", "Gerente Administrativo"],
    keywords: ["oficinas corporativas", "Santo Domingo", "Santiago"],
    locations: [
      { country: "DO", region: "Distrito Nacional", city: "Santo Domingo", allocated_leads: 15 },
      { country: "DO", region: "Santiago", city: "Santiago", allocated_leads: 10 },
    ],
  },
  {
    id: "tinkko_ec_offices",
    name: "🇪🇨 Sedes & Oficinas Corporativas Ecuador",
    country: "EC",
    currency: "USD",
    defaultCity: "Quito",
    isMultiCountry: false,
    offerDescription:
      "Oficinas ejecutivas y centros de negocios corporativos en Quito y Guayaquil para compañías en crecimiento.",
    sectors: ["real_estate_coworking"],
    roles: ["Gerente General", "Director de Operaciones", "Gerente Administrativo"],
    keywords: ["oficinas", "coworking", "Quito", "Guayaquil"],
    locations: [
      { country: "EC", region: "Pichincha", city: "Quito", allocated_leads: 15 },
      { country: "EC", region: "Guayas", city: "Guayaquil", allocated_leads: 10 },
    ],
  },
  {
    id: "alimentos_distribucion",
    name: "🇨🇴 Alimentos & Canal HORECA",
    country: "CO",
    currency: "COP",
    defaultCity: "Bogotá",
    isMultiCountry: false,
    offerDescription:
      "Proveeduría mayorista de insumos alimenticios, perecederos, granos y abarrotes para cadenas de restaurantes, hoteles y distribuidores independientes.",
    sectors: ["retail_commerce", "consumer_goods", "logistics_transport"],
    roles: ["Jefe de Compras", "Director de Abastecimiento", "Gerente de Alimentos y Bebidas", "Gerente General"],
    keywords: ["alimentos", "insumos gastronómicos", "HORECA", "abastecimiento"],
    locations: [
      { country: "CO", region: "Bogotá D.C.", city: "Bogotá", allocated_leads: 15 },
      { country: "CO", region: "Antioquia", city: "Medellín", allocated_leads: 10 },
    ],
  },
  {
    id: "materiales_construccion",
    name: "🇨🇴 Materiales de Construcción & Obras",
    country: "CO",
    currency: "COP",
    defaultCity: "Medellín",
    isMultiCountry: false,
    offerDescription:
      "Suministro de aceros, cementos, prefabricados e insumos ferreteros para constructoras, contratistas de obras civiles y desarrolladores inmobiliarios.",
    sectors: ["construction_realestate", "industrial_manufacturing"],
    roles: ["Director de Obra", "Gerente de Compras e Insumos", "Gerente de Proyectos", "Gerente General"],
    keywords: ["materiales construcción", "aceros", "cemento", "obras civiles"],
    locations: [
      { country: "CO", region: "Antioquia", city: "Medellín", allocated_leads: 15 },
      { country: "CO", region: "Atlántico", city: "Barranquilla", allocated_leads: 10 },
    ],
  },
];

export const OrderGenerator: React.FC = () => {
  const dispatch = useDispatch();
  const { dict } = useSelector((state: RootState) => state.language);
  const { selectedCampaignId } = useSelector((state: RootState) => state.campaign);
  const {
    tier,
    volume,
    currency,
    unitPrice,
    discountPercent,
    subtotal,
    total,
    totalCop,
  } = useSelector((state: RootState) => state.pricing);
  const { activeOrderId } = useSelector((state: RootState) => state.order);
  const partner = useSelector((state: RootState) => state.partner);
  const g = dict.generator;

  const curConfig = SUPPORTED_CURRENCIES[currency] || SUPPORTED_CURRENCIES.COP;

  // Selected Preset or "custom" Universal Mode
  const [selectedPresetId, setSelectedPresetId] = useState<string>(
    selectedCampaignId || "tinkko_enterprise_offices"
  );

  // Universal Prospecting Core Dynamic State
  const initialPreset =
    PRESET_TEMPLATES.find((p) => p.id === selectedCampaignId) || PRESET_TEMPLATES[0];

  const [offerDescription, setOfferDescription] = useState<string>(
    initialPreset?.offerDescription || ""
  );
  const [targetRoles, setTargetRoles] = useState<string[]>(
    initialPreset?.roles || ["Gerente General", "Director de Operaciones"]
  );
  const [selectedSectors, setSelectedSectors] = useState<string[]>(
    initialPreset?.sectors || ["real_estate_coworking"]
  );
  const [positiveKeywords, setPositiveKeywords] = useState<string[]>(
    initialPreset?.keywords || ["oficinas", "coworking"]
  );
  const [locationAllocations, setLocationAllocations] = useState<LocationAllocationPayload[]>(
    initialPreset?.locations || [
      { country: "CO", region: "Antioquia", city: "Medellín", allocated_leads: 15 },
      { country: "CO", region: "Bogotá D.C.", city: "Bogotá", allocated_leads: 10 },
    ]
  );

  // Bidirectional Directionality (Sales vs Procurement/RFQ)
  const [directionality, setDirectionality] = useState<"vendor_to_clients" | "client_to_vendors">("vendor_to_clients");
  const [rfqSpecifications, setRfqSpecifications] = useState<string>("");

  // Buyer Info State
  const [buyerName, setLocalName] = useState("Demo Lead Buyer");
  const [buyerEmail, setLocalEmail] = useState("buyer@demo.com");
  const [buyerPhone, setLocalPhone] = useState("+573001234567");
  const [formError, setFormError] = useState<string | null>(null);

  // Exclusions Drawer & Tag State
  const [isExclusionsOpen, setIsExclusionsOpen] = useState(false);
  const [exclusionsText, setExclusionsText] = useState("");
  const [negativeExclusions, setNegativeExclusions] = useState<string[]>([]);

  // 2-Step Stepper & Mode Switcher
  const [currentStep, setCurrentStep] = useState<1 | 2>(1);
  const [searchMode, setSearchMode] = useState<"direct" | "ai">("direct");

  // Stage 1 AI Intent Discovery States
  const [aiQuery, setAiQuery] = useState("");
  const [discoveryResult, setDiscoveryResult] = useState<any>(null);
  const [profileIntentMutation, { isLoading: isProfiling }] = useProfileIntentMutation();

  // Phase 4: Shareable Quote & Remote Presets State
  const [quoteSharedToast, setQuoteSharedToast] = useState<string | null>(null);
  const [isSharingQuote, setIsSharingQuote] = useState(false);
  const { data: remotePresetsData } = useGetCampaignPresetsQuery();

  const availablePresets: PresetTemplate[] = React.useMemo<PresetTemplate[]>(() => {
    const list: PresetTemplate[] = [...PRESET_TEMPLATES];
    if (remotePresetsData?.presets) {
      for (const rp of remotePresetsData.presets) {
        if (!list.some((p) => p.id === rp.id)) {
          list.push({
            id: rp.id,
            name: rp.name,
            country: rp.country || "CO",
            currency: (rp.currency as SupportedCurrency) || "COP",
            defaultCity: rp.cities?.[0] || "Medellín",
            isMultiCountry: rp.country === "MULTI",
            offerDescription: rp.description || "",
            sectors: rp.sectors || [],
            roles: rp.roles || [],
            keywords: [],
            locations: (rp.cities || ["Medellín"]).map((c: string) => ({
              country: rp.country || "CO",
              city: c,
              allocated_leads: 10,
            })),
          });
        }
      }
    }
    return list;
  }, [remotePresetsData]);

  // Roles Autocomplete Data
  const { data: rolesData } = useSearchRolesQuery({ limit: 15 });
  const [recordRoleUsage] = useRecordRoleUsageMutation();
  const apiRoles = rolesData?.roles
    ?.map((r: any) => r.canonical_title || r.role_title || r.name)
    .filter((title: any): title is string => typeof title === "string" && Boolean(title.trim()));
  const suggestedRoles =
    apiRoles && apiRoles.length > 0
      ? apiRoles
      : [
          "Gerente General",
          "Director de Operaciones",
          "Director de Compras / Abastecimiento",
          "Director Comercial / Ventas",
          "Gerente Financiero (CFO)",
          "Director de Tecnología (CTO)",
          "Gerente de Logística",
          "Director de Recursos Humanos",
        ];

  // API Order Mutation
  const [createOrderMutation, { isLoading: isSubmitting }] = useCreateOrderMutation();

  // Sync with selectedCampaignId from outside (e.g. VerticalProfiles click)
  useEffect(() => {
    if (selectedCampaignId && selectedCampaignId !== selectedPresetId) {
      handlePresetChange(selectedCampaignId);
    }
  }, [selectedCampaignId]);

  const handlePresetChange = (presetId: string) => {
    setSelectedPresetId(presetId);
    dispatch(selectCampaign(presetId));

    if (presetId === "custom") {
      setOfferDescription("");
      setSelectedSectors([]);
      setTargetRoles(["Gerente General", "Director Comercial"]);
      setPositiveKeywords([]);
      setLocationAllocations([
        { country: "CO", region: "Antioquia", city: "Medellín", allocated_leads: 10 },
      ]);
      dispatch(selectCity("Medellín"));
      return;
    }

    const preset = PRESET_TEMPLATES.find((p) => p.id === presetId);
    if (preset) {
      setOfferDescription(preset.offerDescription);
      setSelectedSectors(preset.sectors);
      setTargetRoles(preset.roles);
      setPositiveKeywords(preset.keywords);
      setLocationAllocations(preset.locations);
      dispatch(selectCity(preset.defaultCity));
      if (preset.currency && preset.currency !== currency) {
        dispatch(setCurrency(preset.currency));
      }
      const sum = preset.locations.reduce((acc, curr) => acc + curr.allocated_leads, 0);
      dispatch(setVolume(sum));
    }
  };

  const [createCustomTaxonomy] = useCreateCustomTaxonomyMutation();

  const handleRolesChange = (newRoles: string[]) => {
    setTargetRoles(newRoles);
    // Auto-record and persist newly added roles in taxonomy
    const addedRole = newRoles.find((r) => !targetRoles.includes(r));
    if (addedRole) {
      recordRoleUsage({ role_title: addedRole }).catch(() => {});
      createCustomTaxonomy({ type: "role", name: addedRole }).catch(() => {});
    }
  };

  const handleKeywordsSuggested = (keywords: string[]) => {
    const merged = Array.from(new Set([...positiveKeywords, ...keywords]));
    setPositiveKeywords(merged);
  };

  const handleLocationsChange = (newLocations: LocationAllocationPayload[]) => {
    setLocationAllocations(newLocations);
    const sum = newLocations.reduce((acc, curr) => acc + curr.allocated_leads, 0);
    if (sum > 0 && sum !== volume) {
      dispatch(setVolume(sum));
    }
  };

  const handleTotalVolumeChange = (newTotal: number) => {
    dispatch(setVolume(newTotal));
  };

  const handleProfileIntent = async (overrideQuery?: string) => {
    const q = (overrideQuery || aiQuery).trim();
    if (!q) return;
    setFormError(null);
    try {
      const res = await profileIntentMutation({ query: q }).unwrap();
      if (res && res.status === "success") {
        setDiscoveryResult(res);
        setOfferDescription(q);
        if (res.matched_keywords && res.matched_keywords.length > 0) {
          setPositiveKeywords(res.matched_keywords);
        }
        if (res.city) {
          dispatch(selectCity(res.city));
          setLocationAllocations([
            {
              country: res.country || "CO",
              region: res.city,
              city: res.city,
              allocated_leads: res.recommended_limit || 25,
            },
          ]);
        }
        const safeTier = (res.recommended_tier === 1 || res.recommended_tier === 3
          ? res.recommended_tier
          : 2) as 1 | 2 | 3;
        dispatch(setTier(safeTier));
        dispatch(setVolume(res.recommended_limit || 25));
      }
    } catch (err: any) {
      console.warn("AI Intent discovery error:", err);
    }
  };

  const handleProceedToStep2 = () => {
    if (!offerDescription.trim() && selectedPresetId === "custom") {
      setFormError("Por favor ingresa una breve descripción de tu oferta comercial o producto.");
      return;
    }
    if (locationAllocations.length === 0) {
      setFormError("Por favor asigna al menos un territorio o ciudad con cuota de prospectos.");
      return;
    }
    setFormError(null);
    setCurrentStep(2);
  };

  const formatCop = (val: number) => {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      maximumFractionDigits: 0,
    }).format(val);
  };

  const parsedBulkExclusions = exclusionsText
    .split(/[\n,;]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);

  const allExclusions = Array.from(new Set([...negativeExclusions, ...parsedBulkExclusions]));

  const handleSubmitOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!buyerName.trim() || !buyerEmail.trim()) {
      setFormError("Por favor completa tu nombre y correo corporativo.");
      return;
    }

    dispatch(setBuyerInfo({ name: buyerName, email: buyerEmail, phone: buyerPhone }));
    dispatch(startOrderSubmission());

    try {
      const isMulti = locationAllocations.some((l) => l.country !== locationAllocations[0]?.country);
      const primaryCountry = isMulti ? "MULTI" : (locationAllocations[0]?.country || "CO");
      const primaryCity = locationAllocations.map((a) => a.city).join(", ") || "Medellín";

      const payload: CreateOrderPayload = {
        client: {
          name: buyerName,
          email: buyerEmail,
          phone: buyerPhone || "+573000000000",
          channel: "web_portal",
          referral_partner: partner.isAffiliate ? partner.partnerId : "direct",
        },
        request: {
          campaign_id: selectedPresetId !== "custom" ? selectedPresetId : "universal_prospecting",
          country: primaryCountry,
          city: primaryCity,
          limit: volume,
          tier: tier,
          offer_description: offerDescription || undefined,
          target_roles: targetRoles.length > 0 ? targetRoles : undefined,
          target_ciiu_codes: undefined,
          sector: selectedSectors.length > 0 ? selectedSectors.join(", ") : undefined,
          location_allocations: locationAllocations.length > 0 ? locationAllocations : undefined,
          keywords_include: positiveKeywords.length > 0 ? positiveKeywords : undefined,
          keywords_exclude: allExclusions.length > 0 ? allExclusions : undefined,
          exclusions: allExclusions.length > 0 ? allExclusions : undefined,
          directionality: directionality,
          rfq_specifications: directionality === "client_to_vendors" && rfqSpecifications.trim() ? rfqSpecifications.trim() : undefined,
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

  const handleShareQuote = async () => {
    setFormError(null);
    setQuoteSharedToast(null);

    if (!buyerName.trim() || !buyerEmail.trim()) {
      setFormError("Por favor completa tu nombre y correo corporativo antes de compartir la cotización.");
      return;
    }

    setIsSharingQuote(true);
    dispatch(setBuyerInfo({ name: buyerName, email: buyerEmail, phone: buyerPhone }));
    dispatch(startOrderSubmission());

    try {
      const isMulti = locationAllocations.some((l) => l.country !== locationAllocations[0]?.country);
      const primaryCountry = isMulti ? "MULTI" : (locationAllocations[0]?.country || "CO");
      const primaryCity = locationAllocations.map((a) => a.city).join(", ") || "Medellín";

      const payload: CreateOrderPayload = {
        client: {
          name: buyerName,
          email: buyerEmail,
          phone: buyerPhone || "+573000000000",
          channel: "web_portal",
          referral_partner: partner.isAffiliate ? partner.partnerId : "direct",
        },
        request: {
          campaign_id: selectedPresetId !== "custom" ? selectedPresetId : "universal_prospecting",
          country: primaryCountry,
          city: primaryCity,
          limit: volume,
          tier: tier,
          offer_description: offerDescription || undefined,
          target_roles: targetRoles.length > 0 ? targetRoles : undefined,
          target_ciiu_codes: undefined,
          sector: selectedSectors.length > 0 ? selectedSectors.join(", ") : undefined,
          location_allocations: locationAllocations.length > 0 ? locationAllocations : undefined,
          keywords_include: positiveKeywords.length > 0 ? positiveKeywords : undefined,
          keywords_exclude: allExclusions.length > 0 ? allExclusions : undefined,
          exclusions: allExclusions.length > 0 ? allExclusions : undefined,
          directionality: directionality,
          rfq_specifications: directionality === "client_to_vendors" && rfqSpecifications.trim() ? rfqSpecifications.trim() : undefined,
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
        const shareUrl = `${window.location.origin}/rastrear?order_id=${res.order_id}`;
        if (navigator?.clipboard) {
          navigator.clipboard.writeText(shareUrl);
        }
        setQuoteSharedToast("¡Cotización generada y guardada! Enlace copiado al portapapeles para aprobación interna.");
        setTimeout(() => {
          document.querySelector(".generator-tracker-area")?.scrollIntoView({ behavior: "smooth" });
        }, 300);
      } else {
        dispatch(orderFailed(res.message || "No se pudo crear la cotización."));
      }
    } catch (err: any) {
      const msg = err?.data?.detail || "Error al generar la cotización.";
      setFormError(msg);
      dispatch(orderFailed(msg));
    } finally {
      setIsSharingQuote(false);
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
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: "50%",
                      backgroundColor: "#34d399",
                    }}
                  />
                  <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "#fff" }}>
                    Prospección activa:{" "}
                    <strong style={{ fontFamily: "monospace", color: "#38bdf8" }}>
                      {activeOrderId}
                    </strong>
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <button
                    type="button"
                    onClick={() => {
                      document
                        .querySelector(".generator-tracker-area")
                        ?.scrollIntoView({ behavior: "smooth" });
                    }}
                    className="active-order-action-link"
                  >
                    Ver Estado
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (
                        window.confirm(
                          "¿Deseas iniciar una nueva búsqueda? Tu orden anterior no se borrará."
                        )
                      ) {
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
                      <span className="partner-notice-text">
                        Alianza Oficial: <strong>{partner.name}</strong>
                      </span>
                      {partner.discountRate > 0 && (
                        <span className="partner-notice-discount">
                          • {(partner.discountRate * 100).toFixed(0)}% dto. preferencial aplicado
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Directionality Switcher: Vender vs Comprar / Cotizar */}
                <div style={{ marginBottom: "16px" }}>
                  <div style={{ display: "flex", gap: "8px", background: "rgba(15, 23, 42, 0.6)", padding: "4px", borderRadius: "10px", border: "1px solid rgba(255, 255, 255, 0.08)" }}>
                    <button
                      type="button"
                      onClick={() => setDirectionality("vendor_to_clients")}
                      style={{
                        flex: 1,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "8px",
                        padding: "10px 14px",
                        borderRadius: "8px",
                        border: "none",
                        cursor: "pointer",
                        fontSize: "0.85rem",
                        fontWeight: 600,
                        background: directionality === "vendor_to_clients" ? "linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%)" : "transparent",
                        color: directionality === "vendor_to_clients" ? "#ffffff" : "var(--text-muted)",
                        transition: "all 0.2s ease",
                      }}
                    >
                      <TrendingUp style={{ width: 16, height: 16 }} />
                      <span>Quiero Vender (Captar Clientes B2B)</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setDirectionality("client_to_vendors");
                        if (targetRoles.length === 0 || targetRoles.includes("Director de Operaciones")) {
                          setTargetRoles(["Director Comercial", "Gerente Comercial", "Gerente de Ventas", "Gerente General"]);
                        }
                      }}
                      style={{
                        flex: 1,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "8px",
                        padding: "10px 14px",
                        borderRadius: "8px",
                        border: "none",
                        cursor: "pointer",
                        fontSize: "0.85rem",
                        fontWeight: 600,
                        background: directionality === "client_to_vendors" ? "linear-gradient(135deg, #059669 0%, #10b981 100%)" : "transparent",
                        color: directionality === "client_to_vendors" ? "#ffffff" : "var(--text-muted)",
                        transition: "all 0.2s ease",
                      }}
                    >
                      <ShoppingCart style={{ width: 16, height: 16 }} />
                      <span>Quiero Comprar (Cotizar Proveedores / Auto-RFQ)</span>
                    </button>
                  </div>
                </div>

                {/* Mode Switcher Tabs */}
                <div className="generator-mode-tabs">
                  <button
                    type="button"
                    onClick={() => setSearchMode("direct")}
                    className={`generator-mode-tab ${searchMode === "direct" ? "active" : ""}`}
                  >
                    <SlidersHorizontal style={{ width: 14, height: 14 }} />
                    <span>Configuración Avanzada del Lote</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setSearchMode("ai")}
                    className={`generator-mode-tab ${searchMode === "ai" ? "active" : ""}`}
                  >
                    <Sparkles style={{ width: 14, height: 14, color: "#38bdf8" }} />
                    <span>Búsqueda con IA (Michito Engine™)</span>
                  </button>
                </div>

                {searchMode === "ai" ? (
                  /* AI Natural Language Intent Hero */
                  <div className="ai-intent-hero">
                    <div className="ai-intent-header">
                      <span className="ai-intent-badge">
                        <Sparkles style={{ width: 14, height: 14, color: "#38bdf8" }} />
                        Michito Intent Engine™
                      </span>
                      <h3 className="ai-intent-title">¿A qué empresas le quieres vender hoy?</h3>
                      <p className="ai-intent-subtitle">
                        Describe tu oferta o cliente ideal en lenguaje natural. Nuestra IA extraerá
                        sectores, cargos y configurará el lote óptimo en tiempo real.
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
                        placeholder="Ej: Vendo software contable a clínicas y firmas de consultoría en Bogotá y Cali..."
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
                            <Sparkles style={{ width: 16, height: 16 }} />
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
                          {
                            label: "Oficinas & Sedes Corporativas (Medellín)",
                            query:
                              "Busco empresas medianas y corporativas para arriendo de oficinas y coworking en Medellín",
                          },
                          {
                            label: "Logística y Flotas Pesadas (Bogotá)",
                            query:
                              "Empresas de transporte de carga pesada y distribución logística en Bogotá para suministro de combustible",
                          },
                          {
                            label: "Software & Facturación DIAN (Bogotá)",
                            query:
                              "Clínicas, IPS y empresas de servicios en Bogotá con facturación electrónica DIAN",
                          },
                          {
                            label: "Bodegas y Parques Industriales (Cali)",
                            query:
                              "Empresas buscando bodegas y centros de distribución logística en parques industriales en Cali",
                          },
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
                              <CheckCircle2 style={{ width: 16, height: 16 }} />
                              {discoveryResult.estimated_matches} Empresas Encontradas en{" "}
                              {discoveryResult.city}
                            </span>
                            <p style={{ fontSize: "0.8rem", color: "#cbd5e1", marginTop: "4px" }}>
                              {discoveryResult.summary_message}
                            </p>
                          </div>
                          <div style={{ textAlign: "right" }}>
                            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block" }}>
                              Lote Sugerido:
                            </span>
                            <strong style={{ fontSize: "0.9rem", color: "#34d399" }}>
                              {discoveryResult.recommended_limit} Contactos Directos (
                              {formatCop(discoveryResult.pricing?.total_cop || 0)} COP)
                            </strong>
                          </div>
                        </div>

                        {discoveryResult.sample_preview && (
                          <div className="discovery-sample-preview">
                            <div className="discovery-sample-title">
                              Ejemplo de cuenta calificada en este lote:
                            </div>
                            <div className="discovery-sample-company">
                              {discoveryResult.sample_preview.company_name}
                            </div>
                            <div className="discovery-sample-person">
                              {discoveryResult.sample_preview.masked_decision_maker} (
                              {discoveryResult.sample_preview.title})
                            </div>
                            <div className="discovery-sample-badges">
                              <span className="discovery-sample-badge">✓ NIT Vigente en Cámara de Comercio</span>
                              <span className="discovery-sample-badge">✓ Mailbox MX Corporativo Verificado</span>
                              <span className="discovery-sample-badge">✓ Huella HTTP y Dominio Activo</span>
                            </div>
                          </div>
                        )}

                        <div style={{ display: "flex", gap: "10px", marginTop: "16px" }}>
                          <button
                            type="button"
                            onClick={() => setSearchMode("direct")}
                            className="preset-chip-btn"
                            style={{ flex: 1, justifyContent: "center", padding: "10px" }}
                          >
                            <SlidersHorizontal style={{ width: 14, height: 14 }} />
                            <span>Personalizar y Ajustar Filtros en Modo Avanzado →</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  /* Advanced Direct Selection Configuration */
                  <div className="direct-selection-wrapper">
                    {/* Preset Catalog / Template Selector Bar */}
                    <div className="preset-catalog-bar">
                      <div className="preset-catalog-header">
                        <span className="preset-catalog-title">
                          <Compass style={{ width: 15, height: 15, color: "#38bdf8" }} />
                          <span>Plantillas Rápidas o Búsqueda Libre:</span>
                        </span>
                        {selectedPresetId !== "custom" && (
                          <button
                            type="button"
                            onClick={() => handlePresetChange("custom")}
                            style={{
                              background: "transparent",
                              border: "none",
                              color: "var(--accent-blue)",
                              fontSize: "0.75rem",
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                              gap: "4px",
                            }}
                          >
                            <RotateCcw style={{ width: 12, height: 12 }} />
                            <span>Búsqueda Libre desde Cero</span>
                          </button>
                        )}
                      </div>

                      <div className="preset-pills-row">
                        <button
                          type="button"
                          onClick={() => handlePresetChange("custom")}
                          className={`preset-chip-btn universal-btn ${
                            selectedPresetId === "custom" ? "active" : ""
                          }`}
                        >
                          <Sparkles style={{ width: 14, height: 14 }} />
                          <span>Búsqueda Universal Libre</span>
                        </button>
                        {availablePresets.map((p: PresetTemplate) => (
                          <button
                            key={p.id}
                            type="button"
                            onClick={() => handlePresetChange(p.id)}
                            className={`preset-chip-btn ${
                              selectedPresetId === p.id ? "active" : ""
                            }`}
                          >
                            <span>{p.name}</span>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Offer Description Field */}
                    <div className="form-group">
                      <label className="form-label">
                        <FileText className={`form-label-icon ${directionality === "client_to_vendors" ? "text-emerald-400" : "text-sky-400"}`} />
                        <span>
                          {directionality === "client_to_vendors"
                            ? "Producto, Insumo o Servicio que Necesitas Cotizar / Contratar"
                            : "Propuesta de Valor u Oferta Comercial B2B"}
                        </span>
                      </label>
                      <textarea
                        rows={2}
                        value={offerDescription}
                        onChange={(e) => setOfferDescription(e.target.value)}
                        placeholder={
                          directionality === "client_to_vendors"
                            ? "Describe lo que deseas cotizar (ej: Reparación y mantenimiento locativo de silletería de oficina, suministro de dotaciones escolares, o compra mayorista de insumos)..."
                            : "Describe el producto o servicio que vendes (ej: Distribución mayorista de insumos médicos para clínicas, suministro de combustible diésel para flotas pesadas, o software de facturación)..."
                        }
                        className="form-textarea"
                      />
                      <span className="form-hint">
                        {directionality === "client_to_vendors"
                          ? "El motor identificará los proveedores registrados más sólidos en las cámaras de comercio y generará la solicitud de cotización formal (Auto-RFQ)."
                          : "Esta propuesta personaliza automáticamente las 5 cadencias de contacto (correos y notas de LinkedIn) que genera el motor para cada prospecto."}
                      </span>
                    </div>

                    {/* RFQ Specifications (Visible only in Procurement / Comprar mode) */}
                    {directionality === "client_to_vendors" && (
                      <div className="form-group">
                        <label className="form-label">
                          <FileText className="form-label-icon text-emerald-400" />
                          <span>Especificaciones Técnicas / Pliego del Requerimiento (Auto-RFQ)</span>
                        </label>
                        <textarea
                          rows={2}
                          value={rfqSpecifications}
                          onChange={(e) => setRfqSpecifications(e.target.value)}
                          placeholder="Requerimientos específicos (ej: Requerimos cotizar mantenimiento para 120 puestos de trabajo en Medellín con garantía de 12 meses y ejecución en enero)..."
                          className="form-textarea"
                          style={{ borderColor: "rgba(16, 185, 129, 0.4)" }}
                        />
                        <span className="form-hint" style={{ color: "#34d399" }}>
                          Estas especificaciones se insertarán automáticamente en la solicitud formal de cotización enviada a los directores comerciales de los proveedores calificados.
                        </span>
                      </div>
                    )}

                    {/* Macro-Sector & CIIU Code Selector */}
                    <div className="form-group">
                      <SectorSelector
                        selectedSectors={selectedSectors}
                        onChange={setSelectedSectors}
                        onKeywordsSuggested={handleKeywordsSuggested}
                      />
                    </div>

                    {/* Target Roles & Decision Makers */}
                    <div className="form-group">
                      <label className="form-label">
                        <Target className="form-label-icon text-indigo-400" />
                        <span>Cargos y Tomadores de Decisión Objetivo</span>
                      </label>
                      <TagPillInput
                        tags={targetRoles}
                        onChange={handleRolesChange}
                        suggestions={suggestedRoles}
                        color="indigo"
                        placeholder="Ej: Gerente General, Director de Compras, CFO..."
                        helperText="Escribe un cargo y presiona Enter o haz clic en las sugerencias frecuentes."
                      />
                      <div
                        style={{
                          display: "flex",
                          flexWrap: "wrap",
                          gap: "6px",
                          marginTop: "6px",
                        }}
                      >
                        <span style={{ fontSize: "0.72rem", color: "var(--text-dim)", alignSelf: "center" }}>
                          Sugerencias populares:
                        </span>
                        {[
                          "Gerente General",
                          "Director de Operaciones",
                          "Director de Compras",
                          "Director Comercial",
                          "Gerente Financiero (CFO)",
                          "Director de Tecnología (CTO)",
                        ].map((role) => (
                          <button
                            key={role}
                            type="button"
                            onClick={() => {
                              if (!targetRoles.includes(role)) {
                                handleRolesChange([...targetRoles, role]);
                              }
                            }}
                            className="tag-pill-add-action-btn"
                            style={{ opacity: targetRoles.includes(role) ? 0.4 : 1 }}
                            disabled={targetRoles.includes(role)}
                          >
                            + {role}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Multi-Territory Geo-Quota Allocator */}
                    <div className="form-group">
                      <label className="form-label">
                        <MapPin className="form-label-icon text-emerald-400" />
                        <span>Distribución Geográfica y Cuota de Leads</span>
                      </label>
                      <GeoQuotaAllocator
                        allocations={locationAllocations}
                        onChange={handleLocationsChange}
                        totalVolume={volume}
                        onTotalVolumeChange={handleTotalVolumeChange}
                      />
                    </div>

                    {/* Positive Keywords / Target Signals */}
                    <div className="form-group">
                      <label className="form-label">
                        <Sparkles className="form-label-icon text-emerald-400" />
                        <span>Palabras Clave y Señales de Compra (Inclusiones)</span>
                      </label>
                      <TagPillInput
                        tags={positiveKeywords}
                        onChange={setPositiveKeywords}
                        color="emerald"
                        placeholder="Ej: facturación electrónica, cadena de frío, transporte pesado..."
                        helperText="Señales técnicas o de actividad comercial que deben estar presentes en los registros o el sitio web."
                      />
                    </div>

                    {/* Enrichment Tier Selector */}
                    <div className="form-group">
                      <label className="form-label">
                        <Layers className="form-label-icon text-sky-400" />
                        <span>{g.tierLabel}</span>
                      </label>
                      <div className="tier-pills-selector">
                        <button
                          type="button"
                          onClick={() => dispatch(setTier(1))}
                          className={`tier-pill ${tier === 1 ? "active" : ""}`}
                        >
                          <div className="tier-pill-title-row">
                            <span className="tier-pill-name">Directorio Base</span>
                          </div>
                          <div className="tier-pill-price-row">
                            <span className="tier-pill-price">
                              {formatUnitCurrency(curConfig.tierPrices[1], currency)}
                            </span>
                            <span className="tier-pill-unit">/ cta</span>
                          </div>
                        </button>
                        <button
                          type="button"
                          onClick={() => dispatch(setTier(2))}
                          className={`tier-pill ${tier === 2 ? "active" : ""}`}
                        >
                          <div className="tier-pill-title-row">
                            <span className="tier-pill-name">Contactos Directos</span>
                            <span className="tier-pill-badge">Rec.</span>
                          </div>
                          <div className="tier-pill-price-row">
                            <span className="tier-pill-price">
                              {formatUnitCurrency(curConfig.tierPrices[2], currency)}
                            </span>
                            <span className="tier-pill-unit">/ cta</span>
                          </div>
                        </button>
                        <button
                          type="button"
                          onClick={() => dispatch(setTier(3))}
                          className={`tier-pill ${tier === 3 ? "active" : ""}`}
                        >
                          <div className="tier-pill-title-row">
                            <span className="tier-pill-name">Auditoría Completa</span>
                          </div>
                          <div className="tier-pill-price-row">
                            <span className="tier-pill-price">
                              {formatUnitCurrency(curConfig.tierPrices[3], currency)}
                            </span>
                            <span className="tier-pill-unit">/ cta</span>
                          </div>
                        </button>
                      </div>
                    </div>

                    {/* Volume Presets & Slider */}
                    <div className="form-group">
                      <label className="form-label">
                        <Hash className="form-label-icon text-purple-400" />
                        <span>
                          {g.volumeLabel}{" "}
                          <strong className="text-sky-400">{volume} cuentas</strong>
                        </span>
                      </label>
                      <div className="volume-presets-grid">
                        {[10, 25, 50, 100, 250, 500, 1000].map((v) => (
                          <button
                            key={v}
                            type="button"
                            onClick={() => {
                              dispatch(setVolume(v));
                              if (locationAllocations.length > 0) {
                                const perCity = Math.max(1, Math.round(v / locationAllocations.length));
                                const updated = locationAllocations.map((a, idx) => ({
                                  ...a,
                                  allocated_leads:
                                    idx === locationAllocations.length - 1
                                      ? Math.max(1, v - perCity * (locationAllocations.length - 1))
                                      : perCity,
                                }));
                                setLocationAllocations(updated);
                              }
                            }}
                            className={`preset-btn ${volume === v ? "active" : ""}`}
                          >
                            {v >= 1000 ? "1.000+" : v}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Collapsible Customer & Domain Exclusion Drawer */}
                <div className="exclusions-section" style={{ marginTop: "16px" }}>
                  <button
                    type="button"
                    onClick={() => setIsExclusionsOpen(!isExclusionsOpen)}
                    className="exclusions-toggle-btn"
                    aria-expanded={isExclusionsOpen}
                  >
                    <div className="exclusions-toggle-title">
                      <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span>Excluir Clientes Actuales o Competidores (Opcional)</span>
                      {allExclusions.length > 0 && (
                        <span className="exclusions-count-badge">
                          {allExclusions.length}{" "}
                          {allExclusions.length === 1
                            ? "exclusión activa"
                            : "exclusiones activas"}
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
                        Ingresa dominios web o NITs que desees omitir (ej: cliente1.com, 900123456).
                        Se excluirán automáticamente del lote sin costo alguno.
                      </p>

                      <TagPillInput
                        tags={negativeExclusions}
                        onChange={setNegativeExclusions}
                        color="rose"
                        placeholder="Escribe dominio o NIT y presiona Enter..."
                      />

                      <div style={{ marginTop: "10px" }}>
                        <span style={{ fontSize: "0.72rem", color: "var(--text-dim)", display: "block", marginBottom: "4px" }}>
                          O pega una lista en bloque (separada por comas o saltos de línea):
                        </span>
                        <textarea
                          value={exclusionsText}
                          onChange={(e) => setExclusionsText(e.target.value)}
                          placeholder="cliente1.com, 901234567, empresa.co..."
                          className="exclusions-textarea"
                          rows={2}
                        />
                      </div>
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
                      <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                        <Sparkles style={{ width: 14, height: 14 }} /> Descuento por volumen (-
                        {discountPercent}%):
                      </span>
                      <span>-{formatCurrencyAmount(subtotal - total, currency)}</span>
                    </div>
                  )}
                  <div className="calc-row-total">
                    <span>{g.summaryTotal}</span>
                    <span className="total-cop">{formatCurrencyAmount(total, currency)}</span>
                  </div>
                  {currency !== "COP" && (
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "4px", textAlign: "right" }}>
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
              /* Step 2: Buyer Delivery Info & Comprehensive Validation Recap */
              <form onSubmit={handleSubmitOrder} className="generator-step-2">
                <div className="card-header-box">
                  <h3 className="generator-card-title">2. {g.buyerSection}</h3>
                  <p className="generator-card-sub">{g.buyerSectionSub}</p>
                </div>

                {/* Selected Order Comprehensive Recap */}
                <div className="generator-recap-box">
                  <div className="recap-item">
                    <span className="recap-label">Oferta / Propuesta</span>
                    <span className="recap-value">
                      {offerDescription ? `"${offerDescription.slice(0, 80)}..."` : "Configuración Universal"}
                    </span>
                  </div>

                  <div className="recap-item">
                    <span className="recap-label">Sectores CIIU</span>
                    <span className="recap-value">
                      {selectedSectors.length > 0 ? selectedSectors.join(", ") : "Multi-Sector Abierto"}
                    </span>
                  </div>

                  <div className="recap-item">
                    <span className="recap-label">Cargos Objetivo</span>
                    <span className="recap-value" style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                      {targetRoles.map((r, i) => (
                        <span key={i} className="tag-pill-chip indigo" style={{ fontSize: "0.72rem" }}>
                          {r}
                        </span>
                      ))}
                    </span>
                  </div>

                  <div className="recap-item">
                    <span className="recap-label">Territorios & Cuota</span>
                    <span className="recap-value" style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                      {locationAllocations.map((loc, i) => (
                        <span key={i} style={{ color: "#34d399", fontWeight: 600 }}>
                          {loc.city}: {loc.allocated_leads} leads
                        </span>
                      ))}
                    </span>
                  </div>

                  {allExclusions.length > 0 && (
                    <div className="recap-item">
                      <span className="recap-label">Exclusiones Activas</span>
                      <span className="recap-value text-amber-300 font-medium">
                        {allExclusions.length}{" "}
                        {allExclusions.length === 1 ? "cuenta excluida" : "cuentas excluidas"}
                      </span>
                    </div>
                  )}

                  <div className="recap-item">
                    <span className="recap-label">Inversión Estimada</span>
                    <span className="recap-value text-emerald-400">
                      {formatCurrencyAmount(total, currency)} ({volume} cuentas)
                    </span>
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
                    type="button"
                    onClick={handleShareQuote}
                    disabled={isSubmitting || isSharingQuote}
                    className="generator-share-quote-btn"
                    style={{
                      padding: "10px 16px",
                      borderRadius: "12px",
                      border: "1px solid rgba(56, 189, 248, 0.4)",
                      background: "rgba(14, 165, 233, 0.12)",
                      color: "#38bdf8",
                      fontWeight: 600,
                      fontSize: "0.85rem",
                      cursor: isSubmitting || isSharingQuote ? "not-allowed" : "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      transition: "all 0.2s ease",
                    }}
                    title="Guarda la configuración y copia un enlace directo para que tu equipo o CFO pueda revisarla y autorizarla"
                  >
                    {isSharingQuote ? (
                      <Loader2 className="w-4 h-4 animate-spin text-sky-400" />
                    ) : (
                      <Share2 className="w-4 h-4 text-sky-400" />
                    )}
                    <span>Compartir para Aprobación</span>
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting || isSharingQuote}
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

                {quoteSharedToast && (
                  <div className="mt-3 p-3 rounded-xl bg-emerald-950/80 border border-emerald-500/50 text-emerald-300 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>{quoteSharedToast}</span>
                  </div>
                )}

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
    </section>
  );
};

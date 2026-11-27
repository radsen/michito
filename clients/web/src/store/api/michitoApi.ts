import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

export interface LocationAllocationPayload {
  country: string;
  region: string;
  city: string;
  allocated_leads: number;
}

export interface CreateOrderPayload {
  client: {
    name: string;
    email: string;
    phone?: string;
    channel?: string;
    referral_partner?: string;
  };
  request: {
    campaign_id?: string;
    country?: string;
    country_allocations?: Record<string, number>;
    location_allocations?: LocationAllocationPayload[];
    city?: string;
    limit: number;
    tier: number;
    currency?: string;
    segment?: string;
    sector?: string;
    offer_description?: string;
    target_roles?: string[];
    target_ciiu_codes?: string[];
    keywords_include?: string[];
    keywords_exclude?: string[];
    exclusions?: string[];
    directionality?: "vendor_to_clients" | "client_to_vendors";
    rfq_specifications?: string;
  };
}

export interface CreateOrderResponse {
  status: string;
  order_id: string;
  order_status: string;
  amount_in_cents?: number;
  amount_in_cents_cop?: number;
  total_price?: number;
  total_price_cop?: number;
  currency?: string;
  payment_currency?: string;
  exchange_rate?: number;
  message?: string;
}

export interface OrderStatusResponse {
  order_id: string;
  status: string;
  payment_status?: string;
  payment_currency?: string;
  currency?: string;
  limit?: number;
  total_qualified?: number;
  tier?: number;
  total_price_cop?: number;
  amount_in_cents?: number;
  amount_in_cents_cop?: number;
  exchange_rate?: number;
  client?: {
    name: string;
    email: string;
    phone?: string;
  };
  sample_leads?: Array<{
    company_name: string;
    nit?: string;
    decision_maker_name?: string;
    decision_maker_role?: string;
    email: string;
    phone?: string;
    intent_trigger?: string;
    solvency_tier?: string;
    underwriting_grade?: string;
    is_guarantee_replacement?: boolean;
  }>;
  replacement_claims?: Array<{
    claim_id: string;
    bounced_email: string;
    company_name?: string;
    reason?: string;
    claimed_at: string;
    replacement_count: number;
    replacement_leads: any[];
  }>;
  csv_download_url?: string;
  xlsx_download_url?: string;
  dossier_download_url?: string;
  pdf_download_url?: string;
  playbook?: any[];
  error_message?: string;
  created_at?: string;
  started_processing_at?: string;
  completed_at?: string;
  metrics?: {
    total_elapsed_seconds?: number;
    [key: string]: any;
  };
}

export interface PartnerProfile {
  partner_id: string;
  name: string;
  commission_rate: number;
  discount_rate: number;
  badge_text: string;
  default_campaign_id?: string;
  description?: string;
  active: boolean;
}

export interface PartnerResponse {
  status: string;
  partner: PartnerProfile;
}

export interface ReplacementClaimPayload {
  orderId: string;
  bounced_email: string;
  company_name?: string;
  reason?: string;
}

export interface ReplacementClaimResponse {
  status: string;
  message: string;
  claim_id: string;
  bounced_email: string;
  replacement_leads: any[];
  updated_total_leads: number;
}

export interface OrderQuoteResponse {
  status: string;
  order_id: string;
  shareable_url: string;
  order_status: string;
  created_at: string;
  client: {
    name: string;
    email: string;
    phone: string;
    channel: string;
  };
  scope: {
    campaign_id: string;
    offer_description: string;
    sectors: string;
    target_roles: string[];
    locations: Array<{ country?: string; region?: string; city: string; allocated_leads: number }>;
    total_leads: number;
    tier: number;
    tier_description: string;
    exclusions_count: number;
  };
  financials: {
    currency: string;
    amount_in_cents: number;
    total_price: number;
    unit_price: number;
    payment_status: string;
    guarantee: string;
  };
  is_approved_and_paid: boolean;
  sample_preview_count: number;
}

export interface ParseBriefPayload {
  prompt: string;
  client_id?: string;
  session_id?: string;
  force_fallback?: boolean;
}

export interface ProbeDepthPayload {
  prompt: string;
  country?: string;
  city?: string;
  explicit_directionality?: string;
}

export interface ProbeDepthResponse {
  status: string;
  target_city: string;
  country: string;
  sample_size: number;
  national_sample_size: number;
  recommended_max: number;
  is_sample_limited: boolean;
  advice_message: string;
  directionality: string;
  modality_label: string;
  ciiu_codes: string[];
  keywords: string[];
  detected_concept: string;
  business_understanding?: string;
}

export interface ParseBriefResponse {
  status: string;
  data: {
    query_id: string;
    directionality: "vendor_to_clients" | "client_to_vendors";
    sectors: string[];
    ciiu_codes: string[];
    roles: string[];
    locations: LocationAllocationPayload[];
    limit: number;
    tier: number;
    rfq_specifications?: string | null;
    keywords_include: string[];
    keywords_exclude: string[];
    discovered_tokens: Record<string, any>;
    confidence_score: number;
    source: string;
  };
}

export interface IntentProfileResponse {
  status: string;
  query: string;
  campaign_id: string;
  campaign_name: string;
  country: string;
  city: string;
  recommended_tier: number;
  recommended_limit: number;
  estimated_matches: number;
  matched_keywords: string[];
  directionality?: "vendor_to_clients" | "client_to_vendors";
  sectors?: string[];
  ciiu_codes?: string[];
  roles?: string[];
  locations?: LocationAllocationPayload[];
  rfq_specifications?: string | null;
  keywords_include?: string[];
  keywords_exclude?: string[];
  query_id?: string;
  sample_preview: {
    company_name: string;
    masked_nit: string;
    masked_decision_maker: string;
    title: string;
    masked_phone: string;
    masked_email: string;
    annual_revenue_range?: string;
    signals?: string;
    city?: string;
  };
  pricing: {
    tier: number;
    tier_name: string;
    unit_price_cop: number;
    volume: number;
    total_cop: number;
    currency: string;
    guarantee: string;
  };
  summary_message: string;
}

export interface TrmRatesResponse {
  status: string;
  base: string;
  rates_to_cop: Record<string, number>;
  trm_usd: number;
  trm_dop: number;
  timestamp: string;
}

export interface FxConvertResponse {
  status: string;
  from_currency: string;
  to_currency: string;
  original_amount: number;
  converted_amount: number;
  amount_in_cop: number;
  formatted: string;
  rate_used: number;
  trm_cop: number;
  timestamp: string;
}

export interface PricingCatalogResponse {
  status: string;
  currency: string;
  min_order_leads: number;
  tier_prices: Record<number, number>;
  tier_prices_cents: Record<number, number>;
  volume_discount_curve: Array<{ min_quantity: number; discount_percentage: number }>;
  products: any[];
}

export const michitoApi = createApi({
  reducerPath: "michitoApi",
  baseQuery: fetchBaseQuery({ baseUrl: "/api/v1" }),
  tagTypes: ["Campaigns", "Order", "Partner", "TaxonomySectors", "TaxonomyRoles"],
  endpoints: (builder) => ({
    getPricingCatalog: builder.query<PricingCatalogResponse, string | void>({
      query: (currency = "COP") => `/pricing/catalog?currency=${currency || "COP"}`,
    }),
    getCampaigns: builder.query<{ status: string; count: number; campaigns: any[] }, void>({
      query: () => "/campaigns",
      providesTags: ["Campaigns"],
    }),
    getPartner: builder.query<PartnerResponse, string>({
      query: (partnerId) => `/partners/${partnerId}`,
      providesTags: (_result, _error, partnerId) => [{ type: "Partner", id: partnerId }],
    }),
    profileIntent: builder.mutation<IntentProfileResponse, { query: string; country?: string }>({
      query: (body) => ({
        url: "/intent/profile",
        method: "POST",
        body,
      }),
    }),
    parseBrief: builder.mutation<ParseBriefResponse, ParseBriefPayload>({
      query: (body) => ({
        url: "/prospecting/parse-brief",
        method: "POST",
        body,
      }),
    }),
    probeDepth: builder.mutation<ProbeDepthResponse, ProbeDepthPayload>({
      query: (body) => ({
        url: "/prospecting/probe-depth",
        method: "POST",
        body,
      }),
    }),
    createOrder: builder.mutation<CreateOrderResponse, CreateOrderPayload>({
      query: (body) => ({
        url: "/orders",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Order"],
    }),
    getOrder: builder.query<OrderStatusResponse, string>({
      query: (orderId) => `/orders/${orderId}`,
      providesTags: (_result, _error, orderId) => [{ type: "Order", id: orderId }],
    }),
    getOrderQuote: builder.query<OrderQuoteResponse, string>({
      query: (orderId) => `/orders/${orderId}/quote`,
      providesTags: (_result, _error, orderId) => [{ type: "Order", id: orderId }],
    }),
    payOrder: builder.mutation<{ status: string; order: any }, string>({
      query: (orderId) => ({
        url: `/orders/${orderId}/pay`,
        method: "POST",
      }),
      invalidatesTags: (_result, _error, orderId) => [{ type: "Order", id: orderId }],
    }),
    claimLeadReplacement: builder.mutation<ReplacementClaimResponse, ReplacementClaimPayload>({
      query: ({ orderId, ...body }) => ({
        url: `/orders/${orderId}/claim-replacement`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_result, _error, { orderId }) => [{ type: "Order", id: orderId }],
    }),
    getCampaignPresets: builder.query<{ status: string; total: number; presets: any[] }, void>({
      query: () => "/campaigns/presets",
    }),
    searchLocations: builder.query<{ status: string; total: number; locations: any[] }, { q?: string; country?: string; limit?: number }>({
      query: ({ q = "", country, limit = 20 }) => {
        const params = new URLSearchParams();
        if (q) params.append("q", q);
        if (country) params.append("country", country);
        if (limit) params.append("limit", limit.toString());
        return `/taxonomy/locations?${params.toString()}`;
      },
    }),
    validateLocation: builder.query<{ status: string; is_supported: boolean; location?: any; message: string }, string>({
      query: (name) => `/taxonomy/locations/validate?name=${encodeURIComponent(name)}`,
    }),
    searchRoles: builder.query<{ status: string; total: number; roles: any[] }, { q?: string; domain?: string; country?: string; limit?: number }>({
      query: ({ q = "", domain, country, limit = 20 }) => {
        const params = new URLSearchParams();
        if (q) params.append("q", q);
        if (domain) params.append("domain", domain);
        if (country) params.append("country", country);
        if (limit) params.append("limit", limit.toString());
        return `/taxonomy/roles?${params.toString()}`;
      },
      providesTags: ["TaxonomyRoles"],
    }),
    recordRoleUsage: builder.mutation<{ status: string; message: string }, { role_title: string }>({
      query: (body) => ({
        url: "/taxonomy/roles/usage",
        method: "POST",
        body,
      }),
    }),
    searchSectors: builder.query<{ status: string; total: number; sectors: any[] }, { q?: string; limit?: number }>({
      query: ({ q = "", limit = 30 }) => {
        const params = new URLSearchParams();
        if (q) params.append("q", q);
        if (limit) params.append("limit", limit.toString());
        return `/taxonomy/sectors?${params.toString()}`;
      },
      providesTags: ["TaxonomySectors"],
    }),
    createCustomTaxonomy: builder.mutation<
      { status: string; type: string; item: any },
      {
        type: "sector" | "role";
        name: string;
        country_code?: string;
        ciiu_codes?: string[];
        keywords?: string[];
        domain?: string;
        seniority?: string;
      }
    >({
      query: (body) => ({
        url: "/taxonomy/custom",
        method: "POST",
        body,
      }),
      invalidatesTags: (_result, _error, arg) =>
        arg.type === "sector" ? ["TaxonomySectors"] : ["TaxonomyRoles"],
    }),
    getTrmRates: builder.query<TrmRatesResponse, void>({
      query: () => "/fx/trm",
    }),
    convertFx: builder.query<FxConvertResponse, { amount: number; from?: string; to?: string }>({
      query: (params) => ({
        url: "/fx/convert",
        params: {
          amount: params.amount,
          from: params.from || "COP",
          to: params.to || "COP",
        },
      }),
    }),
  }),
});

export const {
  useGetPricingCatalogQuery,
  useLazyGetPricingCatalogQuery,
  useGetCampaignsQuery,
  useGetPartnerQuery,
  useLazyGetPartnerQuery,
  useProfileIntentMutation,
  useParseBriefMutation,
  useProbeDepthMutation,
  useCreateOrderMutation,
  useGetOrderQuery,
  useGetOrderQuoteQuery,
  useLazyGetOrderQuoteQuery,
  usePayOrderMutation,
  useClaimLeadReplacementMutation,
  useGetCampaignPresetsQuery,
  useSearchLocationsQuery,
  useLazySearchLocationsQuery,
  useValidateLocationQuery,
  useLazyValidateLocationQuery,
  useSearchRolesQuery,
  useLazySearchRolesQuery,
  useRecordRoleUsageMutation,
  useSearchSectorsQuery,
  useLazySearchSectorsQuery,
  useCreateCustomTaxonomyMutation,
  useGetTrmRatesQuery,
  useLazyGetTrmRatesQuery,
  useLazyConvertFxQuery,
} = michitoApi;


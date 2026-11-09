import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

export interface CreateOrderPayload {
  client: {
    name: string;
    email: string;
    phone?: string;
    channel?: string;
    referral_partner?: string;
  };
  request: {
    campaign_id: string;
    country?: string;
    city?: string;
    limit: number;
    tier: number;
    segment?: string;
  };
}

export interface CreateOrderResponse {
  status: string;
  order_id: string;
  order_status: string;
  amount_in_cents?: number;
  total_price_cop?: number;
  message?: string;
}

export interface OrderStatusResponse {
  order_id: string;
  status: string;
  payment_status?: string;
  limit?: number;
  tier?: number;
  total_price_cop?: number;
  amount_in_cents?: number;
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
  }>;
  csv_download_url?: string;
  dossier_download_url?: string;
  error_message?: string;
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

export const michitoApi = createApi({
  reducerPath: "michitoApi",
  baseQuery: fetchBaseQuery({ baseUrl: "/api/v1" }),
  tagTypes: ["Campaigns", "Order", "Partner"],
  endpoints: (builder) => ({
    getCampaigns: builder.query<{ status: string; count: number; campaigns: any[] }, void>({
      query: () => "/campaigns",
      providesTags: ["Campaigns"],
    }),
    getPartner: builder.query<PartnerResponse, string>({
      query: (partnerId) => `/partners/${partnerId}`,
      providesTags: (_result, _error, partnerId) => [{ type: "Partner", id: partnerId }],
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
    payOrder: builder.mutation<{ status: string; order: any }, string>({
      query: (orderId) => ({
        url: `/orders/${orderId}/pay`,
        method: "POST",
      }),
      invalidatesTags: (_result, _error, orderId) => [{ type: "Order", id: orderId }],
    }),
  }),
});

export const {
  useGetCampaignsQuery,
  useGetPartnerQuery,
  useLazyGetPartnerQuery,
  useCreateOrderMutation,
  useGetOrderQuery,
  usePayOrderMutation,
} = michitoApi;


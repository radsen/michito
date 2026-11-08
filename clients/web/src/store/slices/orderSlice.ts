import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface TeaserLead {
  company_name: string;
  nit?: string;
  decision_maker_name?: string;
  decision_maker_role?: string;
  email: string;
  phone?: string;
  intent_trigger?: string;
  solvency_tier?: string;
  underwriting_grade?: string;
}

export interface OrderState {
  buyerName: string;
  buyerEmail: string;
  buyerPhone: string;
  activeOrderId: string | null;
  orderStatus: "idle" | "submitting" | "queued" | "processing" | "awaiting_payment" | "paid" | "error";
  errorMessage: string | null;
  totalLeadsTarget: number;
  teaserLeads: TeaserLead[];
  totalAmountInCents: number;
  csvDownloadUrl: string | null;
  dossierDownloadUrl: string | null;
}

const initialState: OrderState = {
  buyerName: "",
  buyerEmail: "",
  buyerPhone: "",
  activeOrderId: null,
  orderStatus: "idle",
  errorMessage: null,
  totalLeadsTarget: 25,
  teaserLeads: [],
  totalAmountInCents: 0,
  csvDownloadUrl: null,
  dossierDownloadUrl: null,
};

export const orderSlice = createSlice({
  name: "order",
  initialState,
  reducers: {
    setBuyerInfo: (
      state,
      action: PayloadAction<{ name: string; email: string; phone: string }>
    ) => {
      state.buyerName = action.payload.name;
      state.buyerEmail = action.payload.email;
      state.buyerPhone = action.payload.phone;
    },
    startOrderSubmission: (state) => {
      state.orderStatus = "submitting";
      state.errorMessage = null;
    },
    orderCreatedSuccess: (
      state,
      action: PayloadAction<{ orderId: string; status: string; totalAmountInCents: number }>
    ) => {
      state.activeOrderId = action.payload.orderId;
      state.orderStatus = (action.payload.status as any) || "queued";
      state.totalAmountInCents = action.payload.totalAmountInCents;
    },
    updateOrderStatus: (
      state,
      action: PayloadAction<{
        status: string;
        teaserLeads?: TeaserLead[];
        csvUrl?: string;
        dossierUrl?: string;
      }>
    ) => {
      state.orderStatus = action.payload.status as any;
      if (action.payload.teaserLeads && action.payload.teaserLeads.length > 0) {
        state.teaserLeads = action.payload.teaserLeads;
      }
      if (action.payload.csvUrl) {
        state.csvDownloadUrl = action.payload.csvUrl;
      }
      if (action.payload.dossierUrl) {
        state.dossierDownloadUrl = action.payload.dossierUrl;
      }
    },
    orderFailed: (state, action: PayloadAction<string>) => {
      state.orderStatus = "error";
      state.errorMessage = action.payload;
    },
    resetOrder: (state) => {
      state.activeOrderId = null;
      state.orderStatus = "idle";
      state.errorMessage = null;
      state.teaserLeads = [];
      state.csvDownloadUrl = null;
      state.dossierDownloadUrl = null;
    },
  },
});

export const {
  setBuyerInfo,
  startOrderSubmission,
  orderCreatedSuccess,
  updateOrderStatus,
  orderFailed,
  resetOrder,
} = orderSlice.actions;

export default orderSlice.reducer;


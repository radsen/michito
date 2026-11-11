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
  orderStatus: "idle" | "submitting" | "queued" | "processing" | "awaiting_payment" | "paid" | "failed" | "error";
  errorMessage: string | null;
  totalLeadsTarget: number;
  teaserLeads: TeaserLead[];
  totalAmountInCents: number;
  csvDownloadUrl: string | null;
  xlsxDownloadUrl: string | null;
  dossierDownloadUrl: string | null;
  pdfDownloadUrl: string | null;
  playbook: any[];
}

function getInitialActiveOrderId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const urlParams = new URLSearchParams(window.location.search);
    const fromUrl = urlParams.get("order_id");
    if (fromUrl && fromUrl.startsWith("ord_")) {
      return fromUrl;
    }
    // Note: Do NOT auto-load past orders from localStorage on cold page visits.
    // Customers must always land on a clean purchase generator first (like DHL/FedEx).
    // They can look up an existing order anytime via the tracking search bar or direct link.
  } catch (e) {
    // Graceful fallback if localStorage is disabled
  }
  return null;
}

const initialOrderId = getInitialActiveOrderId();

const initialState: OrderState = {
  buyerName: typeof window !== "undefined" ? localStorage.getItem("michito_buyer_name") || "" : "",
  buyerEmail: typeof window !== "undefined" ? localStorage.getItem("michito_buyer_email") || "" : "",
  buyerPhone: typeof window !== "undefined" ? localStorage.getItem("michito_buyer_phone") || "" : "",
  activeOrderId: initialOrderId,
  orderStatus: initialOrderId ? "queued" : "idle",
  errorMessage: null,
  totalLeadsTarget: 25,
  teaserLeads: [],
  totalAmountInCents: 0,
  csvDownloadUrl: null,
  xlsxDownloadUrl: null,
  dossierDownloadUrl: null,
  pdfDownloadUrl: null,
  playbook: [],
};

function syncUrlWithOrderId(orderId: string | null) {
  if (typeof window === "undefined") return;
  try {
    const url = new URL(window.location.href);
    if (orderId) {
      url.searchParams.set("order_id", orderId);
      sessionStorage.setItem("michito_session_order_id", orderId);
    } else {
      url.searchParams.delete("order_id");
      sessionStorage.removeItem("michito_session_order_id");
      localStorage.removeItem("michito_active_order_id");
    }
    window.history.replaceState({}, "", url.toString());
  } catch (e) {
    // Ignore history API errors in tests/embedded
  }
}

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
      if (typeof window !== "undefined") {
        try {
          localStorage.setItem("michito_buyer_name", action.payload.name);
          localStorage.setItem("michito_buyer_email", action.payload.email);
          localStorage.setItem("michito_buyer_phone", action.payload.phone);
        } catch (e) {
          // ignore
        }
      }
    },
    startOrderSubmission: (state) => {
      state.orderStatus = "submitting";
      state.errorMessage = null;
    },
    orderCreatedSuccess: (
      state,
      action: PayloadAction<{
        orderId: string;
        status: string;
        totalAmountInCents: number;
        totalLeadsTarget?: number;
      }>
    ) => {
      state.activeOrderId = action.payload.orderId;
      state.orderStatus = (action.payload.status as any) || "queued";
      state.totalAmountInCents = action.payload.totalAmountInCents;
      if (action.payload.totalLeadsTarget && action.payload.totalLeadsTarget > 0) {
        state.totalLeadsTarget = action.payload.totalLeadsTarget;
      }
      syncUrlWithOrderId(action.payload.orderId);
    },
    restoreOrder: (state, action: PayloadAction<string>) => {
      state.activeOrderId = action.payload;
      state.orderStatus = "queued";
      state.errorMessage = null;
      syncUrlWithOrderId(action.payload);
    },
    updateOrderStatus: (
      state,
      action: PayloadAction<{
        status: string;
        teaserLeads?: TeaserLead[];
        csvUrl?: string;
        xlsxUrl?: string;
        dossierUrl?: string;
        pdfUrl?: string;
        playbook?: any[];
        totalAmountInCents?: number;
        totalLeadsTarget?: number;
      }>
    ) => {
      state.orderStatus = action.payload.status as any;
      if (action.payload.teaserLeads && action.payload.teaserLeads.length > 0) {
        state.teaserLeads = action.payload.teaserLeads;
      }
      if (action.payload.csvUrl) {
        state.csvDownloadUrl = action.payload.csvUrl;
      }
      if (action.payload.xlsxUrl) {
        state.xlsxDownloadUrl = action.payload.xlsxUrl;
      }
      if (action.payload.dossierUrl) {
        state.dossierDownloadUrl = action.payload.dossierUrl;
      }
      if (action.payload.pdfUrl) {
        state.pdfDownloadUrl = action.payload.pdfUrl;
      }
      if (action.payload.playbook && action.payload.playbook.length > 0) {
        state.playbook = action.payload.playbook;
      }
      if (action.payload.totalAmountInCents && action.payload.totalAmountInCents > 0) {
        state.totalAmountInCents = action.payload.totalAmountInCents;
      }
      if (action.payload.totalLeadsTarget && action.payload.totalLeadsTarget > 0) {
        state.totalLeadsTarget = action.payload.totalLeadsTarget;
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
      state.xlsxDownloadUrl = null;
      state.dossierDownloadUrl = null;
      state.pdfDownloadUrl = null;
      state.playbook = [];
      syncUrlWithOrderId(null);
    },
  },
});

export const {
  setBuyerInfo,
  startOrderSubmission,
  orderCreatedSuccess,
  restoreOrder,
  updateOrderStatus,
  orderFailed,
  resetOrder,
} = orderSlice.actions;

export default orderSlice.reducer;

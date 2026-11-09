import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface PartnerState {
  partnerId: string;
  name: string;
  commissionRate: number;
  discountRate: number;
  badgeText: string;
  defaultCampaignId?: string;
  description?: string;
  isAffiliate: boolean;
}

const initialState: PartnerState = {
  partnerId: "direct",
  name: "Direct",
  commissionRate: 0.0,
  discountRate: 0.0,
  badgeText: "",
  defaultCampaignId: undefined,
  description: "",
  isAffiliate: false,
};

export const partnerSlice = createSlice({
  name: "partner",
  initialState,
  reducers: {
    setPartner: (
      state,
      action: PayloadAction<{
        partnerId: string;
        name: string;
        commissionRate: number;
        discountRate: number;
        badgeText: string;
        defaultCampaignId?: string;
        description?: string;
      }>
    ) => {
      state.partnerId = action.payload.partnerId;
      state.name = action.payload.name;
      state.commissionRate = action.payload.commissionRate;
      state.discountRate = action.payload.discountRate;
      state.badgeText = action.payload.badgeText;
      state.defaultCampaignId = action.payload.defaultCampaignId;
      state.description = action.payload.description;
      state.isAffiliate = action.payload.partnerId !== "direct" && Boolean(action.payload.partnerId);
    },
    clearPartner: (state) => {
      state.partnerId = "direct";
      state.name = "Direct";
      state.commissionRate = 0.0;
      state.discountRate = 0.0;
      state.badgeText = "";
      state.defaultCampaignId = undefined;
      state.description = "";
      state.isAffiliate = false;
    },
  },
});

export const { setPartner, clearPartner } = partnerSlice.actions;
export default partnerSlice.reducer;


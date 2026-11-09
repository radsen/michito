import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface PricingState {
  tier: 1 | 2 | 3;
  volume: number;
  unitPriceCop: number;
  discountPercent: number;
  partnerDiscountPercent: number;
  partnerDiscountRate: number;
  subtotalCop: number;
  totalCop: number;
}

const TIER_PRICES: Record<1 | 2 | 3, number> = {
  1: 5000,
  2: 30000,
  3: 65000,
};

function calculatePricing(tier: 1 | 2 | 3, volume: number, partnerDiscountRate: number = 0.0) {
  const unitPrice = TIER_PRICES[tier] || 30000;
  const subtotal = unitPrice * volume;

  let volumeDiscount = 0;
  if (volume >= 500) {
    volumeDiscount = 0.20;
  } else if (volume >= 100) {
    volumeDiscount = 0.10;
  } else if (volume >= 50) {
    volumeDiscount = 0.05;
  }

  const combinedDiscount = Math.min(0.50, volumeDiscount + partnerDiscountRate);
  const total = Math.round(subtotal * (1 - combinedDiscount));

  return {
    unitPriceCop: unitPrice,
    discountPercent: Math.round(combinedDiscount * 100),
    partnerDiscountPercent: Math.round(partnerDiscountRate * 100),
    partnerDiscountRate,
    subtotalCop: subtotal,
    totalCop: total,
  };
}

const initialCalc = calculatePricing(2, 25, 0.0);

const initialState: PricingState = {
  tier: 2,
  volume: 25,
  ...initialCalc,
};

export const pricingSlice = createSlice({
  name: "pricing",
  initialState,
  reducers: {
    setTier: (state, action: PayloadAction<1 | 2 | 3>) => {
      state.tier = action.payload;
      const calc = calculatePricing(state.tier, state.volume, state.partnerDiscountRate);
      state.unitPriceCop = calc.unitPriceCop;
      state.discountPercent = calc.discountPercent;
      state.partnerDiscountPercent = calc.partnerDiscountPercent;
      state.subtotalCop = calc.subtotalCop;
      state.totalCop = calc.totalCop;
    },
    setVolume: (state, action: PayloadAction<number>) => {
      state.volume = action.payload;
      const calc = calculatePricing(state.tier, state.volume, state.partnerDiscountRate);
      state.unitPriceCop = calc.unitPriceCop;
      state.discountPercent = calc.discountPercent;
      state.partnerDiscountPercent = calc.partnerDiscountPercent;
      state.subtotalCop = calc.subtotalCop;
      state.totalCop = calc.totalCop;
    },
    setPartnerDiscountRate: (state, action: PayloadAction<number>) => {
      state.partnerDiscountRate = action.payload;
      const calc = calculatePricing(state.tier, state.volume, state.partnerDiscountRate);
      state.unitPriceCop = calc.unitPriceCop;
      state.discountPercent = calc.discountPercent;
      state.partnerDiscountPercent = calc.partnerDiscountPercent;
      state.subtotalCop = calc.subtotalCop;
      state.totalCop = calc.totalCop;
    },
  },
});

export const { setTier, setVolume, setPartnerDiscountRate } = pricingSlice.actions;
export default pricingSlice.reducer;

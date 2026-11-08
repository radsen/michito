import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface PricingState {
  tier: 1 | 2 | 3;
  volume: number;
  unitPriceCop: number;
  discountPercent: number;
  subtotalCop: number;
  totalCop: number;
}

const TIER_PRICES: Record<1 | 2 | 3, number> = {
  1: 5000,
  2: 30000,
  3: 65000,
};

function calculatePricing(tier: 1 | 2 | 3, volume: number) {
  const unitPrice = TIER_PRICES[tier] || 30000;
  const subtotal = unitPrice * volume;

  let discount = 0;
  if (volume >= 500) {
    discount = 0.20;
  } else if (volume >= 100) {
    discount = 0.10;
  } else if (volume >= 50) {
    discount = 0.05;
  }

  const total = Math.round(subtotal * (1 - discount));
  return {
    unitPriceCop: unitPrice,
    discountPercent: discount * 100,
    subtotalCop: subtotal,
    totalCop: total,
  };
}

const initialCalc = calculatePricing(2, 25);

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
      const calc = calculatePricing(state.tier, state.volume);
      state.unitPriceCop = calc.unitPriceCop;
      state.discountPercent = calc.discountPercent;
      state.subtotalCop = calc.subtotalCop;
      state.totalCop = calc.totalCop;
    },
    setVolume: (state, action: PayloadAction<number>) => {
      state.volume = action.payload;
      const calc = calculatePricing(state.tier, state.volume);
      state.unitPriceCop = calc.unitPriceCop;
      state.discountPercent = calc.discountPercent;
      state.subtotalCop = calc.subtotalCop;
      state.totalCop = calc.totalCop;
    },
  },
});

export const { setTier, setVolume } = pricingSlice.actions;
export default pricingSlice.reducer;


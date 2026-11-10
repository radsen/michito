import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { SupportedCurrency, SUPPORTED_CURRENCIES, DEFAULT_CURRENCY } from "../../config/currencies";

export interface PricingState {
  tier: 1 | 2 | 3;
  volume: number;
  currency: SupportedCurrency;
  unitPrice: number;
  unitPriceCop: number;
  subtotal: number;
  subtotalCop: number;
  total: number;
  totalCop: number;
  discountPercent: number;
  partnerDiscountPercent: number;
  partnerDiscountRate: number;
}

function calculatePricing(
  tier: 1 | 2 | 3,
  volume: number,
  currency: SupportedCurrency,
  partnerDiscountRate: number = 0.0
) {
  const config = SUPPORTED_CURRENCIES[currency] || SUPPORTED_CURRENCIES.COP;
  const unitPrice = config.tierPrices[tier] || config.tierPrices[2];
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
  const total = currency === "USD"
    ? Math.round(subtotal * (1 - combinedDiscount) * 100) / 100
    : Math.round(subtotal * (1 - combinedDiscount));

  // Compute COP equivalent for Wompi gateway settlement
  const unitPriceCop = Math.round(unitPrice * config.conversionRateToCop);
  const subtotalCop = Math.round(subtotal * config.conversionRateToCop);
  const totalCop = Math.round(total * config.conversionRateToCop);

  return {
    unitPrice,
    unitPriceCop,
    discountPercent: Math.round(combinedDiscount * 100),
    partnerDiscountPercent: Math.round(partnerDiscountRate * 100),
    partnerDiscountRate,
    subtotal,
    subtotalCop,
    total,
    totalCop,
  };
}

const getInitialCurrency = (): SupportedCurrency => {
  const saved = localStorage.getItem("michito_currency") as SupportedCurrency;
  if (saved && SUPPORTED_CURRENCIES[saved]) {
    return saved;
  }
  const savedLang = localStorage.getItem("michito_lang");
  if (savedLang === "en_US") {
    return "USD";
  }
  return DEFAULT_CURRENCY;
};

const initialCurrency = getInitialCurrency();
const initialCalc = calculatePricing(2, 25, initialCurrency, 0.0);

const initialState: PricingState = {
  tier: 2,
  volume: 25,
  currency: initialCurrency,
  ...initialCalc,
};

export const pricingSlice = createSlice({
  name: "pricing",
  initialState,
  reducers: {
    setTier: (state, action: PayloadAction<1 | 2 | 3>) => {
      state.tier = action.payload;
      const calc = calculatePricing(state.tier, state.volume, state.currency, state.partnerDiscountRate);
      Object.assign(state, calc);
    },
    setVolume: (state, action: PayloadAction<number>) => {
      state.volume = action.payload;
      const calc = calculatePricing(state.tier, state.volume, state.currency, state.partnerDiscountRate);
      Object.assign(state, calc);
    },
    setPartnerDiscountRate: (state, action: PayloadAction<number>) => {
      state.partnerDiscountRate = action.payload;
      const calc = calculatePricing(state.tier, state.volume, state.currency, state.partnerDiscountRate);
      Object.assign(state, calc);
    },
    setCurrency: (state, action: PayloadAction<SupportedCurrency>) => {
      state.currency = action.payload;
      localStorage.setItem("michito_currency", action.payload);
      const calc = calculatePricing(state.tier, state.volume, state.currency, state.partnerDiscountRate);
      Object.assign(state, calc);
    },
  },
});

export const { setTier, setVolume, setPartnerDiscountRate, setCurrency } = pricingSlice.actions;
export default pricingSlice.reducer;

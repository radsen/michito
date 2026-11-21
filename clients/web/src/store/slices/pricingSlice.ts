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
  trmRates?: { USD?: number; DOP?: number };
  catalogTierPrices?: Record<1 | 2 | 3, number>;
  catalogDiscounts?: Array<{ min_quantity: number; discount_percentage: number }>;
}

function calculatePricing(
  tier: 1 | 2 | 3,
  volume: number,
  currency: SupportedCurrency,
  partnerDiscountRate: number = 0.0,
  trmRates?: { USD?: number; DOP?: number },
  catalogTierPrices?: Record<1 | 2 | 3, number>,
  catalogDiscounts?: Array<{ min_quantity: number; discount_percentage: number }>
) {
  const config = SUPPORTED_CURRENCIES[currency] || SUPPORTED_CURRENCIES.COP;
  const unitPrice = (catalogTierPrices && catalogTierPrices[tier]) || config.tierPrices[tier] || config.tierPrices[2];
  const subtotal = unitPrice * volume;

  let volumeDiscount = 0;
  if (catalogDiscounts && catalogDiscounts.length > 0) {
    const sorted = [...catalogDiscounts].sort((a, b) => b.min_quantity - a.min_quantity);
    for (const d of sorted) {
      if (volume >= d.min_quantity) {
        volumeDiscount = d.discount_percentage / 100.0;
        break;
      }
    }
  } else {
    // Confirmed volume discount curve
    if (volume >= 1000) {
      volumeDiscount = 0.32;
    } else if (volume >= 500) {
      volumeDiscount = 0.25;
    } else if (volume >= 250) {
      volumeDiscount = 0.18;
    } else if (volume >= 100) {
      volumeDiscount = 0.10;
    } else if (volume >= 50) {
      volumeDiscount = 0.05;
    } else {
      volumeDiscount = 0.0;
    }
  }

  const combinedDiscount = Math.min(0.55, volumeDiscount + partnerDiscountRate);
  const minFloor = currency === "USD" ? 6.25 : (currency === "DOP" ? 400 : 25000);
  const rawTotal = subtotal * (1 - combinedDiscount);

  // Micro-Batch Courtesy Policy: If volume < 5, total is 0 (free courtesy sample).
  // Otherwise, enforce minimum order floor to protect gateway margins.
  const total = volume < 5
    ? 0
    : (currency === "USD"
        ? Math.round(Math.max(rawTotal, minFloor) * 100) / 100
        : Math.round(Math.max(rawTotal, minFloor)));

  // Compute COP equivalent for Wompi gateway settlement using live TRM rates if present
  let rateToCop = config.conversionRateToCop;
  if (currency === "USD" && trmRates?.USD) {
    rateToCop = trmRates.USD;
  } else if (currency === "DOP" && trmRates?.DOP) {
    rateToCop = trmRates.DOP;
  }

  const unitPriceCop = Math.round(unitPrice * rateToCop);
  const subtotalCop = Math.round(subtotal * rateToCop);
  const totalCop = Math.round(total * rateToCop);

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
      const calc = calculatePricing(state.tier, state.volume, state.currency, state.partnerDiscountRate, state.trmRates, state.catalogTierPrices, state.catalogDiscounts);
      Object.assign(state, calc);
    },
    setVolume: (state, action: PayloadAction<number>) => {
      state.volume = action.payload;
      const calc = calculatePricing(state.tier, state.volume, state.currency, state.partnerDiscountRate, state.trmRates, state.catalogTierPrices, state.catalogDiscounts);
      Object.assign(state, calc);
    },
    setPartnerDiscountRate: (state, action: PayloadAction<number>) => {
      state.partnerDiscountRate = action.payload;
      const calc = calculatePricing(state.tier, state.volume, state.currency, state.partnerDiscountRate, state.trmRates, state.catalogTierPrices, state.catalogDiscounts);
      Object.assign(state, calc);
    },
    setCurrency: (state, action: PayloadAction<SupportedCurrency>) => {
      state.currency = action.payload;
      localStorage.setItem("michito_currency", action.payload);
      const calc = calculatePricing(state.tier, state.volume, state.currency, state.partnerDiscountRate, state.trmRates, state.catalogTierPrices, state.catalogDiscounts);
      Object.assign(state, calc);
    },
    setTrmRates: (state, action: PayloadAction<{ USD?: number; DOP?: number }>) => {
      state.trmRates = { ...state.trmRates, ...action.payload };
      const calc = calculatePricing(state.tier, state.volume, state.currency, state.partnerDiscountRate, state.trmRates, state.catalogTierPrices, state.catalogDiscounts);
      Object.assign(state, calc);
    },
    setCatalogPricing: (
      state,
      action: PayloadAction<{
        tierPrices?: Record<1 | 2 | 3, number>;
        discounts?: Array<{ min_quantity: number; discount_percentage: number }>;
      }>
    ) => {
      if (action.payload.tierPrices) {
        state.catalogTierPrices = action.payload.tierPrices;
      }
      if (action.payload.discounts) {
        state.catalogDiscounts = action.payload.discounts;
      }
      const calc = calculatePricing(state.tier, state.volume, state.currency, state.partnerDiscountRate, state.trmRates, state.catalogTierPrices, state.catalogDiscounts);
      Object.assign(state, calc);
    },
  },
});

export const { setTier, setVolume, setPartnerDiscountRate, setCurrency, setTrmRates, setCatalogPricing } = pricingSlice.actions;
export default pricingSlice.reducer;

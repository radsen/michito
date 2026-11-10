export type SupportedCurrency = "COP" | "DOP" | "USD";

export interface CurrencyConfig {
  code: SupportedCurrency;
  symbol: string;
  prefix: string;
  suffix: string;
  flag: string;
  name: string;
  country: string;
  shortLabel: string;
  tierPrices: Record<1 | 2 | 3, number>;
  conversionRateToCop: number;
}

export const SUPPORTED_CURRENCIES: Record<SupportedCurrency, CurrencyConfig> = {
  COP: {
    code: "COP",
    symbol: "$",
    prefix: "$",
    suffix: " COP",
    flag: "🇨🇴",
    name: "Peso Colombiano",
    country: "Colombia",
    shortLabel: "🇨🇴 COP",
    tierPrices: {
      1: 5000,
      2: 30000,
      3: 65000,
    },
    conversionRateToCop: 1,
  },
  DOP: {
    code: "DOP",
    symbol: "RD$",
    prefix: "RD$ ",
    suffix: " DOP",
    flag: "🇩🇴",
    name: "Peso Dominicano",
    country: "Rep. Dominicana",
    shortLabel: "🇩🇴 DOP",
    tierPrices: {
      1: 100,
      2: 350,
      3: 750,
    },
    conversionRateToCop: 70, // 1 DOP ~ 70 COP
  },
  USD: {
    code: "USD",
    symbol: "$",
    prefix: "$",
    suffix: " USD",
    flag: "🇺🇸",
    name: "US Dollar",
    country: "Internacional",
    shortLabel: "🇺🇸 USD",
    tierPrices: {
      1: 1.5,
      2: 7.5,
      3: 16.0,
    },
    conversionRateToCop: 4100, // 1 USD ~ 4,100 COP
  },
};

export const DEFAULT_CURRENCY: SupportedCurrency = "COP";

export function formatCurrencyAmount(amount: number, currency: SupportedCurrency): string {
  const config = SUPPORTED_CURRENCIES[currency] || SUPPORTED_CURRENCIES.COP;
  if (currency === "USD") {
    const formatted = amount % 1 === 0 ? amount.toFixed(0) : amount.toFixed(2);
    return `${config.prefix}${formatted}${config.suffix}`;
  }
  const formatted = Math.round(amount).toLocaleString("es-CO");
  return `${config.prefix}${formatted}${config.suffix}`;
}

export function formatUnitCurrency(amount: number, currency: SupportedCurrency): string {
  const config = SUPPORTED_CURRENCIES[currency] || SUPPORTED_CURRENCIES.COP;
  if (currency === "USD") {
    const formatted = amount % 1 === 0 ? amount.toFixed(0) : amount.toFixed(2);
    return `${config.prefix}${formatted}`;
  }
  const formatted = Math.round(amount).toLocaleString("es-CO");
  return `${config.prefix}${formatted}`;
}

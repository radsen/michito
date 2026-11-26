export interface CountryConfig {
  code: string;
  name: string;
  flag: string;
  phonePrefix: string;
  defaultCurrency: "COP" | "DOP" | "USD";
  primaryRegistry: string;
}

export const SUPPORTED_COUNTRIES: Record<string, CountryConfig> = {
  CO: {
    code: "CO",
    name: "Colombia",
    flag: "🇨🇴",
    phonePrefix: "+57",
    defaultCurrency: "COP",
    primaryRegistry: "SECOP II / RUES",
  },
  DO: {
    code: "DO",
    name: "República Dominicana",
    flag: "🇩🇴",
    phonePrefix: "+1809",
    defaultCurrency: "DOP",
    primaryRegistry: "DGCP / DGII RNC",
  },
  EC: {
    code: "EC",
    name: "Ecuador",
    flag: "🇪🇨",
    phonePrefix: "+593",
    defaultCurrency: "USD",
    primaryRegistry: "SERCOP / Supercias",
  },
  CL: {
    code: "CL",
    name: "Chile",
    flag: "🇨🇱",
    phonePrefix: "+56",
    defaultCurrency: "USD",
    primaryRegistry: "Mercado Público / SII",
  },
};

export const COUNTRY_FLAGS: Record<string, string> = {
  CO: "🇨🇴",
  DO: "🇩🇴",
  EC: "🇪🇨",
  CL: "🇨🇱",
};

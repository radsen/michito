import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface CampaignSummary {
  id: string;
  name: string;
  country: string;
  description?: string;
  target_roles?: string[];
  target_cities?: string[];
  pricing_tier?: number;
  segment?: string;
}

export interface CampaignState {
  campaigns: CampaignSummary[];
  selectedCampaignId: string;
  selectedCity: string;
  availableCities: string[];
}

const FALLBACK_CAMPAIGNS: CampaignSummary[] = [
  {
    id: "tinkko_enterprise_offices",
    name: "Tinkko — Enterprise & Corporate Offices",
    country: "CO",
    description: "Prospección de directores y gerentes en empresas en expansión que requieren oficinas privadas y coworking.",
    target_cities: ["Medellín", "Bogotá", "Cali", "Barranquilla"],
    target_roles: ["Gerente General", "Director de Operaciones", "Director Administrativo", "CEO"],
    pricing_tier: 2,
  },
  {
    id: "alfred_corporate_fleet",
    name: "ALFRED — Mantenimiento & Flotas Corporativas",
    country: "CO",
    description: "Empresas con flotas de vehículos operativos o comerciales que buscan optimizar costos de mantenimiento.",
    target_cities: ["Bogotá", "Medellín", "Cali"],
    target_roles: ["Gerente de Logística", "Jefe de Flota", "Director de Operaciones"],
    pricing_tier: 2,
  },
  {
    id: "hebi_corporate_wellness",
    name: "Hebi — Soluciones de Bienestar y Salud Corporativa",
    country: "CO",
    description: "Compañías medianas y grandes estructurando planes de beneficios y salud laboral para colaboradores.",
    target_cities: ["Bogotá", "Medellín"],
    target_roles: ["Director de Gestión Humana", "Gerente de Talento Humano", "Director de Bienestar"],
    pricing_tier: 2,
  },
];

const initialState: CampaignState = {
  campaigns: FALLBACK_CAMPAIGNS,
  selectedCampaignId: "tinkko_enterprise_offices",
  selectedCity: "Medellín",
  availableCities: ["Medellín", "Bogotá", "Cali", "Barranquilla"],
};

export const campaignSlice = createSlice({
  name: "campaign",
  initialState,
  reducers: {
    setCampaigns: (state, action: PayloadAction<CampaignSummary[]>) => {
      state.campaigns = action.payload;
      if (action.payload.length > 0 && !action.payload.find((c) => c.id === state.selectedCampaignId)) {
        state.selectedCampaignId = action.payload[0].id;
        state.availableCities = action.payload[0].target_cities || ["Medellín", "Bogotá"];
        state.selectedCity = state.availableCities[0] || "Medellín";
      }
    },
    selectCampaign: (state, action: PayloadAction<string>) => {
      state.selectedCampaignId = action.payload;
      const found = state.campaigns.find((c) => c.id === action.payload);
      if (found && found.target_cities && found.target_cities.length > 0) {
        state.availableCities = found.target_cities;
        if (!state.availableCities.includes(state.selectedCity)) {
          state.selectedCity = state.availableCities[0];
        }
      }
    },
    selectCity: (state, action: PayloadAction<string>) => {
      state.selectedCity = action.payload;
    },
  },
});

export const { setCampaigns, selectCampaign, selectCity } = campaignSlice.actions;
export default campaignSlice.reducer;


import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import esCO from "../../locales/es_CO.json";
import enUS from "../../locales/en_US.json";

export type Language = "es_CO" | "en_US";

interface LanguageState {
  currentLanguage: Language;
  dict: typeof esCO;
}

const getInitialLanguage = (): Language => {
  const saved = localStorage.getItem("michito_lang");
  if (saved === "en_US" || saved === "es_CO") {
    return saved;
  }
  return "es_CO";
};

const initialLang = getInitialLanguage();

const initialState: LanguageState = {
  currentLanguage: initialLang,
  dict: initialLang === "en_US" ? enUS : esCO,
};

export const languageSlice = createSlice({
  name: "language",
  initialState,
  reducers: {
    setLanguage: (state, action: PayloadAction<Language>) => {
      state.currentLanguage = action.payload;
      state.dict = action.payload === "en_US" ? enUS : esCO;
      localStorage.setItem("michito_lang", action.payload);
    },
    toggleLanguage: (state) => {
      const next: Language = state.currentLanguage === "es_CO" ? "en_US" : "es_CO";
      state.currentLanguage = next;
      state.dict = next === "en_US" ? enUS : esCO;
      localStorage.setItem("michito_lang", next);
    },
  },
});

export const { setLanguage, toggleLanguage } = languageSlice.actions;
export default languageSlice.reducer;


import { configureStore } from "@reduxjs/toolkit";
import languageReducer from "./slices/languageSlice";
import pricingReducer from "./slices/pricingSlice";
import campaignReducer from "./slices/campaignSlice";
import orderReducer from "./slices/orderSlice";
import uiReducer from "./slices/uiSlice";
import { michitoApi } from "./api/michitoApi";

export const store = configureStore({
  reducer: {
    language: languageReducer,
    pricing: pricingReducer,
    campaign: campaignReducer,
    order: orderReducer,
    ui: uiReducer,
    [michitoApi.reducerPath]: michitoApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(michitoApi.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;


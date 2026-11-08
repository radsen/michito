import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface UiState {
  isWompiModalOpen: boolean;
  isMobileNavOpen: boolean;
  activeToast: string | null;
}

const initialState: UiState = {
  isWompiModalOpen: false,
  isMobileNavOpen: false,
  activeToast: null,
};

export const uiSlice = createSlice({
  name: "ui",
  initialState,
  reducers: {
    setWompiModalOpen: (state, action: PayloadAction<boolean>) => {
      state.isWompiModalOpen = action.payload;
    },
    setMobileNavOpen: (state, action: PayloadAction<boolean>) => {
      state.isMobileNavOpen = action.payload;
    },
    showToast: (state, action: PayloadAction<string>) => {
      state.activeToast = action.payload;
    },
    clearToast: (state) => {
      state.activeToast = null;
    },
  },
});

export const { setWompiModalOpen, setMobileNavOpen, showToast, clearToast } = uiSlice.actions;
export default uiSlice.reducer;


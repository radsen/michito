import React, { useState, useRef, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "../../store";
import { setCurrency } from "../../store/slices/pricingSlice";
import {
  SupportedCurrency,
  SUPPORTED_CURRENCIES,
} from "../../config/currencies";
import { ChevronDown } from "lucide-react";

interface CurrencySwitcherProps {
  variant?: "dropdown" | "segmented";
  className?: string;
}

export const CurrencySwitcher: React.FC<CurrencySwitcherProps> = ({
  variant = "dropdown",
  className = "",
}) => {
  const dispatch = useDispatch();
  const { currency } = useSelector((state: RootState) => state.pricing);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const activeConfig = SUPPORTED_CURRENCIES[currency] || SUPPORTED_CURRENCIES.COP;

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  if (variant === "segmented") {
    return (
      <div className={`currency-segmented-group ${className}`} data-testid="currency-segmented">
        {Object.values(SUPPORTED_CURRENCIES).map((c) => (
          <button
            key={c.code}
            type="button"
            onClick={() => dispatch(setCurrency(c.code))}
            className={`currency-segmented-btn ${currency === c.code ? "active" : ""}`}
            title={`${c.name} (${c.code})`}
          >
            <span className="currency-btn-flag">{c.flag}</span>
            <span className="currency-btn-code">{c.code}</span>
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className={`currency-dropdown-wrapper ${className}`} ref={dropdownRef} data-testid="currency-dropdown">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="currency-switcher-btn"
        title="Cambiar Moneda / Change Currency"
        aria-expanded={isOpen}
      >
        <span className="currency-btn-flag">{activeConfig.flag}</span>
        <span className="currency-btn-code">{activeConfig.code}</span>
        <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <div className="currency-dropdown-menu">
          <div className="currency-dropdown-header">Moneda / Currency</div>
          {Object.values(SUPPORTED_CURRENCIES).map((c) => (
            <button
              key={c.code}
              type="button"
              onClick={() => {
                dispatch(setCurrency(c.code));
                setIsOpen(false);
              }}
              className={`currency-dropdown-item ${currency === c.code ? "selected" : ""}`}
            >
              <span className="item-flag">{c.flag}</span>
              <div className="item-info">
                <span className="item-code-name">
                  <strong>{c.code}</strong> — {c.country}
                </span>
                <span className="item-sub">{c.name}</span>
              </div>
              {currency === c.code && <span className="item-check">✓</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};


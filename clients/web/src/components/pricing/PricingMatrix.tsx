import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "../../store";
import { setTier } from "../../store/slices/pricingSlice";
import { CurrencySwitcher } from "../common/CurrencySwitcher";
import { SUPPORTED_CURRENCIES, formatCurrencyAmount } from "../../config/currencies";
import { Check, Star, ShieldAlert, Sparkles, ShieldCheck } from "lucide-react";

export const PricingMatrix: React.FC = () => {
  const dispatch = useDispatch();
  const { dict } = useSelector((state: RootState) => state.language);
  const { tier: selectedTier, currency } = useSelector((state: RootState) => state.pricing);
  const p = dict.pricing;

  const curConfig = SUPPORTED_CURRENCIES[currency] || SUPPORTED_CURRENCIES.COP;
  const tier1PriceFormatted = formatCurrencyAmount(curConfig.tierPrices[1], currency);
  const tier2PriceFormatted = formatCurrencyAmount(curConfig.tierPrices[2], currency);
  const tier3PriceFormatted = formatCurrencyAmount(curConfig.tierPrices[3], currency);

  const handleChooseTier = (t: 1 | 2 | 3) => {
    dispatch(setTier(t));
    const el = document.getElementById("generador");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <section id="precios" className="pricing-section">
      <div className="section-container">
        <div className="section-header">
          <span className="section-kicker">{p.kicker}</span>
          <h2 className="section-title">{p.title}</h2>
          <p className="section-subtitle">{p.subtitle}</p>

          <div className="pricing-currency-bar">
            <span className="pricing-currency-label">{p.currencySelectorLabel || "Ver precios en:"}</span>
            <CurrencySwitcher variant="segmented" />
          </div>
        </div>

        <div className="pricing-cards-grid">
          {/* Tier 1 */}
          <div
            className={`pricing-card ${selectedTier === 1 ? "active-tier" : ""}`}
            onClick={() => handleChooseTier(1)}
          >
            <div className="tier-header">
              <h3 className="tier-name">{p.tier1Name}</h3>
              <p className="tier-desc">{p.tier1Desc}</p>
            </div>
            <div className="tier-price-box">
              <span className="tier-price">{tier1PriceFormatted}</span>
              <span className="tier-unit">{p.tier1Unit}</span>
            </div>
            <ul className="tier-features">
              <li>
                <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{p.tier1Feature1}</span>
              </li>
              <li>
                <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{p.tier1Feature2}</span>
              </li>
              <li>
                <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{p.tier1Feature3}</span>
              </li>
              <li>
                <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{p.tier1Feature4}</span>
              </li>
              <li>
                <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{p.tier1Feature5}</span>
              </li>
              <li>
                <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{p.tier1Feature6}</span>
              </li>
            </ul>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleChooseTier(1);
              }}
              className={`tier-cta-btn ${selectedTier === 1 ? "btn-selected" : ""}`}
            >
              {selectedTier === 1 ? "Directorio Seleccionado" : "Elegir Directorio"}
            </button>
          </div>

          {/* Tier 2 (Featured) */}
          <div
            className={`pricing-card tier-2-featured ${selectedTier === 2 ? "active-tier" : ""}`}
            onClick={() => handleChooseTier(2)}
          >
            <div className="featured-badge">
              <Star className="w-3.5 h-3.5 fill-current" />
              <span>{p.tier2Badge}</span>
            </div>
            <div className="tier-header">
              <h3 className="tier-name text-sky-400">{p.tier2Name}</h3>
              <p className="tier-desc">{p.tier2Desc}</p>
            </div>
            <div className="tier-price-box">
              <span className="tier-price">{tier2PriceFormatted}</span>
              <span className="tier-unit">{p.tier2Unit}</span>
            </div>
            <ul className="tier-features">
              <li>
                <Sparkles className="w-4 h-4 text-sky-400 shrink-0" />
                <span>{p.tier2Feature1}</span>
              </li>
              <li>
                <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{p.tier2Feature2}</span>
              </li>
              <li>
                <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{p.tier2Feature3}</span>
              </li>
              <li>
                <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{p.tier2Feature4}</span>
              </li>
              <li>
                <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{p.tier2Feature5}</span>
              </li>
              <li>
                <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{p.tier2Feature6}</span>
              </li>
            </ul>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleChooseTier(2);
              }}
              className={`tier-cta-btn btn-highlighted ${selectedTier === 2 ? "btn-selected" : ""}`}
            >
              {selectedTier === 2 ? "Contactos Directos Seleccionado" : "Elegir Contactos Directos"}
            </button>
          </div>

          {/* Tier 3 */}
          <div
            className={`pricing-card ${selectedTier === 3 ? "active-tier" : ""}`}
            onClick={() => handleChooseTier(3)}
          >
            <div className="tier-header">
              <h3 className="tier-name text-amber-400">{p.tier3Name}</h3>
              <p className="tier-desc">{p.tier3Desc}</p>
            </div>
            <div className="tier-price-box">
              <span className="tier-price">{tier3PriceFormatted}</span>
              <span className="tier-unit">{p.tier3Unit}</span>
            </div>
            <ul className="tier-features">
              <li>
                <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{p.tier3Feature1}</span>
              </li>
              <li>
                <Check className="w-4 h-4 text-amber-400 shrink-0" />
                <span>{p.tier3Feature2}</span>
              </li>
              <li>
                <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
                <span>{p.tier3Feature3}</span>
              </li>
              <li>
                <Check className="w-4 h-4 text-amber-400 shrink-0" />
                <span>{p.tier3Feature4}</span>
              </li>
              <li>
                <Check className="w-4 h-4 text-amber-400 shrink-0" />
                <span>{p.tier3Feature5}</span>
              </li>
              <li>
                <Check className="w-4 h-4 text-amber-400 shrink-0" />
                <span>{p.tier3Feature6}</span>
              </li>
            </ul>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleChooseTier(3);
              }}
              className={`tier-cta-btn ${selectedTier === 3 ? "btn-selected" : ""}`}
            >
              {selectedTier === 3 ? "Auditoría Seleccionada" : "Elegir Auditoría Completa"}
            </button>
          </div>
        </div>

        <div className="volume-discount-notice">
          <p>{p.volumeDiscounts}</p>
        </div>
      </div>
    </section>
  );
};

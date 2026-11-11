import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "../../store";
import { setTier, setVolume } from "../../store/slices/pricingSlice";
import { CurrencySwitcher } from "../common/CurrencySwitcher";
import { SUPPORTED_CURRENCIES, formatCurrencyAmount } from "../../config/currencies";
import { Check, Star, ShieldAlert, Sparkles, ShieldCheck, Calculator, ArrowRight } from "lucide-react";

export const PricingMatrix: React.FC = () => {
  const dispatch = useDispatch();
  const { dict } = useSelector((state: RootState) => state.language);
  const {
    tier: selectedTier,
    currency,
    volume,
    unitPrice,
    subtotal,
    total,
    discountPercent,
    totalCop,
  } = useSelector((state: RootState) => state.pricing);
  const p = dict.pricing;

  const curConfig = SUPPORTED_CURRENCIES[currency] || SUPPORTED_CURRENCIES.COP;
  const tier1PriceFormatted = formatCurrencyAmount(curConfig.tierPrices[1], currency);
  const tier2PriceFormatted = formatCurrencyAmount(curConfig.tierPrices[2], currency);
  const tier3PriceFormatted = formatCurrencyAmount(curConfig.tierPrices[3], currency);

  const handleChooseTier = (t: 1 | 2 | 3) => {
    dispatch(setTier(t));
  };

  const handleScrollToOrder = () => {
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
              {selectedTier === 1 ? "Tier 1 Seleccionado" : "Elegir Directorio"}
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
              {selectedTier === 2 ? "Tier 2 Seleccionado" : "Elegir Contactos Directos"}
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
              {selectedTier === 3 ? "Tier 3 Seleccionado" : "Elegir Auditoría"}
            </button>
          </div>
        </div>

        <div className="volume-discount-notice">
          <p>{p.volumeDiscounts}</p>
        </div>

        {/* Interactive Volume & Investment Calculator */}
        <div className="pricing-calculator-card">
          <div className="calc-card-header">
            <div className="calc-card-title-box">
              <Calculator className="w-5 h-5 text-sky-400" />
              <h3 className="calc-card-title">Simula tu Inversión por Volumen</h3>
            </div>
            <p className="calc-card-subtitle">
              Pagas únicamente por las cuentas verificadas. Descuentos automáticos hasta 42%.
            </p>
          </div>

          <div className="calc-controls-grid">
            <div className="calc-volume-picker">
              <label className="form-label">
                <span>Cantidad de Cuentas:</span>
                <strong className="text-sky-400 font-bold ml-1">{volume} cuentas</strong>
              </label>

              <div className="pricing-volume-presets-grid">
                <button
                  type="button"
                  onClick={() => dispatch(setVolume(10))}
                  className={`pricing-preset-btn ${volume === 10 ? "active" : ""}`}
                >
                  10
                </button>
                <button
                  type="button"
                  onClick={() => dispatch(setVolume(25))}
                  className={`pricing-preset-btn ${volume === 25 ? "active" : ""}`}
                >
                  25 (-6%)
                </button>
                <button
                  type="button"
                  onClick={() => dispatch(setVolume(50))}
                  className={`pricing-preset-btn ${volume === 50 ? "active" : ""}`}
                >
                  50 (-12%)
                </button>
                <button
                  type="button"
                  onClick={() => dispatch(setVolume(100))}
                  className={`pricing-preset-btn ${volume === 100 ? "active" : ""}`}
                >
                  100 (-20%)
                </button>
                <button
                  type="button"
                  onClick={() => dispatch(setVolume(500))}
                  className={`pricing-preset-btn ${volume === 500 ? "active" : ""}`}
                >
                  500+ (-42%)
                </button>
              </div>

              <input
                type="range"
                min="10"
                max="500"
                step="5"
                value={volume}
                onChange={(e) => dispatch(setVolume(Number(e.target.value)))}
                className="pricing-volume-slider"
              />
            </div>

            <div className="pricing-calc-summary">
              <div className="calc-row">
                <span>Paquete Seleccionado:</span>
                <span className="text-white font-semibold">
                  {selectedTier === 1
                    ? "Directorio Base"
                    : selectedTier === 2
                    ? "Contactos Directos"
                    : "Auditoría Completa"}
                </span>
              </div>
              <div className="calc-row">
                <span>Precio por cuenta:</span>
                <span>{formatCurrencyAmount(unitPrice, currency)}</span>
              </div>
              <div className="calc-row">
                <span>Subtotal ({volume} cuentas):</span>
                <span>{formatCurrencyAmount(subtotal, currency)}</span>
              </div>
              {discountPercent > 0 && (
                <div className="calc-row text-emerald-400">
                  <span className="flex items-center gap-1">
                    <Sparkles className="w-3.5 h-3.5" /> Descuento por volumen (-{discountPercent}%):
                  </span>
                  <span>-{formatCurrencyAmount(subtotal - total, currency)}</span>
                </div>
              )}
              <div className="calc-row-total">
                <span>Inversión Total:</span>
                <span className="total-cop">{formatCurrencyAmount(total, currency)}</span>
              </div>
              {currency !== "COP" && (
                <div className="text-xs text-slate-400 text-right mt-1">
                  Equivalente aproximado: {formatCurrencyAmount(totalCop, "COP")} (Liquidación Wompi)
                </div>
              )}

              <button
                type="button"
                onClick={handleScrollToOrder}
                className="calc-order-cta-btn"
              >
                <span>Configurar este Lote ({volume} Cuentas)</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

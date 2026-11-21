import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "../../store";
import { setTier, setVolume, setCatalogPricing } from "../../store/slices/pricingSlice";
import { useGetPricingCatalogQuery } from "../../store/api/michitoApi";
import { CurrencySwitcher } from "../common/CurrencySwitcher";
import { SUPPORTED_CURRENCIES, formatCurrencyAmount } from "../../config/currencies";
import { Check, Star, ShieldAlert, Sparkles, Calculator, ArrowRight } from "lucide-react";

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
    catalogTierPrices,
    catalogDiscounts,
  } = useSelector((state: RootState) => state.pricing);
  const p = dict.pricing;

  // Live dynamic catalog query from database
  const { data: catalogData } = useGetPricingCatalogQuery(currency);

  React.useEffect(() => {
    if (catalogData && catalogData.status === "success") {
      dispatch(
        setCatalogPricing({
          tierPrices: catalogData.tier_prices,
          discounts: catalogData.volume_discount_curve,
        })
      );
    }
  }, [catalogData, dispatch]);

  const curConfig = SUPPORTED_CURRENCIES[currency] || SUPPORTED_CURRENCIES.COP;
  const tier1Price = (catalogTierPrices && catalogTierPrices[1]) || curConfig.tierPrices[1];
  const tier2Price = (catalogTierPrices && catalogTierPrices[2]) || curConfig.tierPrices[2];
  const tier3Price = (catalogTierPrices && catalogTierPrices[3]) || curConfig.tierPrices[3];

  const tier1PriceFormatted = formatCurrencyAmount(tier1Price, currency);
  const tier2PriceFormatted = formatCurrencyAmount(tier2Price, currency);
  const tier3PriceFormatted = formatCurrencyAmount(tier3Price, currency);

  // Dynamic maximum discount percentage
  const maxDiscount = React.useMemo(() => {
    if (catalogDiscounts && catalogDiscounts.length > 0) {
      return Math.max(...catalogDiscounts.map((d) => d.discount_percentage));
    }
    return 32;
  }, [catalogDiscounts]);

  // Volume threshold scale milestones
  const thresholds = [
    { qty: 25, label: "25", pct: 0 },
    { qty: 50, label: "50", pct: 5 },
    { qty: 100, label: "100", pct: 10 },
    { qty: 250, label: "250", pct: 18 },
    { qty: 500, label: "500", pct: 25 },
    { qty: 1000, label: "1.000+", pct: 32 },
  ];

  // Calculate accounts needed to unlock the next discount tier
  const nextTierInfo = React.useMemo(() => {
    if (volume < 50) return { needed: 50 - volume, nextPct: 5 };
    if (volume < 100) return { needed: 100 - volume, nextPct: 10 };
    if (volume < 250) return { needed: 250 - volume, nextPct: 18 };
    if (volume < 500) return { needed: 500 - volume, nextPct: 25 };
    if (volume < 1000) return { needed: 1000 - volume, nextPct: 32 };
    return null;
  }, [volume]);

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
                <span>
                  {p.tier1Feature6?.replace("42%", `${maxDiscount}%`) || `Descuentos por volumen hasta ${maxDiscount}%`}
                </span>
              </li>
            </ul>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleChooseTier(1);
              }}
              className={`tier-cta-btn ${selectedTier === 1 ? "btn-selected" : ""}`}
            >
              {selectedTier === 1 ? p.tier1Selected : p.tier1Cta}
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
              {selectedTier === 2 ? p.tier2Selected : p.tier2Cta}
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
              {selectedTier === 3 ? p.tier3Selected : p.tier3Cta}
            </button>
          </div>
        </div>

        {/* Interactive Dynamic Volume & Investment Simulator */}
        <div className="pricing-calculator-card">
          <div className="calc-card-header">
            <div className="calc-card-title-box">
              <Calculator className="w-5 h-5 text-sky-400" />
              <h3 className="calc-card-title">{p.calcTitle}</h3>
            </div>
            <p className="calc-card-subtitle">{p.calcSubtitle}</p>
          </div>

          <div className="calc-controls-grid">
            <div className="calc-volume-picker">
              {/* Prominent Header with Quantity and Live Status Badge */}
              <div className="pricing-volume-header">
                <div>
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                    {p.calcVolumeLabel}
                  </span>
                  <span className="pricing-volume-val">
                    {volume} {p.calcAccountsUnit}
                  </span>
                </div>

                <div>
                  {discountPercent > 0 ? (
                    <span className="pricing-discount-badge active-discount">
                      <Sparkles className="w-3.5 h-3.5 fill-current" />
                      {p.calcSavingsBadge?.replace("{percent}", String(discountPercent)) ||
                        `-${discountPercent}% Ahorro por Volumen`}
                    </span>
                  ) : (
                    <span className="pricing-discount-badge base-rate">
                      {p.calcBaseRate || "Tarifa Base (Mínimo 25)"}
                    </span>
                  )}
                </div>
              </div>

              {/* Slider with Milestone Threshold Scale */}
              <div className="pricing-slider-container">
                <input
                  type="range"
                  min={25}
                  max={1000}
                  step={5}
                  value={Math.max(25, volume)}
                  onChange={(e) => dispatch(setVolume(Number(e.target.value)))}
                  className="pricing-volume-slider"
                  aria-label={p.calcVolumeLabel}
                />

                <div className="pricing-thresholds-track">
                  {thresholds.map((t) => {
                    const isReached = volume >= t.qty;
                    const isExact = volume === t.qty;
                    return (
                      <button
                        key={t.qty}
                        type="button"
                        onClick={() => dispatch(setVolume(t.qty))}
                        className={`threshold-tick-btn ${isReached ? "reached" : ""} ${
                          isExact ? "selected" : ""
                        }`}
                        title={`Seleccionar ${t.qty} cuentas`}
                      >
                        <span className="tick-dot" />
                        <span className="tick-label">{t.label}</span>
                        <span className="tick-badge">{t.pct > 0 ? `-${t.pct}%` : "Base"}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Motivational Unlock Progress Hint */}
              {nextTierInfo ? (
                <div className="pricing-next-tier-hint">
                  <Sparkles className="w-4 h-4 text-sky-400 shrink-0" />
                  <span>
                    {p.calcNextTierHint
                      ?.replace("{needed}", String(nextTierInfo.needed))
                      ?.replace("{nextPercent}", `${nextTierInfo.nextPct}%`) ||
                      `Agrega ${nextTierInfo.needed} cuentas más para activar ${nextTierInfo.nextPct}% de ahorro`}
                  </span>
                </div>
              ) : (
                <div className="pricing-next-tier-hint text-emerald-400 border-emerald-500/30">
                  <Sparkles className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>
                    {p.calcMaxDiscountReached?.replace("{percent}", `${maxDiscount}`) ||
                      `¡Descuento máximo del ${maxDiscount}% activado!`}
                  </span>
                </div>
              )}
            </div>

            {/* Live Financial Breakdown Summary */}
            <div className="pricing-calc-summary">
              <div className="calc-row">
                <span>{p.calcSelectedTier}</span>
                <span className="text-white font-semibold">
                  {selectedTier === 1
                    ? p.tier1Name
                    : selectedTier === 2
                    ? p.tier2Name
                    : p.tier3Name}
                </span>
              </div>
              <div className="calc-row">
                <span>{p.calcPricePerAccount}</span>
                <span>{formatCurrencyAmount(unitPrice, currency)}</span>
              </div>
              <div className="calc-row">
                <span>{p.calcSubtotal.replace("{volume}", String(volume))}</span>
                <span>{formatCurrencyAmount(subtotal, currency)}</span>
              </div>
              {discountPercent > 0 && (
                <div className="calc-row text-emerald-400">
                  <span className="flex items-center gap-1">
                    <Sparkles className="w-3.5 h-3.5" />{" "}
                    {p.calcDiscount.replace("{percent}", String(discountPercent))}
                  </span>
                  <span>-{formatCurrencyAmount(subtotal - total, currency)}</span>
                </div>
              )}
              <div className="calc-row-total">
                <span>{p.calcTotal}</span>
                <span className="total-cop">{formatCurrencyAmount(total, currency)}</span>
              </div>
              {currency !== "COP" && (
                <div className="text-xs text-slate-400 text-right mt-1">
                  {p.calcWompiEquiv.replace("{amount}", formatCurrencyAmount(totalCop, "COP"))}
                </div>
              )}

              <button
                type="button"
                onClick={handleScrollToOrder}
                className="calc-order-cta-btn"
              >
                <span>{p.calcOrderCta.replace("{volume}", String(volume))}</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

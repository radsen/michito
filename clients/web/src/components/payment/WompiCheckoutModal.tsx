import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "../../store";
import { setWompiModalOpen } from "../../store/slices/uiSlice";
import { updateOrderStatus } from "../../store/slices/orderSlice";
import { usePayOrderMutation, useGetOrderQuery } from "../../store/api/michitoApi";
import { formatCurrencyAmount } from "../../config/currencies";
import { X, CreditCard, ShieldCheck, AlertCircle, Loader2 } from "lucide-react";

declare global {
  interface Window {
    WidgetCheckout?: any;
  }
}

async function sha256(message: string): Promise<string> {
  const msgUint8 = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest("SHA-256", msgUint8);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

export const WompiCheckoutModal: React.FC = () => {
  const dispatch = useDispatch();
  const { dict } = useSelector((state: RootState) => state.language);
  const { isWompiModalOpen } = useSelector((state: RootState) => state.ui);
  const { activeOrderId, totalAmountInCents } = useSelector((state: RootState) => state.order);
  const { totalCop, total, currency } = useSelector((state: RootState) => state.pricing);
  const [payOrder, { isLoading: isPaying }] = usePayOrderMutation();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { data: orderData } = useGetOrderQuery(activeOrderId || "", {
    skip: !activeOrderId,
  });

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isWompiModalOpen) {
        dispatch(setWompiModalOpen(false));
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isWompiModalOpen, dispatch]);

  if (!isWompiModalOpen) return null;

  const resolvedAmountInCents =
    orderData?.amount_in_cents_cop ||
    (orderData?.total_price_cop ? Math.round(orderData.total_price_cop * 100) : null) ||
    (totalCop > 0 ? Math.round(totalCop * 100) : orderData?.amount_in_cents || totalAmountInCents);
  const WOMPI_PUBLIC_KEY =
    (orderData as any)?.payment?.wompi_public_key ||
    (import.meta as any).env?.VITE_WOMPI_PUBLIC_KEY ||
    "pub_test_IcBzwUvqUDy85sD7i3snlgxvMLj4A1eL";

  const handleOpenWompiWidget = async () => {
    setErrorMsg(null);
    if (!activeOrderId) {
      setErrorMsg((dict.checkout as any).errNoActiveOrder || "No se encontró una orden activa.");
      return;
    }

    try {
      if (typeof window.WidgetCheckout === "function") {
        // Retrieve server-generated cryptographic integrity signature
        // The secret stays securely on the server; the frontend only receives the pre-signed HMAC/SHA-256
        let integritySignature =
          (orderData as any)?.payment?.integrity_signature ||
          (orderData as any)?.integrity_signature;

        if (!integritySignature) {
          // Offline / development fallback only if server signature is omitted
          const fallbackSecret =
            (import.meta as any).env?.VITE_WOMPI_INTEGRITY_SECRET ||
            "test_integrity_r5SIpk6PnYywRaCxQlOXgySj28wNNlmj";
          const rawString = `${activeOrderId}${resolvedAmountInCents}COP${fallbackSecret}`;
          integritySignature = await sha256(rawString);
        }

        const checkoutConfig: any = {
          currency: "COP",
          amountInCents: resolvedAmountInCents,
          reference: activeOrderId,
          publicKey: WOMPI_PUBLIC_KEY,
          signature: { integrity: integritySignature },
        };

        if (orderData?.client?.email) {
          const customerData: any = {
            email: orderData.client.email,
            fullName: orderData.client.name,
          };

          const rawPhone = (orderData.client.phone || "").trim();
          if (rawPhone) {
            let prefix = "+57";
            let digits = rawPhone.replace(/\D/g, "");
            if (rawPhone.startsWith("+57") || (digits.startsWith("57") && digits.length === 12)) {
              prefix = "+57";
              digits = digits.startsWith("57") ? digits.slice(2) : digits;
            } else if (rawPhone.startsWith("+593") || (digits.startsWith("593") && digits.length === 12)) {
              prefix = "+593";
              digits = digits.startsWith("593") ? digits.slice(3) : digits;
            } else if (rawPhone.startsWith("+1") || (digits.startsWith("1") && digits.length === 11)) {
              prefix = "+1";
              digits = digits.startsWith("1") ? digits.slice(1) : digits;
            }
            if (digits.length >= 7 && digits.length <= 11) {
              customerData.phoneNumber = digits;
              customerData.phoneNumberPrefix = prefix;
            }
          }

          checkoutConfig.customerData = customerData;
        }

        const checkout = new window.WidgetCheckout(checkoutConfig);

        checkout.open(async (result: any) => {
          console.log("[Wompi] Transaction result:", result);
          dispatch(setWompiModalOpen(false));
          if (result && result.transaction && result.transaction.status === "APPROVED") {
            try {
              const res = await payOrder(activeOrderId).unwrap();
              dispatch(
                updateOrderStatus({
                  status: "paid",
                  csvUrl: res.order.csv_download_url,
                  xlsxUrl: (res.order as any).xlsx_download_url,
                  dossierUrl: res.order.dossier_download_url,
                  pdfUrl: (res.order as any).pdf_download_url,
                })
              );
            } catch {
              dispatch(updateOrderStatus({ status: "paid" }));
            }
            dispatch(setWompiModalOpen(false));
          }
        });
      } else {
        // Fallback to direct simulated API payment if widget script isn't loaded
        handleSimulatedDirectPayment();
      }
    } catch (err: any) {
      console.error("[Wompi] Error opening widget:", err);
      setErrorMsg(
        (dict.checkout as any).errWidgetInit ||
        "No se pudo iniciar el widget de Wompi. Puedes usar la confirmación directa de prueba."
      );
    }
  };

  const handleSimulatedDirectPayment = async () => {
    if (!activeOrderId) return;
    try {
      const res = await payOrder(activeOrderId).unwrap();
      if (res.status === "success") {
        dispatch(
          updateOrderStatus({
            status: "paid",
            csvUrl: res.order.csv_download_url,
            xlsxUrl: (res.order as any).xlsx_download_url,
            dossierUrl: res.order.dossier_download_url,
            pdfUrl: (res.order as any).pdf_download_url,
          })
        );
        dispatch(setWompiModalOpen(false));
      }
    } catch (err: any) {
      setErrorMsg(err?.data?.detail || (dict.checkout as any).errProcessing || "Error al procesar el pago.");
    }
  };

  const formatCop = (amount: number) => {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      dispatch(setWompiModalOpen(false));
    }
  };

  return (
    <div
      className="modal-backdrop"
      onClick={handleBackdropClick}
      data-testid="wompi-checkout-modal"
    >
      <div className="modal-card">
        <button
          onClick={() => dispatch(setWompiModalOpen(false))}
          className="modal-close-btn"
          aria-label={dict.checkout.closeLabel}
          type="button"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="modal-header">
          <div className="modal-icon-badge">
            <CreditCard className="w-6 h-6 text-sky-400" />
          </div>
          <h3 className="modal-title">{dict.checkout.modalTitle}</h3>
          <p className="modal-subtitle">
            {dict.checkout.modalSubtitle}
          </p>
        </div>

        <div className="modal-summary">
          <div className="summary-row">
            <span>{dict.checkout.reference}</span>
            <span className="font-mono text-white font-semibold">{activeOrderId}</span>
          </div>
          <div className="summary-row">
            <span>{dict.checkout.totalAmount}</span>
            <span className="text-xl font-bold text-emerald-400">
              {currency !== "COP"
                ? `${formatCurrencyAmount(total, currency)} (${formatCop(resolvedAmountInCents / 100)} COP)`
                : `${formatCop(resolvedAmountInCents / 100)} COP`}
            </span>
          </div>
          <div className="summary-row text-xs text-slate-400">
            <span>{dict.checkout.environment}</span>
            <span className={WOMPI_PUBLIC_KEY.startsWith("pub_prod") ? "text-emerald-400 font-semibold" : "text-amber-400 font-semibold"}>
              {WOMPI_PUBLIC_KEY.startsWith("pub_prod")
                ? ((dict.checkout as any).productionBadge || "Wompi Live (Production)")
                : dict.checkout.sandboxBadge}
            </span>
          </div>
        </div>

        {errorMsg && (
          <div className="modal-error-box">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <div className="modal-actions">
          <button
            onClick={handleOpenWompiWidget}
            className="modal-primary-btn"
            disabled={isPaying}
            type="button"
          >
            <CreditCard className="w-5 h-5" />
            <span>{dict.checkout.payBtn}</span>
          </button>

          <button
            onClick={handleSimulatedDirectPayment}
            className="modal-secondary-btn"
            disabled={isPaying}
            type="button"
          >
            {isPaying ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
            <span>{dict.checkout.devApproveBtn}</span>
          </button>
        </div>
      </div>
    </div>
  );
};


import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "../../store";
import { setWompiModalOpen } from "../../store/slices/uiSlice";
import { updateOrderStatus } from "../../store/slices/orderSlice";
import { usePayOrderMutation } from "../../store/api/michitoApi";
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
  const { isWompiModalOpen } = useSelector((state: RootState) => state.ui);
  const { activeOrderId, totalAmountInCents } = useSelector((state: RootState) => state.order);
  const { totalCop, total, currency } = useSelector((state: RootState) => state.pricing);
  const [payOrder, { isLoading: isPaying }] = usePayOrderMutation();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isWompiModalOpen) return null;

  const amountInCents = totalAmountInCents || totalCop * 100;
  const WOMPI_PUBLIC_KEY = "pub_test_IcBzwUvqUDy85sD7i3snlgxvMLj4A1eL";
  const WOMPI_INTEGRITY_SECRET = "test_integrity_r5SIpk6PnYywRaCxQlOXgySj28wNNlmj";

  const handleOpenWompiWidget = async () => {
    setErrorMsg(null);
    if (!activeOrderId) {
      setErrorMsg("No active order found.");
      return;
    }

    try {
      if (typeof window.WidgetCheckout === "function") {
        // Compute SHA-256 integrity signature
        // Form: reference + amount_in_cents + currency + integrity_secret
        const rawString = `${activeOrderId}${amountInCents}COP${WOMPI_INTEGRITY_SECRET}`;
        const integritySignature = await sha256(rawString);

        const checkout = new window.WidgetCheckout({
          currency: "COP",
          amountInCents: amountInCents,
          reference: activeOrderId,
          publicKey: WOMPI_PUBLIC_KEY,
          signature: { integrity: integritySignature },
          redirectUrl: window.location.href,
        });

        checkout.open(async (result: any) => {
          console.log("[Wompi] Transaction result:", result);
          if (result && result.transaction && result.transaction.status === "APPROVED") {
            dispatch(
              updateOrderStatus({
                status: "paid",
              })
            );
            dispatch(setWompiModalOpen(false));
          }
        });
      } else {
        // Fallback to direct simulated API payment if widget script isn't loaded
        handleSimulatedDirectPayment();
      }
    } catch (err: any) {
      console.error("[Wompi] Error opening widget:", err);
      setErrorMsg("No se pudo iniciar el widget de Wompi. Puedes usar la confirmación directa de prueba.");
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
            dossierUrl: res.order.dossier_download_url,
          })
        );
        dispatch(setWompiModalOpen(false));
      }
    } catch (err: any) {
      setErrorMsg(err?.data?.detail || "Error al procesar el pago.");
    }
  };

  const formatCop = (amount: number) => {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      maximumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-card">
        <button
          onClick={() => dispatch(setWompiModalOpen(false))}
          className="modal-close-btn"
          aria-label="Cerrar modal"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="modal-header">
          <div className="modal-icon-badge">
            <CreditCard className="w-6 h-6 text-sky-400" />
          </div>
          <h3 className="modal-title">Confirmar y Desbloquear Lote B2B</h3>
          <p className="modal-subtitle">
            Transacción segura con tarjeta, PSE o Bancolombia vía Wompi.
          </p>
        </div>

        <div className="modal-summary">
          <div className="summary-row">
            <span>Referencia:</span>
            <span className="font-mono text-white font-semibold">{activeOrderId}</span>
          </div>
          <div className="summary-row">
            <span>Monto Total:</span>
            <span className="text-xl font-bold text-emerald-400">
              {currency !== "COP"
                ? `${formatCurrencyAmount(total, currency)} (${formatCop(amountInCents / 100)} COP)`
                : `${formatCop(amountInCents / 100)} COP`}
            </span>
          </div>
          <div className="summary-row text-xs text-slate-400">
            <span>Ambiente:</span>
            <span className="text-amber-400 font-semibold">Wompi Sandbox (Pruebas)</span>
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
          >
            <CreditCard className="w-5 h-5" />
            <span>Pagar con Pasarela Wompi</span>
          </button>

          <button
            onClick={handleSimulatedDirectPayment}
            className="modal-secondary-btn"
            disabled={isPaying}
          >
            {isPaying ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
            <span>Aprobar Directo (Modo Sandbox / Dev)</span>
          </button>
        </div>
      </div>
    </div>
  );
};


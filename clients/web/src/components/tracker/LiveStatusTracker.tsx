import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "../../store";
import { updateOrderStatus, resetOrder } from "../../store/slices/orderSlice";
import { useGetOrderQuery } from "../../store/api/michitoApi";
import { SampleTeaserTable } from "./SampleTeaserTable";
import {
  CheckCircle2,
  Loader2,
  RefreshCw,
  Copy,
  Check,
  PlusCircle,
  Sparkles,
  Clock,
  Globe,
  Mail,
  ShieldCheck,
  FileSpreadsheet,
  FileText,
  Building2,
  AlertCircle,
} from "lucide-react";

export const LiveStatusTracker: React.FC = () => {
  const dispatch = useDispatch();
  const { dict } = useSelector((state: RootState) => state.language);
  const {
    activeOrderId,
    orderStatus,
    teaserLeads,
    totalLeadsTarget,
    totalAmountInCents,
    csvDownloadUrl,
    dossierDownloadUrl,
  } = useSelector((state: RootState) => state.order);

  const [copied, setCopied] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);

  // Poll every 2.5 seconds while active order is in flight
  const shouldPoll = Boolean(activeOrderId) && orderStatus !== "paid" && orderStatus !== "error";
  const { data: orderData, refetch, isFetching } = useGetOrderQuery(activeOrderId || "", {
    skip: !activeOrderId,
    pollingInterval: shouldPoll ? 2500 : 0,
  });

  const isQueued = orderStatus === "queued";
  const isProcessing = orderStatus === "processing";
  const isAwaitingPayment = orderStatus === "awaiting_payment";
  const isPaid = orderStatus === "paid";
  const isFailed = orderStatus === "failed" || orderStatus === "error";

  // Elapsed timer ticker while processing
  useEffect(() => {
    if (isQueued || isProcessing) {
      const interval = setInterval(() => {
        setElapsedSec((prev) => prev + 1);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [isQueued, isProcessing]);

  // Sync API response with Redux
  useEffect(() => {
    if (orderData) {
      dispatch(
        updateOrderStatus({
          status: orderData.status,
          teaserLeads: orderData.sample_leads,
          csvUrl: orderData.csv_download_url,
          dossierUrl: orderData.dossier_download_url,
          totalAmountInCents: orderData.amount_in_cents,
        })
      );
    }
  }, [orderData, dispatch]);

  if (!activeOrderId) return null;

  const handleCopyOrderId = () => {
    if (navigator?.clipboard && activeOrderId) {
      navigator.clipboard.writeText(activeOrderId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleNewOrder = () => {
    if (window.confirm("¿Deseas iniciar una nueva búsqueda? Podrás recuperar esta orden luego con su referencia.")) {
      dispatch(resetOrder());
    }
  };

  // Dynamic progress percentage
  const getProgressPercent = () => {
    if (isPaid) return 100;
    if (isAwaitingPayment) return 100;
    if (isProcessing) {
      return Math.min(88, 35 + elapsedSec * 5);
    }
    if (isQueued) return 20;
    return 10;
  };

  const progressPercent = getProgressPercent();

  const getStepStatus = (stepIndex: number) => {
    if (isPaid) return "completed";
    if (isAwaitingPayment && stepIndex <= 3) return "completed";
    if (isProcessing && stepIndex === 2) return "active";
    if (isProcessing && stepIndex < 2) return "completed";
    if (isQueued && stepIndex === 1) return "active";
    return "pending";
  };

  const steps = [
    { title: dict.tracker.statusQueued },
    { title: dict.tracker.statusHarvesting },
    { title: dict.tracker.statusVerifying },
    { title: dict.tracker.statusUnderwriting },
  ];

  return (
    <div className="tracker-card" data-testid="live-status-tracker">
      {/* Top Header with Order Reference and Actions */}
      <div className="tracker-header">
        <div className="flex items-center gap-3">
          <div className="tracker-spinner">
            {isFailed ? (
              <AlertCircle className="w-6 h-6 text-rose-400" />
            ) : !isAwaitingPayment && !isPaid ? (
              <Loader2 className="w-6 h-6 text-sky-400 animate-spin" />
            ) : (
              <CheckCircle2 className="w-6 h-6 text-emerald-400" />
            )}
          </div>
          <div>
            <h3 className="tracker-title">
              {isPaid
                ? dict.tracker.completedTitle
                : isFailed
                ? "Calificación no completada"
                : isAwaitingPayment
                ? "Calificación Lista: Revisa la Muestra y Desbloquea"
                : dict.tracker.processingTitle}
            </h3>
            <div className="tracker-ref-row">
              <span className="text-slate-400 text-xs">Referencia de Orden:</span>
              <strong className="font-mono text-sky-300 text-sm">{activeOrderId}</strong>
              <button
                onClick={handleCopyOrderId}
                className="copy-id-btn"
                title="Copiar ID de orden"
                type="button"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? "¡Copiado!" : "Copiar"}</span>
              </button>
            </div>
          </div>
        </div>

        <div className="tracker-action-buttons">
          <button
            onClick={() => refetch()}
            className={`tracker-icon-btn ${isFetching ? "animate-spin" : ""}`}
            title="Refrescar estado en vivo"
            type="button"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleNewOrder}
            className="tracker-new-search-btn"
            title="Iniciar nueva búsqueda"
            type="button"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Nueva Búsqueda</span>
          </button>
        </div>
      </div>

      {/* Real-Time Progress Bar & Timer */}
      <div className="tracker-progress-block">
        <div className="progress-bar-header">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-300">
              {isPaid
                ? "Entrega Confirmada"
                : isAwaitingPayment
                ? "Muestra Teaser Calificada (100%)"
                : isProcessing
                ? "Motor de Inteligencia Michito en Ejecución..."
                : "Orden en Cola • Asignando Worker..."}
            </span>
          </div>

          {(isQueued || isProcessing) && (
            <div className="tracker-timer-chip">
              <Clock className="w-3 h-3 text-sky-400" />
              <span>Tiempo: {elapsedSec}s (est. ~15s)</span>
            </div>
          )}
        </div>

        <div className="tracker-progress-track">
          <div
            className={`tracker-progress-fill ${isProcessing || isQueued ? "pulsing" : ""}`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Progress Timeline Steps */}
      <div className="timeline-container">
        {steps.map((st, i) => {
          const status = getStepStatus(i + 1);
          return (
            <div key={i} className={`timeline-step step-${status}`}>
              <div className="step-bubble">
                {status === "completed" ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : status === "active" ? (
                  <span className="w-2 h-2 rounded-full bg-sky-400 animate-ping" />
                ) : (
                  <span>{i + 1}</span>
                )}
              </div>
              <span className="step-label">{st.title}</span>
            </div>
          );
        })}
      </div>

      {/* Failed / Incomplete State Alert */}
      {isFailed && (
        <div className="order-failed-card" data-testid="order-failed-card">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-semibold text-rose-300 text-sm">
                No fue posible completar la calificación de prospectos
              </h4>
              <p className="text-xs text-slate-300 mt-1">
                {orderData?.error_message ||
                  "No se encontraron entidades que cumplieran con el 100% de los criterios de solvencia, sitio web verificado y buzón corporativo activo."}
              </p>
              <div className="mt-3 flex items-center gap-2">
                <button
                  onClick={handleNewOrder}
                  className="px-3.5 py-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-white font-medium text-xs transition-colors flex items-center gap-1.5"
                  type="button"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  <span>Ajustar Parámetros / Nueva Búsqueda</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Live Radar Quality Checks (Feedback during processing) */}
      {(isQueued || isProcessing) && (
        <div className="live-quality-radar" data-testid="live-quality-radar">
          <div className="radar-title">
            <Sparkles className="w-4 h-4 text-sky-400" />
            <span>Verificaciones en Ejecución en Segundo Plano (Worker Daemon)</span>
          </div>
          <div className="radar-grid">
            <div className="radar-item active">
              <Building2 className="w-4 h-4 text-sky-400" />
              <div>
                <div className="radar-item-title">Registros Mercantiles</div>
                <div className="radar-item-sub">Extrayendo NITs/RNC vigentes</div>
              </div>
            </div>
            <div className={`radar-item ${isProcessing ? "active" : ""}`}>
              <Globe className="w-4 h-4 text-emerald-400" />
              <div>
                <div className="radar-item-title">Auditoría Web HTTP</div>
                <div className="radar-item-sub">Descartando dominios caídos</div>
              </div>
            </div>
            <div className={`radar-item ${isProcessing ? "active" : ""}`}>
              <Mail className="w-4 h-4 text-purple-400" />
              <div>
                <div className="radar-item-title">Comprobación Socket MX</div>
                <div className="radar-item-sub">Verificando buzones directos</div>
              </div>
            </div>
            <div className={`radar-item ${isProcessing ? "active" : ""}`}>
              <ShieldCheck className="w-4 h-4 text-amber-400" />
              <div>
                <div className="radar-item-title">Solvencia & Cadencias</div>
                <div className="radar-item-sub">Redactando toques B2B</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sample Teaser Table if awaiting_payment or paid */}
      {(isAwaitingPayment || isPaid) && teaserLeads && teaserLeads.length > 0 && (
        <SampleTeaserTable
          leads={teaserLeads}
          totalLeads={totalLeadsTarget}
          totalAmountCop={(totalAmountInCents || 0) / 100}
        />
      )}

      {/* Deliverables Unlocked State */}
      {isPaid && (
        <div className="deliverables-unlocked-card">
          <div className="unlocked-header">
            <Sparkles className="w-6 h-6 text-emerald-400" />
            <div>
              <h4 className="text-lg font-bold text-white">Entregables Listos para Descarga Inmediata</h4>
              <p className="text-sm text-slate-300">
                Los enlaces seguros están activos por 48 horas. Tu orden queda guardada en tu navegador.
              </p>
            </div>
          </div>

          <div className="download-buttons-grid">
            {csvDownloadUrl ? (
              <a
                href={csvDownloadUrl}
                download
                className="download-btn csv-download"
                target="_blank"
                rel="noreferrer"
              >
                <FileSpreadsheet className="w-5 h-5 text-emerald-400" />
                <div className="text-left">
                  <div className="font-semibold text-white">{dict.tracker.downloadCsv}</div>
                  <div className="text-xs text-slate-400">HubSpot / Salesforce Ready</div>
                </div>
              </a>
            ) : (
              <button className="download-btn csv-download" disabled type="button">
                <FileSpreadsheet className="w-5 h-5 text-slate-400" />
                <span>Generando enlace seguro...</span>
              </button>
            )}

            {dossierDownloadUrl ? (
              <a
                href={dossierDownloadUrl}
                download
                className="download-btn dossier-download"
                target="_blank"
                rel="noreferrer"
              >
                <FileText className="w-5 h-5 text-blue-400" />
                <div className="text-left">
                  <div className="font-semibold text-white">{dict.tracker.downloadDossier}</div>
                  <div className="text-xs text-slate-400">Cadencias de 5 toques & Finanzas</div>
                </div>
              </a>
            ) : (
              <button className="download-btn dossier-download" disabled type="button">
                <FileText className="w-5 h-5 text-slate-400" />
                <span>Generando enlace seguro...</span>
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

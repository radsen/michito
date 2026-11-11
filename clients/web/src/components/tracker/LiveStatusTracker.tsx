import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "../../store";
import { updateOrderStatus, resetOrder } from "../../store/slices/orderSlice";
import { useGetOrderQuery } from "../../store/api/michitoApi";
import { SampleTeaserTable } from "./SampleTeaserTable";
import { OutreachPlaybook } from "./OutreachPlaybook";
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
  Download,
  FileCheck,
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
    xlsxDownloadUrl,
    dossierDownloadUrl,
    pdfDownloadUrl,
    playbook,
  } = useSelector((state: RootState) => state.order);

  const [copied, setCopied] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [activeViewTab, setActiveViewTab] = useState<"summary" | "playbook">("summary");

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
      const resolvedTotal =
        orderData.total_qualified && orderData.total_qualified > 0
          ? orderData.total_qualified
          : orderData.limit || (orderData as any).request?.limit || totalLeadsTarget;

      dispatch(
        updateOrderStatus({
          status: orderData.status,
          teaserLeads: orderData.sample_leads,
          csvUrl: orderData.csv_download_url,
          xlsxUrl: (orderData as any).xlsx_download_url,
          dossierUrl: orderData.dossier_download_url,
          pdfUrl: (orderData as any).pdf_download_url,
          playbook: (orderData as any).playbook || [],
          totalAmountInCents: orderData.amount_in_cents,
          totalLeadsTarget: resolvedTotal,
        })
      );
    }
  }, [orderData, dispatch, totalLeadsTarget]);

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

  const targetTier = (orderData as any)?.request?.tier || (orderData as any)?.tier || 2;
  const targetVolume = totalLeadsTarget || 25;

  // Realistic execution time estimation based on tier and volume:
  // Tier 1: ~0.8s/lead. 10 leads = 15s, 25 leads = 20s, 100 leads = 80s
  // Tier 2: ~1.8s/lead. 10 leads = 20s, 25 leads = 45s, 100 leads = 180s
  // Tier 3: ~3.5s/lead (Deep Financial & Legal Underwriting). 10 leads = 35s, 25 leads = 90s, 100 leads = ~350s (~6 min)
  const estimatedTotalSec = Math.max(
    15,
    Math.round(
      targetVolume * (targetTier === 3 ? 3.5 : targetTier === 2 ? 1.8 : 0.8)
    )
  );

  const formatTimeDisplay = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs.toString().padStart(2, "0")}s`;
  };

  const formatEstDisplay = (seconds: number) => {
    if (seconds < 60) return `~${seconds}s`;
    const mins = Math.ceil(seconds / 60);
    return `~${mins} min`;
  };

  // Dynamic progress percentage smoothly paced over estimated time
  const getProgressPercent = () => {
    if (isPaid || isAwaitingPayment) return 100;
    if (isProcessing) {
      const ratio = Math.min(1.0, elapsedSec / Math.max(estimatedTotalSec, 1));
      const paced = 20 + ratio * 74;
      return Math.min(94, Math.round(paced));
    }
    if (isQueued) return 15;
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
                ? targetTier === 3
                  ? "Auditando Estados Financieros, Rama Judicial y Registros en Tiempo Real..."
                  : "Calificando Huellas Web HTTP 200 y Servidores MX en Tiempo Real..."
                : "Orden en Cola • Asignando Worker..."}
            </span>
          </div>

          {(isQueued || isProcessing) && (
            <div className="tracker-timer-chip">
              <Clock className="w-3 h-3 text-sky-400" />
              <span>Tiempo: {formatTimeDisplay(elapsedSec)} (est. {formatEstDisplay(estimatedTotalSec)})</span>
            </div>
          )}
        </div>

        <div className="tracker-progress-track">
          <div
            className={`tracker-progress-fill ${isProcessing || isQueued ? "pulsing" : ""}`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {targetVolume >= 50 && isProcessing && (
          <div className="text-xs text-slate-400 mt-2 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-sky-400 shrink-0" />
            <span>
              Lote empresarial de {targetVolume} cuentas: realizando debida diligencia profunda en fuentes oficiales. No cierres esta ventana.
            </span>
          </div>
        )}
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
                  "No se encontraron cuentas que superaran todos los filtros de validación técnica, presencia web y buzón activo."}
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

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 my-4">
            {/* 1. Styled XLSX */}
            {xlsxDownloadUrl || csvDownloadUrl ? (
              <a
                href={xlsxDownloadUrl || `/api/v1/orders/${activeOrderId}/download/xlsx`}
                download
                className="download-btn xlsx-download group p-3.5 rounded-xl bg-teal-950/40 border border-teal-600/40 hover:border-teal-400 hover:bg-teal-900/30 transition-all flex items-center gap-3 text-left shadow-sm"
                target="_blank"
                rel="noreferrer"
              >
                <div className="w-10 h-10 rounded-lg bg-teal-900/60 border border-teal-500/40 flex items-center justify-center text-teal-300 shrink-0 group-hover:scale-105 transition-transform">
                  <FileSpreadsheet className="w-5 h-5 text-teal-300" />
                </div>
                <div className="min-w-0">
                  <div className="font-semibold text-white text-sm truncate">Hoja de Cálculo (.XLSX)</div>
                  <div className="text-xs text-teal-300/80 truncate">Excel con filtros y formato</div>
                </div>
              </a>
            ) : null}

            {/* 2. Executive PDF Dossier */}
            {pdfDownloadUrl || dossierDownloadUrl ? (
              <a
                href={pdfDownloadUrl || `/api/v1/orders/${activeOrderId}/download/pdf`}
                download
                className="download-btn pdf-download group p-3.5 rounded-xl bg-sky-950/40 border border-sky-600/40 hover:border-sky-400 hover:bg-sky-900/30 transition-all flex items-center gap-3 text-left shadow-sm"
                target="_blank"
                rel="noreferrer"
              >
                <div className="w-10 h-10 rounded-lg bg-sky-900/60 border border-sky-500/40 flex items-center justify-center text-sky-300 shrink-0 group-hover:scale-105 transition-transform">
                  <FileText className="w-5 h-5 text-sky-300" />
                </div>
                <div className="min-w-0">
                  <div className="font-semibold text-white text-sm truncate">Dossier Ejecutivo (.PDF)</div>
                  <div className="text-xs text-sky-300/80 truncate">Reporte C-Level & Guiones</div>
                </div>
              </a>
            ) : null}

            {/* 3. CRM-Clean CSV */}
            {csvDownloadUrl ? (
              <a
                href={csvDownloadUrl}
                download
                className="download-btn csv-download group p-3.5 rounded-xl bg-slate-900/80 border border-slate-700 hover:border-slate-500 hover:bg-slate-800 transition-all flex items-center gap-3 text-left shadow-sm"
                target="_blank"
                rel="noreferrer"
              >
                <div className="w-10 h-10 rounded-lg bg-slate-800 border border-slate-600 flex items-center justify-center text-emerald-400 shrink-0 group-hover:scale-105 transition-transform">
                  <Download className="w-5 h-5 text-emerald-400" />
                </div>
                <div className="min-w-0">
                  <div className="font-semibold text-white text-sm truncate">Base para CRM (.CSV)</div>
                  <div className="text-xs text-slate-400 truncate">HubSpot / Salesforce Ready</div>
                </div>
              </a>
            ) : null}

            {/* 4. Markdown Dossier */}
            {dossierDownloadUrl ? (
              <a
                href={dossierDownloadUrl}
                download
                className="download-btn dossier-download group p-3.5 rounded-xl bg-slate-900/80 border border-slate-700 hover:border-slate-500 hover:bg-slate-800 transition-all flex items-center gap-3 text-left shadow-sm"
                target="_blank"
                rel="noreferrer"
              >
                <div className="w-10 h-10 rounded-lg bg-slate-800 border border-slate-600 flex items-center justify-center text-slate-300 shrink-0 group-hover:scale-105 transition-transform">
                  <FileCheck className="w-5 h-5 text-slate-300" />
                </div>
                <div className="min-w-0">
                  <div className="font-semibold text-white text-sm truncate">Playbook Texto (.MD)</div>
                  <div className="text-xs text-slate-400 truncate">Notion / Obsidian Ready</div>
                </div>
              </a>
            ) : null}
          </div>
        </div>
      )}

      {/* View Switcher Tabs: Summary Table vs Interactive Outreach Playbook */}
      {(isAwaitingPayment || isPaid) && (
        <div className="space-y-4 mt-6">
          {playbook && playbook.length > 0 && (
            <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
              <button
                type="button"
                onClick={() => setActiveViewTab("summary")}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                  activeViewTab === "summary"
                    ? "bg-sky-600 text-white shadow-md shadow-sky-950"
                    : "text-slate-400 hover:text-white hover:bg-slate-800"
                }`}
              >
                📋 Resumen & Muestra de Datos
              </button>
              <button
                type="button"
                onClick={() => setActiveViewTab("playbook")}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors flex items-center gap-2 ${
                  activeViewTab === "playbook"
                    ? "bg-sky-600 text-white shadow-md shadow-sky-950"
                    : "text-slate-400 hover:text-white hover:bg-slate-800"
                }`}
              >
                <span>🎯 Playbook de Prospección (1-Click Outreach)</span>
                <span className="px-1.5 py-0.5 text-xs bg-sky-950 text-sky-300 rounded font-mono">
                  {playbook.length}
                </span>
              </button>
            </div>
          )}

          {/* Tab 1: Summary Table */}
          {activeViewTab === "summary" && teaserLeads && teaserLeads.length > 0 && (
            <SampleTeaserTable
              leads={teaserLeads}
              totalLeads={totalLeadsTarget}
              totalAmountCop={(totalAmountInCents || 0) / 100}
            />
          )}

          {/* Tab 2: Interactive 1-Click Outreach Playbook */}
          {activeViewTab === "playbook" && playbook && playbook.length > 0 && (
            <OutreachPlaybook companies={playbook} />
          )}
        </div>
      )}
    </div>
  );
};

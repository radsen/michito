import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "../../store";
import { updateOrderStatus, resetOrder } from "../../store/slices/orderSlice";
import { useGetOrderQuery, useClaimLeadReplacementMutation } from "../../store/api/michitoApi";
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
  ShieldAlert,
  FileSpreadsheet,
  FileText,
  Building2,
  AlertCircle,
  Download,
  FileCheck,
  RotateCcw,
  X,
  Share2,
  ExternalLink,
  MessageSquare,
} from "lucide-react";

export const LiveStatusTracker: React.FC = () => {
  const dispatch = useDispatch();
  const { currentLanguage, dict } = useSelector((state: RootState) => state.language);
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
  const [copiedLink, setCopiedLink] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [activeViewTab, setActiveViewTab] = useState<"summary" | "playbook">("summary");

  const getShareableApprovalUrl = () => {
    if (!activeOrderId) return "";
    const origin = window.location.origin;
    return `${origin}/rastrear?order_id=${activeOrderId}`;
  };

  const handleCopyApprovalLink = () => {
    const url = getShareableApprovalUrl();
    if (navigator?.clipboard && url) {
      navigator.clipboard.writeText(url);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2500);
    }
  };

  // Guarantee 2x1 Replacement State
  const [showGuaranteeModal, setShowGuaranteeModal] = useState(false);
  const [claimEmail, setClaimEmail] = useState("");
  const [claimCompany, setClaimCompany] = useState("");
  const [claimReason, setClaimReason] = useState("hard_bounce");
  const [claimError, setClaimError] = useState<string | null>(null);
  const [claimSuccess, setClaimSuccess] = useState<string | null>(null);
  const [claimReplacement, { isLoading: isClaiming }] = useClaimLeadReplacementMutation();

  const handleClaimSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeOrderId || !claimEmail.trim()) return;
    setClaimError(null);
    setClaimSuccess(null);
    try {
      const res = await claimReplacement({
        orderId: activeOrderId,
        bounced_email: claimEmail.trim(),
        company_name: claimCompany.trim() || undefined,
        reason: claimReason,
      }).unwrap();
      setClaimSuccess(res.message);
      setClaimEmail("");
      setClaimCompany("");
      refetch();
    } catch (err: any) {
      setClaimError(err?.data?.detail || "No fue posible procesar la garantía técnica para este correo.");
    }
  };

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

  // Elapsed timer ticker synchronized with server timestamps and session persistence
  useEffect(() => {
    const computeCurrentElapsed = () => {
      // 1. If completed and server reported total execution time
      if (orderData?.metrics?.total_elapsed_seconds) {
        return Math.max(0, Math.round(orderData.metrics.total_elapsed_seconds));
      }

      // 2. Authoritative server start timestamp
      const serverStart = orderData?.started_processing_at || orderData?.created_at;
      if (serverStart) {
        const startMs = new Date(serverStart).getTime();
        if (!isNaN(startMs)) {
          const diffSec = Math.max(0, Math.floor((Date.now() - startMs) / 1000));
          if (activeOrderId) {
            sessionStorage.setItem(`michito_order_start_${activeOrderId}`, String(startMs));
          }
          return diffSec;
        }
      }

      // 3. Fallback to session storage for instant response across reloads before network response
      if (activeOrderId) {
        const cachedStart = sessionStorage.getItem(`michito_order_start_${activeOrderId}`);
        if (cachedStart) {
          const startMs = parseInt(cachedStart, 10);
          if (!isNaN(startMs)) {
            return Math.max(0, Math.floor((Date.now() - startMs) / 1000));
          }
        } else {
          sessionStorage.setItem(`michito_order_start_${activeOrderId}`, String(Date.now()));
        }
      }

      return 0;
    };

    // Calculate immediately on mount or data change
    setElapsedSec(computeCurrentElapsed());

    if (isQueued || isProcessing) {
      const interval = setInterval(() => {
        setElapsedSec(computeCurrentElapsed());
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [
    isQueued,
    isProcessing,
    activeOrderId,
    orderData?.created_at,
    orderData?.started_processing_at,
    orderData?.metrics?.total_elapsed_seconds,
  ]);

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
              <span className="tracker-ref-label">Referencia de Orden:</span>
              <strong className="tracker-ref-id">{activeOrderId}</strong>
              <button
                onClick={handleCopyOrderId}
                className="copy-id-btn"
                title="Copiar ID de orden"
                type="button"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? "¡Copiado!" : "Copiar"}</span>
              </button>
              <button
                onClick={handleCopyApprovalLink}
                className="copy-id-btn"
                title="Copiar enlace compartible para aprobación"
                type="button"
              >
                {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Share2 className="w-3.5 h-3.5 text-sky-400" />}
                <span>{copiedLink ? "¡Enlace Copiado!" : "Compartir Enlace"}</span>
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

      {/* Shareable Quote & Approval Banner */}
      <div className="shareable-quote-box">
        <div className="shareable-quote-layout">
          <div className="shareable-quote-left">
            <div className="shareable-quote-icon">
              <Share2 className="w-4 h-4" />
            </div>
            <div>
              <div className="shareable-quote-header">
                <span className="shareable-quote-title">Enlace Compartible de Aprobación</span>
                <span className="shareable-quote-badge">
                  {isPaid ? "Entrega Aprobada" : isAwaitingPayment ? "Listo para Aprobación" : "En Calificación"}
                </span>
              </div>
              <p className="shareable-quote-desc">
                Comparte este enlace directo con tu líder comercial o equipo para revisar los criterios, verificar la muestra y autorizar el lote.
              </p>
            </div>
          </div>
          <div className="shareable-quote-actions">
            <button
              type="button"
              onClick={handleCopyApprovalLink}
              className="btn-quote-copy"
            >
              {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-300" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedLink ? "¡Copiado!" : "Copiar Enlace"}</span>
            </button>
            <a
              href={`https://wa.me/?text=${encodeURIComponent(`Hola, por favor revisa y aprueba esta cotización de prospección B2B en Michito: ${getShareableApprovalUrl()}`)}`}
              target="_blank"
              rel="noreferrer"
              className="btn-quote-whatsapp"
              title="Compartir por WhatsApp"
            >
              <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />
              <span>WhatsApp</span>
            </a>
          </div>
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

          {isQueued || isProcessing ? (
            <div className="tracker-timer-chip">
              <Clock className="w-3 h-3 text-sky-400" />
              <span>Tiempo: {formatTimeDisplay(elapsedSec)} (est. {formatEstDisplay(estimatedTotalSec)})</span>
            </div>
          ) : elapsedSec > 0 ? (
            <div className="tracker-timer-chip">
              <Clock className="w-3 h-3 text-emerald-400" />
              <span>Tiempo de calificación: {formatTimeDisplay(elapsedSec)}</span>
            </div>
          ) : null}
        </div>

        <div className="tracker-progress-track">
          <div
            className={`tracker-progress-fill ${isProcessing || isQueued ? "pulsing" : ""}`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {(isProcessing || isQueued) && (
          <div className="tracker-async-notice">
            <div className="flex items-center gap-2 text-xs font-semibold text-sky-300">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
              <span>
                {currentLanguage === "en_US"
                  ? "Your batch is being processed"
                  : "Tu lote se está procesando"}
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed mt-1 mb-0">
              {currentLanguage === "en_US"
                ? `You don't need to keep this window open. Feel free to close it or carry on with your tasks; once verification finishes, you can review your qualified prospects right here with your order number (${activeOrderId}).`
                : `Puedes cerrar esta ventana o continuar con tus actividades habituales. La verificación seguirá ejecutándose normalmente; cuando finalice, podrás revisar tus prospectos calificados aquí mismo con tu número de orden (${activeOrderId}).`}
            </p>
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
          <div className="order-failed-layout">
            <AlertCircle className="w-5 h-5 order-failed-icon" />
            <div className="order-failed-content">
              <h4 className="order-failed-title">
                No fue posible completar la calificación de prospectos
              </h4>
              <p className="order-failed-desc">
                {orderData?.error_message ||
                  "No se encontraron cuentas que superaran todos los filtros de validación técnica, presencia web y buzón activo."}
              </p>
              <div className="order-failed-actions">
                <button
                  onClick={handleNewOrder}
                  className="order-failed-btn"
                  type="button"
                >
                  <PlusCircle className="w-4 h-4" />
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

          <div className="download-buttons-grid">
            {/* 1. Styled XLSX */}
            {xlsxDownloadUrl || csvDownloadUrl ? (
              <a
                href={xlsxDownloadUrl || `/api/v1/orders/${activeOrderId}/download/xlsx`}
                download
                className="download-btn xlsx-download"
                target="_blank"
                rel="noreferrer"
              >
                <div className="download-btn-icon xlsx-icon">
                  <FileSpreadsheet className="w-5 h-5" />
                </div>
                <div className="download-btn-info">
                  <div className="download-btn-title">Hoja de Cálculo (.XLSX)</div>
                  <div className="download-btn-sub">Excel con filtros y formato</div>
                </div>
              </a>
            ) : null}

            {/* 2. Executive PDF Dossier */}
            {pdfDownloadUrl || dossierDownloadUrl ? (
              <a
                href={pdfDownloadUrl || `/api/v1/orders/${activeOrderId}/download/pdf`}
                download
                className="download-btn pdf-download"
                target="_blank"
                rel="noreferrer"
              >
                <div className="download-btn-icon pdf-icon">
                  <FileText className="w-5 h-5" />
                </div>
                <div className="download-btn-info">
                  <div className="download-btn-title">Dossier Ejecutivo (.PDF)</div>
                  <div className="download-btn-sub">Reporte C-Level & Guiones</div>
                </div>
              </a>
            ) : null}

            {/* 3. CRM-Clean CSV */}
            {csvDownloadUrl ? (
              <a
                href={csvDownloadUrl}
                download
                className="download-btn csv-download"
                target="_blank"
                rel="noreferrer"
              >
                <div className="download-btn-icon csv-icon">
                  <Download className="w-5 h-5" />
                </div>
                <div className="download-btn-info">
                  <div className="download-btn-title">Base para CRM (.CSV)</div>
                  <div className="download-btn-sub">HubSpot / Salesforce Ready</div>
                </div>
              </a>
            ) : null}

            {/* 4. Markdown Dossier */}
            {dossierDownloadUrl ? (
              <a
                href={dossierDownloadUrl}
                download
                className="download-btn dossier-download"
                target="_blank"
                rel="noreferrer"
              >
                <div className="download-btn-icon dossier-icon">
                  <FileCheck className="w-5 h-5" />
                </div>
                <div className="download-btn-info">
                  <div className="download-btn-title">Playbook Texto (.MD)</div>
                  <div className="download-btn-sub">Notion / Obsidian Ready</div>
                </div>
              </a>
            ) : null}
          </div>

          {/* Phase 3: Automated 2x1 Replacement Guarantee Portal */}
          <div className="guarantee-banner-card">
            <div className="guarantee-banner-layout">
              <div className="guarantee-banner-left">
                <div className="guarantee-banner-icon">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h5 className="text-sm font-bold text-white">Garantía Técnica 2x1 por Rebote Duro</h5>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-500/40">
                      7 Días Activa
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 mt-0.5">
                    Si un correo corporativo presenta rebote duro verificado, recibe 2 cuentas nuevas de reemplazo al instante.
                  </p>
                  {orderData?.replacement_claims && orderData.replacement_claims.length > 0 && (
                    <div className="text-xs text-emerald-400 font-medium mt-1">
                      Garantías aplicadas: {orderData.replacement_claims.length} rebote(s) reportado(s) •{" "}
                      {orderData.replacement_claims.reduce((acc: number, c: any) => acc + (c.replacement_count || 2), 0)} cuentas adicionales generadas
                    </div>
                  )}
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowGuaranteeModal(true);
                  setClaimError(null);
                  setClaimSuccess(null);
                }}
                className="btn-guarantee-claim"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reclamar Reemplazo 2x1</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* View Switcher Tabs: Summary Table vs Interactive Outreach Playbook */}
      {(isAwaitingPayment || isPaid) && (
        <div className="space-y-4 mt-6">
          {playbook && playbook.length > 0 && (
            <div className="tracker-view-tabs">
              <button
                type="button"
                onClick={() => setActiveViewTab("summary")}
                className={`tracker-view-tab-btn ${activeViewTab === "summary" ? "active" : ""}`}
              >
                Resumen & Muestra de Datos
              </button>
              <button
                type="button"
                onClick={() => setActiveViewTab("playbook")}
                className={`tracker-view-tab-btn ${activeViewTab === "playbook" ? "active" : ""}`}
              >
                <span>Playbook de Prospección (1-Click Outreach)</span>
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
              totalAmountCop={(orderData?.amount_in_cents || totalAmountInCents || 0) / 100}
            />
          )}

          {/* Tab 2: Interactive 1-Click Outreach Playbook */}
          {activeViewTab === "playbook" && playbook && playbook.length > 0 && (
            <OutreachPlaybook companies={playbook} />
          )}
        </div>
      )}

      {/* 2x1 Guarantee Claim Modal */}
      {showGuaranteeModal && (
        <div className="claim-modal-backdrop">
          <div className="claim-modal-card">
            <button
              type="button"
              onClick={() => setShowGuaranteeModal(false)}
              className="claim-modal-close-btn"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-emerald-950/80 border border-emerald-500/40 flex items-center justify-center text-emerald-400 shrink-0">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-base font-bold text-white">Reclamar Garantía Técnica 2x1</h4>
                <p className="text-xs text-slate-400">Reemplazo instantáneo de contactos con rebote verificado</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 mb-4 leading-relaxed">
              Ingresa el correo corporativo que presentó rebote duro (hard bounce). El motor registrará el correo en el
              ledger global de deduplicación y generará de inmediato <strong>2 cuentas nuevas</strong> con el mismo criterio territorial y de rol.
            </p>

            {claimSuccess && (
              <div className="mb-4 p-3 rounded-xl bg-emerald-950/70 border border-emerald-500/50 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                <span>{claimSuccess}</span>
              </div>
            )}

            {claimError && (
              <div className="mb-4 p-3 rounded-xl bg-rose-950/70 border border-rose-500/50 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{claimError}</span>
              </div>
            )}

            <form onSubmit={handleClaimSubmit} className="space-y-3">
              <div>
                <label className="claim-form-label">
                  Correo Electrónico Rebotado *
                </label>
                <input
                  type="email"
                  required
                  placeholder="ejemplo@empresa.com"
                  value={claimEmail}
                  onChange={(e) => setClaimEmail(e.target.value)}
                  className="claim-form-input"
                />
                {teaserLeads && teaserLeads.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1 items-center">
                    <span className="text-[11px] text-slate-400">Sugeridos de la orden:</span>
                    {teaserLeads.slice(0, 4).map((l, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => {
                          setClaimEmail(l.email);
                          if (l.company_name) setClaimCompany(l.company_name);
                        }}
                        className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 truncate max-w-[140px]"
                      >
                        {l.email}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <label className="claim-form-label">
                  Nombre de la Empresa (Opcional)
                </label>
                <input
                  type="text"
                  placeholder="Empresa asociada al contacto"
                  value={claimCompany}
                  onChange={(e) => setClaimCompany(e.target.value)}
                  className="claim-form-input"
                />
              </div>

              <div>
                <label className="claim-form-label">
                  Motivo del Rechazo
                </label>
                <select
                  value={claimReason}
                  onChange={(e) => setClaimReason(e.target.value)}
                  className="claim-form-select"
                >
                  <option value="hard_bounce">Rebote Duro / Buzón Inexistente (Error 550)</option>
                  <option value="domain_dead">Dominio Inactivo / Sin Registro MX</option>
                  <option value="left_company">Contacto Ya No Labora en la Compañía</option>
                  <option value="mailbox_full">Buzón Saturado Permanente</option>
                </select>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowGuaranteeModal(false)}
                  className="claim-cancel-btn"
                >
                  Cerrar
                </button>
                <button
                  type="submit"
                  disabled={isClaiming || !claimEmail.trim()}
                  className="claim-submit-btn"
                >
                  {isClaiming ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Generando Reemplazos...</span>
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>Ejecutar Garantía 2x1</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

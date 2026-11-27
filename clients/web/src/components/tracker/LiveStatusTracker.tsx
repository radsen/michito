import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "../../store";
import { updateOrderStatus, resetOrder, orderFailed } from "../../store/slices/orderSlice";
import { setWompiModalOpen } from "../../store/slices/uiSlice";
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
  Database,
  CreditCard,
} from "lucide-react";

export interface LiveStatusTrackerProps {
  onAdjustParameters?: () => void;
}

export const LiveStatusTracker: React.FC<LiveStatusTrackerProps> = ({ onAdjustParameters }) => {
  const dispatch = useDispatch();
  const { currentLanguage, dict } = useSelector((state: RootState) => state.language);
  const {
    activeOrderId,
    orderStatus,
    errorMessage,
    teaserLeads,
    totalLeadsTarget,
    totalQualified,
    totalAmountInCents,
    csvDownloadUrl,
    fullCsvDownloadUrl,
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
    return `${origin}/track?order_id=${activeOrderId}`;
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
      setClaimError(err?.data?.detail || (dict.tracker as any).guaranteeClaimError || "No fue posible procesar la garantía técnica para este correo.");
    }
  };

  // Poll every 3 seconds while active order is in flight (persistent until terminal state)
  const isTerminalReduxState =
    orderStatus === "paid" ||
    orderStatus === "delivered" ||
    orderStatus === "courtesy_delivered" ||
    orderStatus === "awaiting_payment" ||
    orderStatus === "ready_for_review";

  const shouldPoll = Boolean(activeOrderId) && !isTerminalReduxState;

  const { data: orderData, refetch, isFetching, isError, error } = useGetOrderQuery(
    activeOrderId || "",
    {
      skip: !activeOrderId,
      pollingInterval: shouldPoll ? 3000 : 0,
    }
  );

  const isTerminalSuccess =
    isTerminalReduxState ||
    (orderData as any)?.status === "awaiting_payment" ||
    (orderData as any)?.status === "ready_for_review" ||
    (orderData as any)?.status === "paid" ||
    (orderData as any)?.status === "delivered";

  const isExplicitBackendFailure =
    ((orderData as any)?.status === "failed" ||
      (orderData as any)?.status === "failed_zero_leads") &&
    !isTerminalSuccess;

  const isCourtesyDelivered =
    orderStatus === "courtesy_delivered" ||
    (orderData as any)?.order_status === "courtesy_delivered" ||
    (orderData as any)?.status === "courtesy_delivered" ||
    (orderData as any)?.payment_status === "COURTESY_FREE";

  const isQueued =
    (orderStatus === "queued" || orderStatus === "intake_submitted" || (orderData as any)?.status === "queued") &&
    !isTerminalSuccess;
  const isProcessing =
    (orderStatus === "processing" || (orderData as any)?.status === "processing") &&
    !isTerminalSuccess;
  const isAwaitingPayment =
    (orderStatus === "awaiting_payment" ||
      orderStatus === "ready_for_review" ||
      (orderData as any)?.status === "awaiting_payment" ||
      (orderData as any)?.status === "ready_for_review") &&
    !isCourtesyDelivered;
  const isPaid = orderStatus === "paid" || orderStatus === "delivered" || isCourtesyDelivered;
  const isFailed = isExplicitBackendFailure && !isTerminalSuccess;

  // Handle API error (Only mark failed if backend explicitly returns 404, never on transient network drop)
  useEffect(() => {
    if (isError) {
      const statusCode = (error as any)?.status;
      if (statusCode === 404) {
        const errDetail =
          (error as any)?.data?.detail ||
          (error as any)?.message ||
          "Orden no encontrada en este entorno.";
        dispatch(orderFailed(errDetail));
      } else {
        console.warn("Transient network issue during order polling. Will retry...", error);
      }
    }
  }, [isError, error, dispatch]);

  // Server-Sent Events (SSE) Stream Listener with auto-reconnection for live telemetry
  useEffect(() => {
    const token = (orderData as any)?.stream_token || "";
    // CRITICAL: Do NOT attempt SSE if token is empty, otherwise Cloud Run responds with 403 Forbidden!
    if (!activeOrderId || (!isQueued && !isProcessing) || !token) return;
    const sseUrl = `/api/v1/orders/${activeOrderId}/stream?token=${encodeURIComponent(token)}`;

    let eventSource: EventSource | null = null;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
    let isDisposed = false;

    const initSSE = () => {
      if (isDisposed) return;
      try {
        eventSource = new EventSource(sseUrl);
        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.status && data.status !== orderStatus) {
              refetch();
            }
          } catch {
            // ignore JSON parse errors
          }
        };
        eventSource.addEventListener("close", () => {
          refetch();
          eventSource?.close();
        });
        eventSource.onerror = () => {
          eventSource?.close();
          if (!isDisposed) {
            reconnectTimeout = setTimeout(initSSE, 3500);
          }
        };
      } catch {
        // Fallback to RTK polling
      }
    };

    initSSE();

    return () => {
      isDisposed = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      eventSource?.close();
    };
  }, [activeOrderId, isQueued, isProcessing, (orderData as any)?.stream_token]);

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
        const hasTz = serverStart.endsWith("Z") || /[+-]\d{2}:\d{2}$/.test(serverStart);
        const normalizedStart = hasTz ? serverStart : `${serverStart}Z`;
        const startMs = new Date(normalizedStart).getTime();
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
          fullCsvUrl: (orderData as any).full_csv_download_url,
          xlsxUrl: (orderData as any).xlsx_download_url,
          dossierUrl: orderData.dossier_download_url,
          pdfUrl: (orderData as any).pdf_download_url,
          playbook: (orderData as any).playbook || [],
          totalAmountInCents: orderData.amount_in_cents,
          totalLeadsTarget: resolvedTotal,
          totalQualified: orderData.total_qualified,
        })
      );
    }
  }, [orderData, dispatch, totalLeadsTarget]);

  // Smoothly bring the deliverables section into view upon payment confirmation
  useEffect(() => {
    if (isPaid) {
      setTimeout(() => {
        const target = document.querySelector(".deliverables-unlocked-card");
        if (target) {
          target.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }, 200);
    }
  }, [isPaid]);

  if (!activeOrderId) return null;

  const handleCopyOrderId = () => {
    if (navigator?.clipboard && activeOrderId) {
      navigator.clipboard.writeText(activeOrderId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleNewOrder = () => {
    if (onAdjustParameters) {
      onAdjustParameters();
    } else {
      dispatch(resetOrder());
      if (typeof window !== "undefined") {
        const generatorElem = document.getElementById("generador");
        if (generatorElem) {
          generatorElem.scrollIntoView({ behavior: "smooth" });
        } else {
          window.location.href = "/#generador";
        }
      }
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

  const telemetry = (orderData as any)?.metrics?.telemetry;

  const orderCurrency =
    (orderData as any)?.currency ||
    (orderData as any)?.payment?.currency ||
    (orderData as any)?.request?.currency ||
    "COP";
  const orderCountry =
    (orderData as any)?.request?.country ||
    (orderData as any)?.country ||
    "CO";
  const amountInCents =
    orderData?.amount_in_cents ||
    (orderData as any)?.payment?.amount_in_cents ||
    totalAmountInCents ||
    0;
  const orderAmount = amountInCents / 100;

  const formatOrderCurrency = (amount: number, curr: string = "COP") => {
    const c = (curr || "COP").toUpperCase();
    const locale = c === "DOP" ? "es-DO" : c === "USD" ? "en-US" : "es-CO";
    try {
      return new Intl.NumberFormat(locale, {
        style: "currency",
        currency: c,
        maximumFractionDigits: 0,
      }).format(amount);
    } catch {
      return `$${amount.toLocaleString()} ${c}`;
    }
  };

  // Dynamic progress percentage smoothly paced over estimated time or telemetry progress
  // In awaiting_payment, harvesting & verification are already complete (90%), awaiting instant unlock (100%)
  const getProgressPercent = () => {
    if (isPaid) return 100;
    if (isAwaitingPayment) return 90;
    if (telemetry?.progress_percent !== undefined && isProcessing) {
      return Math.min(89, Math.max(25, telemetry.progress_percent));
    }
    if (isProcessing) {
      const ratio = Math.min(1.0, elapsedSec / Math.max(estimatedTotalSec, 1));
      const paced = 25 + ratio * 64;
      return Math.min(89, Math.round(paced));
    }
    if (isQueued) return 15;
    return 10;
  };

  const progressPercent = getProgressPercent();
  const isStalled = isProcessing && elapsedSec > Math.max(estimatedTotalSec * 2, 90);

  const getStepStatus = (stepIndex: number) => {
    if (isPaid) return "completed";
    if (isAwaitingPayment) {
      if (stepIndex <= 3) return "completed";
      if (stepIndex === 4) return "active";
      return "pending";
    }
    if (isProcessing) {
      if (stepIndex <= 2) return "completed";
      if (stepIndex === 3) return "active";
      return "pending";
    }
    if (isQueued) {
      if (stepIndex === 1) return "active";
      return "pending";
    }
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
                ? dict.tracker.failedTitle
                : isAwaitingPayment
                ? dict.tracker.readyToUnlockTitle
                : dict.tracker.processingTitle}
            </h3>
            <div className="tracker-ref-row">
              <span className="tracker-ref-label">{dict.tracker.orderRefLabel}</span>
              <strong className="tracker-ref-id">{activeOrderId}</strong>
              <button
                onClick={handleCopyOrderId}
                className="copy-id-btn"
                title={dict.tracker.copyId}
                type="button"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? dict.tracker.copiedId : dict.tracker.copyId}</span>
              </button>
              <button
                onClick={handleCopyApprovalLink}
                className="copy-id-btn"
                title={dict.tracker.shareLink}
                type="button"
              >
                {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Share2 className="w-3.5 h-3.5 text-sky-400" />}
                <span>{copiedLink ? dict.tracker.linkCopied : dict.tracker.shareLink}</span>
              </button>
            </div>
          </div>
        </div>

        <div className="tracker-action-buttons">
          <button
            onClick={() => refetch()}
            className={`tracker-icon-btn ${isFetching ? "animate-spin" : ""}`}
            title={dict.tracker.refreshTooltip}
            type="button"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleNewOrder}
            className="tracker-new-search-btn"
            title={dict.tracker.newSearch}
            type="button"
          >
            <PlusCircle className="w-4 h-4" />
            <span>{dict.tracker.newSearch}</span>
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
                <span className="shareable-quote-title">{dict.tracker.shareableApprovalTitle}</span>
                <span className="shareable-quote-badge">
                  {isPaid
                    ? dict.tracker.shareableApprovalBadgePaid
                    : isAwaitingPayment
                    ? dict.tracker.shareableApprovalBadgeReady
                    : dict.tracker.shareableApprovalBadgeQualifying}
                </span>
              </div>
              <p className="shareable-quote-desc">
                {dict.tracker.shareableApprovalDesc}
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
              <span>{copiedLink ? dict.tracker.copiedId : dict.tracker.copyId}</span>
            </button>
            <a
              href={`https://wa.me/?text=${encodeURIComponent(`${dict.tracker.shareWhatsappText} ${getShareableApprovalUrl()}`)}`}
              target="_blank"
              rel="noreferrer"
              className="btn-quote-whatsapp"
              title="WhatsApp"
            >
              <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />
              <span>WhatsApp</span>
            </a>
          </div>
        </div>
      </div>

      {/* Prominent Async Handoff Reassurance Card during Cold Search */}
      {(isProcessing || isQueued) && (() => {
        const email = (orderData as any)?.client?.email || (orderData as any)?.customer_email || "";
        const phone = (orderData as any)?.client?.phone || (orderData as any)?.customer_phone || "";
        return (
          <div className="async-handoff-banner" data-testid="async-handoff-card">
            <div className="async-handoff-icon-wrapper">
              <Mail className="w-6 h-6 text-sky-400" />
            </div>
            <div className="async-handoff-body">
              <div className="async-handoff-title-row">
                <h4 className="async-handoff-title">
                  {dict.tracker.handoffTitle || "¡Solicitud Recibida! Tu auditoría está en marcha"}
                </h4>
                <span className="async-handoff-badge">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse inline-block mr-1.5" />
                  {dict.tracker.statusHarvesting}
                </span>
              </div>
              <p className="async-handoff-desc">
                {dict.tracker.handoffDesc || "Estamos consultando registros oficiales y auditando buzones corporativos en tiempo real. Debido al volumen de validación profunda, este proceso toma entre 3 y 5 minutos."}
              </p>
              <div className="async-handoff-notify-box">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>
                  {dict.tracker.handoffNotification || "Te notificaremos por correo"}
                  {email ? ` (${email})` : ""}
                  {phone ? ` y WhatsApp (${phone})` : ""}
                  {" en cuanto tu cotización final exacta y tu muestra estén listas."}
                </span>
              </div>
              <p className="async-handoff-reassurance">
                {dict.tracker.handoffReassurance || "Puedes cerrar esta ventana con total tranquilidad. Si prefieres seguir el progreso en vivo, mantén abierta esta pestaña."}
              </p>
            </div>
          </div>
        );
      })()}

      {/* Real-Time Progress Bar & Timer */}
      <div className="tracker-progress-block">
        <div className="progress-bar-header">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-300">
              {isPaid
                ? dict.tracker.deliveryConfirmed
                : isAwaitingPayment
                ? dict.tracker.teaserSampleQualified
                : isProcessing
                ? targetTier === 3
                  ? dict.tracker.auditingFinancials
                  : dict.tracker.checkingWebAndMx
                : dict.tracker.orderQueued}
            </span>
          </div>

          {isQueued || isProcessing ? (
            <div className="tracker-timer-chip">
              <Clock className="w-3 h-3 text-sky-400" />
              <span>{dict.tracker.elapsedLabel} {formatTimeDisplay(elapsedSec)} ({dict.tracker.estimatedPrefix} {formatEstDisplay(estimatedTotalSec)})</span>
            </div>
          ) : elapsedSec > 0 ? (
            <div className="tracker-timer-chip">
              <Clock className="w-3 h-3 text-emerald-400" />
              <span>{dict.tracker.qualificationTimeLabel} {formatTimeDisplay(elapsedSec)}</span>
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
                {dict.tracker.batchProcessingTitle}
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed mt-1 mb-0">
              {dict.tracker.batchProcessingNotice.replace("{orderId}", activeOrderId || "")}
            </p>
          </div>
        )}

        {isStalled && (
          <div className="tracker-stalled-banner mt-3 p-3 rounded-lg border border-amber-500/30 bg-amber-500/10 flex items-center justify-between text-xs text-amber-200">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>{dict.tracker.stalledNotice || "La validación está tomando unos segundos adicionales. Estamos confirmando los últimos contactos..."}</span>
            </div>
            <button
              onClick={() => refetch()}
              className="px-2.5 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 font-medium transition-colors cursor-pointer"
              type="button"
            >
              {dict.tracker.refreshBtn || "Actualizar"}
            </button>
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
                {dict.tracker.failedCardTitle}
              </h4>
              <p className="order-failed-desc">
                {orderData?.error_message || errorMessage || dict.tracker.failedCardFallback}
              </p>
              <div className="order-failed-actions">
                <button
                  onClick={handleNewOrder}
                  className="order-failed-btn"
                  type="button"
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>{dict.tracker.failedCardBtn}</span>
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
            <span>{dict.tracker.radarTitle}</span>
          </div>
          <div className="radar-grid">
            <div className="radar-item active">
              <Building2 className="w-4 h-4 text-sky-400" />
              <div>
                <div className="radar-item-title">{dict.tracker.radarRegistries}</div>
                <div className="radar-item-sub">{dict.tracker.radarRegistriesSub}</div>
              </div>
            </div>
            <div className={`radar-item ${isProcessing ? "active" : ""}`}>
              <Globe className="w-4 h-4 text-emerald-400" />
              <div>
                <div className="radar-item-title">{dict.tracker.radarWeb}</div>
                <div className="radar-item-sub">{dict.tracker.radarWebSub}</div>
              </div>
            </div>
            <div className={`radar-item ${isProcessing ? "active" : ""}`}>
              <Mail className="w-4 h-4 text-purple-400" />
              <div>
                <div className="radar-item-title">{dict.tracker.radarMx}</div>
                <div className="radar-item-sub">{dict.tracker.radarMxSub}</div>
              </div>
            </div>
            <div className={`radar-item ${isProcessing ? "active" : ""}`}>
              <ShieldCheck className="w-4 h-4 text-amber-400" />
              <div>
                <div className="radar-item-title">{dict.tracker.radarSolvency}</div>
                <div className="radar-item-sub">{dict.tracker.radarSolvencySub}</div>
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
              {isCourtesyDelivered && (
                <div style={{ marginBottom: "6px" }}>
                  <span className="payment-cta-badge">OBSEQUIO DE CORTESÍA • $0 COP</span>
                </div>
              )}
              <h4 className="text-lg font-bold text-white">
                {isCourtesyDelivered
                  ? "Lote de Cortesía ($0 COP) - Entregables Desbloqueados"
                  : dict.tracker.deliverablesTitle}
              </h4>
              <p className="text-sm text-slate-300">
                {isCourtesyDelivered
                  ? `Identificamos menos de 3 empresas verificadas (${(orderData as any)?.verified_yield || orderData?.total_qualified || 2} empresas). Michito te obsequia estos contactos verificados 100% gratis sin requerir pago.`
                  : dict.tracker.deliverablesSub}
              </p>
            </div>
          </div>

          <div className="download-buttons-grid">
            {/* 1. Styled XLSX */}
            <a
              href={`/api/v1/orders/${activeOrderId}/download/xlsx`}
              download
              className="download-btn xlsx-download"
              target="_blank"
              rel="noreferrer"
            >
              <div className="download-btn-icon xlsx-icon">
                <FileSpreadsheet className="w-5 h-5" />
              </div>
              <div className="download-btn-info">
                <div className="download-btn-title">{dict.tracker.dlXlsxTitle}</div>
                <div className="download-btn-sub">{dict.tracker.dlXlsxSub}</div>
              </div>
            </a>

            {/* 2. Executive PDF Dossier */}
            <a
              href={`/api/v1/orders/${activeOrderId}/download/pdf`}
              download
              className="download-btn pdf-download"
              target="_blank"
              rel="noreferrer"
            >
              <div className="download-btn-icon pdf-icon">
                <FileText className="w-5 h-5" />
              </div>
              <div className="download-btn-info">
                <div className="download-btn-title">{dict.tracker.dlPdfTitle}</div>
                <div className="download-btn-sub">{dict.tracker.dlPdfSub}</div>
              </div>
            </a>

            {/* 3. CRM-Clean CSV */}
            <a
              href={`/api/v1/orders/${activeOrderId}/download/csv`}
              download
              className="download-btn csv-download"
              target="_blank"
              rel="noreferrer"
            >
              <div className="download-btn-icon csv-icon">
                <Download className="w-5 h-5" />
              </div>
              <div className="download-btn-info">
                <div className="download-btn-title">{dict.tracker.dlCsvTitle}</div>
                <div className="download-btn-sub">{dict.tracker.dlCsvSub}</div>
              </div>
            </a>
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
                    <h5 className="text-sm font-bold text-white">{dict.tracker.guaranteeBannerTitle}</h5>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-500/40">
                      {dict.tracker.guaranteeBannerBadge}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 mt-0.5">
                    {dict.tracker.guaranteeBannerDesc}
                  </p>
                  {orderData?.replacement_claims && orderData.replacement_claims.length > 0 && (
                    <div className="text-xs text-emerald-400 font-medium mt-1">
                      {dict.tracker.guaranteeBannerApplied
                        .replace("{claims}", String(orderData.replacement_claims.length))
                        .replace(
                          "{accounts}",
                          String(
                            orderData.replacement_claims.reduce(
                              (acc: number, c: any) => acc + (c.replacement_count || 2),
                              0
                            )
                          )
                        )}
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
                <span>{dict.tracker.guaranteeClaimBtn}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Prominent Payment Authorization Banner when awaiting payment */}
      {isAwaitingPayment && (() => {
        const verifiedYield =
          (orderData as any)?.verified_yield ||
          (orderData as any)?.delivery?.verified_yield ||
          orderData?.total_qualified ||
          totalLeadsTarget;
        const requestedLimit =
          (orderData as any)?.request?.limit ||
          (orderData as any)?.limit ||
          totalLeadsTarget;
        const hasQuotaAdjustment =
          verifiedYield > 0 && requestedLimit > 0 && verifiedYield < requestedLimit;

        return (
          <div
            className="payment-authorization-card"
            data-testid="payment-authorization-card"
          >
            {hasQuotaAdjustment && (
              <div className="fair-price-adjustment-banner">
                <ShieldCheck className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="fair-price-banner-title">
                    {currentLanguage === "en_US" ? "Automatic Fair Price Adjustment" : "Ajuste Automático por Cobro Justo"}
                  </strong>
                  <p className="fair-price-banner-desc">
                    {currentLanguage === "en_US"
                      ? `You requested ${requestedLimit} accounts, but only ${verifiedYield} companies met our legal registration, active website, and verified corporate inbox standards. In compliance with our Fair Price Policy, your quote was automatically reduced to strictly charge you for ${verifiedYield} accounts.`
                      : `Solicitaste ${requestedLimit} cuentas, pero únicamente ${verifiedYield} empresas cumplieron con nuestros estándares legales, presencia web y buzón corporativo activo. En cumplimiento de nuestra Política de Cobro Justo, tu cotización se redujo automáticamente para cobrarte estrictamente por las ${verifiedYield} cuentas verificadas.`}
                  </p>
                </div>
              </div>
            )}

            <div className="payment-cta-layout">
              <div className="payment-cta-left">
                <div className="payment-cta-icon-box">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <div>
                  <div className="payment-cta-heading-row">
                    <h4 className="payment-cta-title">
                      {dict.tracker.paymentCtaTitle || "Lote Auditado y Listo para Descarga Inmediata"}
                    </h4>
                    <span className="payment-cta-badge">
                      {verifiedYield} {dict.tracker.verifiedUnits || "Cuentas Verificadas"}
                    </span>
                  </div>
                  <p className="payment-cta-desc">
                    {(dict.tracker.paymentCtaDesc || "Identificamos y verificamos {verified} empresas activas que superaron nuestros filtros técnicos de validación. Revisa la muestra a continuación. Al confirmar tu pago, tus archivos Excel (.xlsx), CSV y Dossier PDF se desbloquean inmediatamente sin esperas.")
                      .replace("{verified}", String(verifiedYield))
                      .replace("{total}", String(verifiedYield))}
                  </p>
                  <div className="payment-cta-guarantee-line">
                    <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
                    <span>
                      {(dict.tracker.paymentCtaGuarantee || "Política de Cobro Justo: Solo pagas por cuentas verificadas ({verified} cuentas). Sin suscripciones ni créditos que expiran.")
                        .replace("{verified}", String(verifiedYield))}
                    </span>
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={() => dispatch(setWompiModalOpen(true))}
                className="main-payment-cta-btn"
                data-testid="main-payment-cta-btn"
              >
                <CreditCard className="w-5 h-5" />
                <span>
                  {(dict.tracker.paymentCtaBtn || "Pagar y Desbloquear Lote ({amount})")
                    .replace("{amount}", formatOrderCurrency(orderAmount, orderCurrency))}
                </span>
              </button>
            </div>
          </div>
        );
      })()}

      {/* View Switcher Tabs: Summary Table vs Interactive Outreach Playbook */}
      {(isAwaitingPayment || isPaid) && (
        <div className="tracker-views-container">
          {playbook && playbook.length > 0 && (
            <div className="tracker-view-tabs">
              <button
                type="button"
                onClick={() => setActiveViewTab("summary")}
                className={`tracker-view-tab-btn ${activeViewTab === "summary" ? "active" : ""}`}
              >
                {dict.tracker.tabSummary}
              </button>
              <button
                type="button"
                onClick={() => setActiveViewTab("playbook")}
                className={`tracker-view-tab-btn ${activeViewTab === "playbook" ? "active" : ""}`}
              >
                <span>{dict.tracker.tabPlaybook}</span>
                <span className="tracker-tab-badge">
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
              totalAmountCop={orderAmount}
              currency={orderCurrency}
              country={orderCountry}
              requestedLeads={(orderData as any)?.request?.limit || orderData?.limit}
              isPaid={isPaid}
              xlsxUrl={xlsxDownloadUrl || (orderData as any)?.xlsx_download_url}
              csvUrl={csvDownloadUrl || orderData?.csv_download_url}
              pdfUrl={pdfDownloadUrl || (orderData as any)?.pdf_download_url}
              fullCsvUrl={fullCsvDownloadUrl || (orderData as any)?.full_csv_download_url}
              activeOrderId={activeOrderId}
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

            <div className="claim-modal-header">
              <div className="claim-modal-icon-box">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h4 className="claim-modal-title">{dict.tracker.guaranteeModalTitle}</h4>
                <p className="claim-modal-sub">{dict.tracker.guaranteeModalSub}</p>
              </div>
            </div>

            <p className="claim-modal-desc">
              {dict.tracker.guaranteeModalDesc}
            </p>

            {claimSuccess && (
              <div className="claim-alert-success">
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                <span>{claimSuccess}</span>
              </div>
            )}

            {claimError && (
              <div className="claim-alert-error">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{claimError}</span>
              </div>
            )}

            <form onSubmit={handleClaimSubmit} className="claim-form-stack">
              <div>
                <label className="claim-form-label">
                  {dict.tracker.guaranteeModalEmailLabel}
                </label>
                <input
                  type="email"
                  required
                  placeholder={dict.tracker.guaranteeModalEmailPlaceholder}
                  value={claimEmail}
                  onChange={(e) => setClaimEmail(e.target.value)}
                  className="claim-form-input"
                />
                {teaserLeads && teaserLeads.length > 0 && (
                  <div className="claim-suggested-row">
                    <span className="claim-suggested-label">{dict.tracker.guaranteeModalSuggested}</span>
                    {teaserLeads.slice(0, 4).map((l, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => {
                          setClaimEmail(l.email);
                          if (l.company_name) setClaimCompany(l.company_name);
                        }}
                        className="claim-suggested-btn"
                      >
                        {l.email}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <label className="claim-form-label">
                  {dict.tracker.guaranteeModalCompanyLabel}
                </label>
                <input
                  type="text"
                  placeholder={dict.tracker.guaranteeModalCompanyPlaceholder}
                  value={claimCompany}
                  onChange={(e) => setClaimCompany(e.target.value)}
                  className="claim-form-input"
                />
              </div>

              <div>
                <label className="claim-form-label">
                  {dict.tracker.guaranteeModalReasonLabel}
                </label>
                <select
                  value={claimReason}
                  onChange={(e) => setClaimReason(e.target.value)}
                  className="claim-form-select"
                >
                  <option value="hard_bounce">{dict.tracker.guaranteeReasonHardBounce}</option>
                  <option value="domain_dead">{dict.tracker.guaranteeReasonDeadDomain}</option>
                  <option value="left_company">{dict.tracker.guaranteeReasonLeftCompany}</option>
                  <option value="mailbox_full">{dict.tracker.guaranteeReasonMailboxFull}</option>
                </select>
              </div>

              <div className="claim-modal-footer">
                <button
                  type="button"
                  onClick={() => setShowGuaranteeModal(false)}
                  className="claim-cancel-btn"
                >
                  {dict.tracker.guaranteeModalClose}
                </button>
                <button
                  type="submit"
                  disabled={isClaiming || !claimEmail.trim()}
                  className="claim-submit-btn"
                >
                  {isClaiming ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>{dict.tracker.guaranteeModalGenerating}</span>
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>{dict.tracker.guaranteeModalSubmit}</span>
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

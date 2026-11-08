import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "../../store";
import { updateOrderStatus } from "../../store/slices/orderSlice";
import { useGetOrderQuery } from "../../store/api/michitoApi";
import { SampleTeaserTable } from "./SampleTeaserTable";
import { CheckCircle2, Loader2, Download, FileSpreadsheet, FileText, Sparkles, RefreshCw } from "lucide-react";

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

  // Poll every 3 seconds while active order is not finalized
  const shouldPoll = activeOrderId !== null && orderStatus !== "paid" && orderStatus !== "error";
  const { data: orderData, refetch } = useGetOrderQuery(activeOrderId || "", {
    skip: !activeOrderId,
    pollingInterval: shouldPoll ? 3000 : 0,
  });

  useEffect(() => {
    if (orderData) {
      dispatch(
        updateOrderStatus({
          status: orderData.status,
          teaserLeads: orderData.sample_leads,
          csvUrl: orderData.csv_download_url,
          dossierUrl: orderData.dossier_download_url,
        })
      );
    }
  }, [orderData, dispatch]);

  if (!activeOrderId) return null;

  const isQueued = orderStatus === "queued";
  const isProcessing = orderStatus === "processing";
  const isAwaitingPayment = orderStatus === "awaiting_payment";
  const isPaid = orderStatus === "paid";

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
    <div className="tracker-card">
      <div className="tracker-header">
        <div className="flex items-center gap-3">
          <div className="tracker-spinner">
            {!isPaid ? (
              <Loader2 className="w-5 h-5 text-sky-400 animate-spin" />
            ) : (
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            )}
          </div>
          <div>
            <h3 className="tracker-title">
              {isPaid
                ? dict.tracker.completedTitle
                : dict.tracker.processingTitle}
            </h3>
            <p className="tracker-ref">
              {dict.tracker.orderRef} <span className="font-mono text-sky-300">{activeOrderId}</span>
            </p>
          </div>
        </div>

        <button onClick={() => refetch()} className="tracker-refresh-btn" title="Refrescar estado">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Progress timeline */}
      <div className="timeline-container">
        {steps.map((st, i) => {
          const status = getStepStatus(i + 1);
          return (
            <div key={i} className={`timeline-step step-${status}`}>
              <div className="step-bubble">
                {status === "completed" ? (
                  <CheckCircle2 className="w-4 h-4" />
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
                Los enlaces firmados de Cloud Storage están activos por 48 horas.
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
              <button className="download-btn csv-download" disabled>
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
              <button className="download-btn dossier-download" disabled>
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


import React from "react";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "../../store";
import { setWompiModalOpen } from "../../store/slices/uiSlice";
import { TeaserLead } from "../../store/slices/orderSlice";
import {
  ShieldCheck,
  Mail,
  Phone,
  Lock,
  CreditCard,
  Info,
  CheckCircle2,
  FileSpreadsheet,
  Download,
  FileText,
  Database,
} from "lucide-react";

interface SampleTeaserTableProps {
  leads: TeaserLead[];
  totalLeads: number;
  totalAmountCop: number;
  currency?: string;
  country?: string;
  requestedLeads?: number;
  isPaid?: boolean;
  xlsxUrl?: string | null;
  csvUrl?: string | null;
  pdfUrl?: string | null;
  fullCsvUrl?: string | null;
  activeOrderId?: string | null;
}

export const SampleTeaserTable: React.FC<SampleTeaserTableProps> = ({
  leads,
  totalLeads,
  totalAmountCop,
  currency = "COP",
  country,
  requestedLeads,
  isPaid,
  xlsxUrl,
  csvUrl,
  pdfUrl,
  fullCsvUrl,
  activeOrderId,
}) => {
  const dispatch = useDispatch();
  const { dict } = useSelector((state: RootState) => state.language);

  const formatMoney = (amount: number, curr: string = "COP") => {
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

  const formatTaxId = (taxId?: string, countryCode?: string) => {
    if (!taxId) return null;
    const trimmed = taxId.trim();
    const upper = trimmed.toUpperCase();
    if (
      upper.startsWith("RNC") ||
      upper.startsWith("RUC") ||
      upper.startsWith("RUT") ||
      upper.startsWith("NIT")
    ) {
      return trimmed;
    }
    const c = (countryCode || "").toUpperCase();
    const prefix = c === "DO" ? "RNC" : c === "EC" ? "RUC" : c === "CL" ? "RUT" : "NIT";
    return `${prefix}: ${trimmed}`;
  };

  const isPartialFill = Boolean(requestedLeads && requestedLeads > totalLeads);

  return (
    <div className="teaser-container">
      {isPartialFill && (
        <div className="fair-price-adjustment-banner" style={{ marginBottom: "16px" }}>
          <Info className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
          <div className="fair-price-banner-desc">
            {dict.tracker.fairBillingNotice
              .replace("{requested}", String(requestedLeads))
              .replace("{delivered}", String(totalLeads))}
          </div>
        </div>
      )}

      <div className="teaser-header">
        <h3 className="teaser-title">
          {dict.tracker.teaserTitle.replace("{total}", String(totalLeads))}
        </h3>
        <p className="teaser-subtitle">{dict.tracker.teaserSubtitle}</p>
      </div>

      {/* Horizontal Scrollable Table Wrapper */}
      <div className="teaser-table-wrapper">
        <table className="teaser-table">
          <thead>
            <tr>
              <th>{dict.tracker.colCompany}</th>
              <th>{dict.tracker.colRole}</th>
              <th>{dict.tracker.colEmail}</th>
              <th>{dict.tracker.colPhone}</th>
              <th>{dict.tracker.colTrigger}</th>
              <th>{dict.tracker.colSolvency}</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((lead, idx) => (
              <tr key={idx}>
                <td className="font-semibold text-white">
                  <div className="flex items-center gap-2">
                    <span>{lead.company_name}</span>
                    {lead.is_guarantee_replacement && (
                      <span className="payment-cta-badge">
                        {dict.tracker.guarantee2x1Badge}
                      </span>
                    )}
                  </div>
                  {lead.nit && (
                    <span className="text-xs text-slate-400 font-mono">
                      {formatTaxId(lead.nit, country)}
                    </span>
                  )}
                </td>
                <td>
                  <div>{lead.decision_maker_name || dict.tracker.contactInstitutional}</div>
                  <div className="text-xs text-sky-400">
                    {lead.decision_maker_role || (lead as any).decision_maker_title || dict.tracker.roleLegalRep}
                  </div>
                </td>
                <td>
                  <span className="email-masked-badge">
                    <Mail className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>{lead.email || "c***@empresa.com"}</span>
                  </span>
                </td>
                <td>
                  <span className="phone-masked-badge">
                    <Phone className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>{lead.phone || "+57 3•• ••• ••••"}</span>
                  </span>
                </td>
                <td>
                  <span className="intent-badge">
                    {lead.intent_trigger || (lead as any).intent_level || dict.tracker.recentAward}
                  </span>
                </td>
                <td>
                  {lead.solvency_tier ? (
                    <span className="solvency-badge">
                      <ShieldCheck className="w-3 h-3 text-emerald-400 inline mr-1" />
                      {lead.solvency_tier} • {lead.underwriting_grade || "AAA"}
                    </span>
                  ) : (
                    <span className="text-xs text-slate-400">{dict.tracker.verified}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Unlock / Pay Action Bar or Instant Deliverables Download Receipt */}
      {isPaid ? (
        <div className="teaser-unlocked-receipt-bar">
          <div className="receipt-bar-left">
            <div className="receipt-bar-icon-box">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <div className="receipt-bar-title">
                <span>{dict.tracker.unlockedBarTitle.replace("{total}", String(totalLeads))}</span>
                <span className="receipt-bar-badge">
                  {dict.tracker.unlockedBarBadge}
                </span>
              </div>
              <p className="receipt-bar-sub">
                {dict.tracker.unlockedBarSub}
              </p>
            </div>
          </div>

          <div className="receipt-bar-actions">
            {(xlsxUrl || csvUrl) && (
              <a
                href={xlsxUrl || `/api/v1/orders/${activeOrderId}/download/xlsx`}
                download
                className="btn-receipt-download primary"
                target="_blank"
                rel="noreferrer"
              >
                <FileSpreadsheet className="w-4 h-4" />
                <span>Excel (.XLSX)</span>
              </a>
            )}
            {csvUrl && (
              <a
                href={csvUrl}
                download
                className="btn-receipt-download secondary"
                target="_blank"
                rel="noreferrer"
              >
                <Download className="w-4 h-4" />
                <span>CSV</span>
              </a>
            )}
            {pdfUrl && (
              <a
                href={pdfUrl || `/api/v1/orders/${activeOrderId}/download/pdf`}
                download
                className="btn-receipt-download secondary"
                target="_blank"
                rel="noreferrer"
              >
                <FileText className="w-4 h-4" />
                <span>Dossier PDF</span>
              </a>
            )}
            {fullCsvUrl && (
              <a
                href={fullCsvUrl || `/api/v1/orders/${activeOrderId}/download/full_csv`}
                download
                className="btn-receipt-download secondary"
                target="_blank"
                rel="noreferrer"
              >
                <Database className="w-4 h-4" />
                <span>{dict.tracker.dlFullCsvTitle}</span>
              </a>
            )}
          </div>
        </div>
      ) : (
        <div className="teaser-unlock-bar">
          <div className="unlock-info">
            <Lock className="w-5 h-5 text-amber-400" />
            <span>
              {totalLeads > leads.length
                ? dict.tracker.unlockRemaining.replace(
                    "{remaining}",
                    String(totalLeads - leads.length)
                  )
                : "Completa el pago para desbloquear el lote completo y descargar tus archivos."}
            </span>
          </div>
          <button
            type="button"
            onClick={() => dispatch(setWompiModalOpen(true))}
            className="teaser-pay-btn"
            data-testid="teaser-pay-btn"
          >
            <CreditCard className="w-5 h-5" />
            <span>
              {isPartialFill
                ? dict.tracker.unlockPartialBtn
                    .replace("{total}", String(totalLeads))
                    .replace("{amount}", formatMoney(totalAmountCop, currency))
                : dict.tracker.unlockBtn.replace("{amount}", formatMoney(totalAmountCop, currency))}
            </span>
          </button>
        </div>
      )}
    </div>
  );
};


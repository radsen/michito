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
        <div className="mb-4 p-3 rounded-lg bg-sky-950/40 border border-sky-500/30 flex items-start gap-2.5">
          <Info className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
          <div className="text-xs text-slate-300">
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
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950/80 border border-emerald-500/50 text-emerald-300 font-semibold">
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
        <div className="teaser-unlocked-receipt-bar p-4 rounded-xl bg-emerald-950/60 border border-emerald-500/50 mt-4 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center shrink-0">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <div className="text-sm font-bold text-white flex items-center gap-2">
                <span>{dict.tracker.unlockedBarTitle.replace("{total}", String(totalLeads))}</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-900/80 text-emerald-300 border border-emerald-500/30">
                  {dict.tracker.unlockedBarBadge}
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-0.5 mb-0">
                {dict.tracker.unlockedBarSub}
              </p>
            </div>
          </div>

          <div className="flex items-center flex-wrap gap-2">
            {(xlsxUrl || csvUrl) && (
              <a
                href={xlsxUrl || `/api/v1/orders/${activeOrderId}/download/xlsx`}
                download
                className="px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center gap-1.5 transition-colors shadow-sm"
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
                className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-xs flex items-center gap-1.5 transition-colors"
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
                className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-xs flex items-center gap-1.5 transition-colors"
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
                className="px-3 py-2 rounded-lg bg-indigo-950/60 hover:bg-indigo-900/80 text-indigo-300 border border-indigo-500/40 font-semibold text-xs flex items-center gap-1.5 transition-colors"
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
              {dict.tracker.unlockRemaining.replace(
                "{remaining}",
                String(Math.max(1, totalLeads - leads.length))
              )}
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


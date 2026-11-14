import React from "react";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "../../store";
import { setWompiModalOpen } from "../../store/slices/uiSlice";
import { TeaserLead } from "../../store/slices/orderSlice";
import { ShieldCheck, Mail, Phone, Lock, CreditCard, Info } from "lucide-react";

interface SampleTeaserTableProps {
  leads: TeaserLead[];
  totalLeads: number;
  totalAmountCop: number;
  requestedLeads?: number;
}

export const SampleTeaserTable: React.FC<SampleTeaserTableProps> = ({
  leads,
  totalLeads,
  totalAmountCop,
  requestedLeads,
}) => {
  const dispatch = useDispatch();
  const { dict } = useSelector((state: RootState) => state.language);

  const formatCop = (amount: number) => {
    return new Intl.NumberFormat("es-CO", {
      style: "currency",
      currency: "COP",
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const isPartialFill = Boolean(requestedLeads && requestedLeads > totalLeads);

  return (
    <div className="teaser-container">
      {isPartialFill && (
        <div className="mb-4 p-3 rounded-lg bg-sky-950/40 border border-sky-500/30 flex items-start gap-2.5">
          <Info className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
          <div className="text-xs text-slate-300">
            <span className="font-semibold text-sky-300">Garantía de Cobro Justo: </span>
            Se solicitaron {requestedLeads} cuentas y se entregaron {totalLeads} cuentas que superaron el 100% de los filtros de solvencia, buzón activo y presencia web. Únicamente pagarás por las cuentas verificadas con éxito.
          </div>
        </div>
      )}

      <div className="teaser-header">
        <h3 className="teaser-title">
          Muestra de Cuentas Identificadas (3 de {totalLeads})
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
                        Garantía 2x1
                      </span>
                    )}
                  </div>
                  {lead.nit && <span className="text-xs text-slate-400 font-mono">NIT: {lead.nit}</span>}
                </td>
                <td>
                  <div>{lead.decision_maker_name || "Contacto Institucional"}</div>
                  <div className="text-xs text-sky-400">
                    {lead.decision_maker_role || (lead as any).decision_maker_title || "Representante Legal"}
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
                    {lead.intent_trigger || (lead as any).intent_level || "Adjudicación Contrato Reciente"}
                  </span>
                </td>
                <td>
                  {lead.solvency_tier ? (
                    <span className="solvency-badge">
                      <ShieldCheck className="w-3 h-3 text-emerald-400 inline mr-1" />
                      {lead.solvency_tier} • {lead.underwriting_grade || "AAA"}
                    </span>
                  ) : (
                    <span className="text-xs text-slate-400">Verificado</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Unlock / Pay Action Bar */}
      <div className="teaser-unlock-bar">
        <div className="unlock-info">
          <Lock className="w-5 h-5 text-amber-400" />
          <span>
            Las {Math.max(1, totalLeads - leads.length)} cuentas restantes y los correos completos se desbloquean con el pago.
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
              ? `Desbloquear ${totalLeads} Cuentas Verificadas (${formatCop(totalAmountCop)})`
              : `Desbloquear Lote Completo (${formatCop(totalAmountCop)})`}
          </span>
        </button>
      </div>
    </div>
  );
};


import React from "react";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "../../store";
import { setWompiModalOpen } from "../../store/slices/uiSlice";
import { TeaserLead } from "../../store/slices/orderSlice";
import { ShieldCheck, Mail, Phone, Lock, CreditCard } from "lucide-react";

interface SampleTeaserTableProps {
  leads: TeaserLead[];
  totalLeads: number;
  totalAmountCop: number;
}

export const SampleTeaserTable: React.FC<SampleTeaserTableProps> = ({
  leads,
  totalLeads,
  totalAmountCop,
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

  return (
    <div className="teaser-container">
      <div className="teaser-header">
        <h3 className="teaser-title">
          🎯 Muestra de Cuentas Identificadas (3 de {totalLeads})
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
                  <div>{lead.company_name}</div>
                  {lead.nit && <span className="text-xs text-slate-400">NIT: {lead.nit}</span>}
                </td>
                <td>
                  <div>{lead.decision_maker_name || "Directivo Clave"}</div>
                  <div className="text-xs text-sky-400">
                    {lead.decision_maker_role || (lead as any).decision_maker_title || "Tomador de Decisión"}
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
          onClick={() => dispatch(setWompiModalOpen(true))}
          className="teaser-pay-btn"
        >
          <CreditCard className="w-5 h-5" />
          <span>Desbloquear Lote Completo ({formatCop(totalAmountCop)})</span>
        </button>
      </div>
    </div>
  );
};


import React, { useEffect } from "react";
import { useSelector } from "react-redux";
import { RootState } from "../../store";
import { ShieldCheck, Scale, FileText, ArrowLeft, CheckCircle2 } from "lucide-react";

interface TermsPageProps {
  onBack: () => void;
}

export const TermsPage: React.FC<TermsPageProps> = ({ onBack }) => {
  const { dict } = useSelector((state: RootState) => state.language);
  const d = dict.deliverables;

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  return (
    <div className="legal-page-container">
      <div className="section-container max-w-4xl py-12 px-6">
        {/* Back Link */}
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 text-sm text-sky-400 hover:text-sky-300 font-semibold mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Volver a la plataforma principal</span>
        </button>

        <div className="legal-header mb-10 pb-6 border-b border-slate-800">
          <span className="section-kicker">Marco Jurídico & Operativo</span>
          <h1 className="text-3xl font-extrabold text-white mt-2">
            Términos del Servicio, Garantía & Habeas Data
          </h1>
          <p className="text-sm text-slate-400 mt-2">
            Última actualización: Noviembre 2026 • Cobertura Comercial: Colombia y República Dominicana
          </p>
        </div>

        <div className="space-y-8 text-slate-300 text-sm leading-relaxed">
          {/* Section 1: Scope */}
          <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-9 h-9 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400">
                <FileText className="w-5 h-5" />
              </div>
              <h2 className="text-lg font-bold text-white">
                1. Delimitación de Alcance Comercial
              </h2>
            </div>
            <p className="mb-4">
              {d.disclaimerP1 ||
                "Michito es un proveedor de datos e inteligencia B2B calificada. Nuestra responsabilidad técnica y contractual consiste en entregar cuentas corporativas verificadas, canales de contacto válidos y cadencias estratégicas redactadas. Michito no es una agencia de ventas, no ejecuta llamadas en frío en nombre de terceros ni cobra comisiones por cierre."}
            </p>
            <p>
              {d.disclaimerP2 ||
                "La conversión comercial final, las reuniones agendadas y los negocios cerrados dependen de la propuesta de valor, la competitividad de precios, la agilidad de seguimiento y la habilidad de cierre del equipo comercial de cada cliente."}
            </p>
          </section>

          {/* Section 2: Technical Replacement Guarantee */}
          <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h2 className="text-lg font-bold text-white">
                2. Garantía Técnica de Reemplazo
              </h2>
            </div>
            <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 font-medium mb-4 flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" />
              <span>
                {d.replacementGuarantee ||
                  "Garantía Técnica de Reemplazo: Si algún buzón presenta rebote duro comprobable en los primeros 7 días de entrega, el sistema lo reemplaza sin costo por 2 cuentas verificadas."}
              </span>
            </div>
            <p>
              Para activar la garantía técnica de reemplazo, el cliente únicamente debe remitir el log técnico o cabecera de rebote (SMTP bounce notification) a nuestro canal de soporte dentro del periodo de 7 días naturales posteriores a la entrega del archivo.
            </p>
          </section>

          {/* Section 3: Habeas Data & Compliance */}
          <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
                <Scale className="w-5 h-5" />
              </div>
              <h2 className="text-lg font-bold text-white">
                3. Cumplimiento Normativo & Habeas Data Comercial
              </h2>
            </div>
            <p className="mb-4">
              <strong>Fuentes Institucionales Públicas:</strong> Michito recopila y procesa exclusivamente datos de naturaleza pública, institucional y comercial provenientes de registros mercantiles oficiales, portales de contratación pública y sitios web de empresas activas.
            </p>
            <p className="mb-4">
              <strong>Cumplimiento Legal:</strong> Todo tratamiento de información comercial se realiza en estricto apego a la <strong>Ley 1581 de 2012</strong> y Decreto 1377 de 2013 de la República de Colombia, y a la <strong>Ley 172-13</strong> sobre Protección de Datos de Carácter Personal de la República Dominicana.
            </p>
            <p>
              <strong>Garantía de Cobro Justo:</strong> El sistema factura exclusivamente por las cuentas corporativas que superan con éxito todos los filtros técnicos de calificación en vivo. Si una cuenta no pasa los filtros, no se debita de la orden del cliente.
            </p>
          </section>
        </div>

        {/* Bottom Back CTA */}
        <div className="mt-12 text-center">
          <button
            type="button"
            onClick={onBack}
            className="px-6 py-3 rounded-lg bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-sm transition-all shadow-lg shadow-sky-500/20"
          >
            ← Volver a la plataforma
          </button>
        </div>
      </div>
    </div>
  );
};

export default TermsPage;

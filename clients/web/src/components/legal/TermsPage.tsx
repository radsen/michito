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
      <div className="legal-page-content">
        {/* Back Link */}
        <button
          type="button"
          onClick={onBack}
          className="legal-back-btn"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Volver a la plataforma principal</span>
        </button>

        <div className="legal-header">
          <span className="section-kicker">Marco Jurídico & Operativo</span>
          <h1 className="legal-title">
            Términos del Servicio, Garantía & Habeas Data
          </h1>
          <p className="legal-subtitle">
            Última actualización: Noviembre 2026 • Cobertura Comercial: Colombia 🇨🇴, República Dominicana 🇩🇴, Ecuador 🇪🇨 y Mercados B2B 🌎
          </p>
        </div>

        <div className="legal-sections">
          {/* Section 1: Scope */}
          <section className="legal-card" id="terminos">
            <div className="legal-card-header">
              <div className="legal-card-icon" style={{ background: "rgba(56, 189, 248, 0.1)", border: "1px solid rgba(56, 189, 248, 0.3)", color: "var(--accent-blue)" }}>
                <FileText className="w-5 h-5" />
              </div>
              <h2 className="legal-card-title">
                1. Delimitación de Alcance Comercial
              </h2>
            </div>
            <div className="legal-card-body">
              <p>
                {d.disclaimerP1 ||
                  "Michito es un proveedor de datos e inteligencia B2B calificada. Nuestra responsabilidad técnica y contractual consiste en entregar cuentas corporativas verificadas, canales de contacto válidos y cadencias estratégicas redactadas. Michito no es una agencia de ventas, no ejecuta llamadas en frío en nombre de terceros ni cobra comisiones por cierre."}
              </p>
              <p>
                {d.disclaimerP2 ||
                  "La conversión comercial final, las reuniones agendadas y los negocios cerrados dependen de la propuesta de valor, la competitividad de precios, la agilidad de seguimiento y la habilidad de cierre del equipo comercial de cada cliente."}
              </p>
            </div>
          </section>

          {/* Section 2: Technical Replacement Guarantee */}
          <section className="legal-card" id="garantia">
            <div className="legal-card-header">
              <div className="legal-card-icon" style={{ background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", color: "var(--accent-emerald)" }}>
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h2 className="legal-card-title">
                2. Garantía Técnica de Reemplazo 2 por 1
              </h2>
            </div>
            <div className="legal-card-body">
              <div className="legal-guarantee-box">
                <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" />
                <span>
                  {d.replacementGuarantee ||
                    "Garantía Técnica de Reemplazo: Si algún buzón presenta rebote duro comprobable en los primeros 7 días de entrega, el sistema lo reemplaza sin costo por 2 cuentas verificadas."}
                </span>
              </div>
              <p>
                Para activar la garantía técnica de reemplazo, el cliente puede reportar el rebote duro directamente en el portal de seguimiento con su número de orden o remitir la notificación técnica de rebote SMTP. El sistema registrará el dominio en el ledger de exclusión y generará 2 nuevas cuentas verificadas con los mismos criterios de vertical y rol.
              </p>
              <p>
                <strong>Garantía de Cobro Justo:</strong> El sistema factura exclusivamente por las cuentas que superan el 100% de los filtros técnicos de calificación en vivo. Si un lote no alcanza el objetivo solicitado debido a filtros de calidad estrictos, las cuentas no calificadas se descuentan automáticamente del cobro final.
              </p>
            </div>
          </section>

          {/* Section 3: Habeas Data & Compliance */}
          <section className="legal-card" id="habeas-data">
            <div className="legal-card-header">
              <div className="legal-card-icon" style={{ background: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.3)", color: "var(--accent-amber)" }}>
                <Scale className="w-5 h-5" />
              </div>
              <h2 className="legal-card-title">
                3. Marco Jurídico por Territorio & Habeas Data Comercial
              </h2>
            </div>
            <div className="legal-card-body">
              <p>
                <strong>Fuentes Institucionales Públicas y Corporativas:</strong> Michito recopila y procesa exclusivamente información de naturaleza pública, mercantil y corporativa vinculada a personas jurídicas legalmente constituidas, portales estatales de contratación y sitios web corporativos en operación activa. No se procesan datos sensibles, datos crediticios reservados ni información de vida privada.
              </p>

              <div className="mt-4 space-y-4">
                <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800">
                  <h4 className="text-sm font-bold text-white flex items-center gap-2 mb-1.5">
                    <span>🇨🇴 Colombia — Ley 1581 de 2012 y Decreto 1377 de 2013</span>
                  </h4>
                  <p className="text-xs text-slate-300 leading-relaxed m-0">
                    Conforme al Artículo 10 de la Ley 1581 de 2012 y normas de la Superintendencia de Industria y Comercio (SIC), los datos de naturaleza pública contenidos en registros mercantiles oficiales (Cámaras de Comercio y RUES), como razón social, NIT, representantes legales estatutarios y datos de contacto institucional, no requieren autorización previa para su tratamiento con fines de contacto interempresarial (B2B).
                  </p>
                </div>

                <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800">
                  <h4 className="text-sm font-bold text-white flex items-center gap-2 mb-1.5">
                    <span>🇩🇴 República Dominicana — Ley 172-13</span>
                  </h4>
                  <p className="text-xs text-slate-300 leading-relaxed m-0">
                    En cumplimiento de la Ley 172-13 sobre Protección Integral de los Datos Personales, la recopilación se limita a datos de personas jurídicas inscritas en el Registro Mercantil y registros públicos de proveedores del Estado administrados por la Dirección General de Contrataciones Públicas (DGCP).
                  </p>
                </div>

                <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800">
                  <h4 className="text-sm font-bold text-white flex items-center gap-2 mb-1.5">
                    <span>🇪🇨 Ecuador — Ley Orgánica de Protección de Datos Personales (LOPDP)</span>
                  </h4>
                  <p className="text-xs text-slate-300 leading-relaxed m-0">
                    Bajo el principio de legitimidad y transparencia de la LOPDP, los datos procesados provienen de información comercial y tributaria de acceso público del Registro Único de Contribuyentes (RUC) administrado por el SRI y proveedores oficiales del Servicio Nacional de Contratación Pública (SERCOP).
                  </p>
                </div>

                <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800">
                  <h4 className="text-sm font-bold text-white flex items-center gap-2 mb-1.5">
                    <span>🌎 Estándares Internacionales B2B & CAN-SPAM</span>
                  </h4>
                  <p className="text-xs text-slate-300 leading-relaxed m-0">
                    Las cadencias de contacto sugeridas por Michito cumplen con los principios de pertinencia profesional B2B, identificación clara del remitente, asunto transparente relacionado con la actividad comercial y mecanismo visible de cancelación de suscripción (opt-out).
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Section 4: ARCO & Opt-Out */}
          <section className="legal-card" id="arco">
            <div className="legal-card-header">
              <div className="legal-card-icon" style={{ background: "rgba(168, 85, 247, 0.1)", border: "1px solid rgba(168, 85, 247, 0.3)", color: "#c084fc" }}>
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h2 className="legal-card-title">
                4. Canales de Exclusión Voluntaria (Opt-Out) & Derechos ARCO
              </h2>
            </div>
            <div className="legal-card-body">
              <p>
                Cualquier persona jurídica, directivo o representante estatutario puede ejercer en cualquier momento sus derechos de Acceso, Rectificación, Cancelación u Oposición (ARCO), así como solicitar la exclusión voluntaria de su correo corporativo para que no sea incluido en futuros lotes comerciales generados por el motor.
              </p>
              <p>
                Para solicitar la exclusión inmediata, remita un correo a <strong>habeasdata@chiketto.com</strong> indicando el dominio o correo corporativo a excluir. El motor registrará la exclusión en el ledger global permanente en un plazo máximo de 24 horas hábiles.
              </p>
            </div>
          </section>
        </div>

        {/* Bottom Back Action */}
        <div style={{ marginTop: "48px", textAlign: "center" }}>
          <button
            type="button"
            onClick={onBack}
            className="hero-primary-btn"
            style={{ margin: "0 auto", padding: "14px 28px" }}
          >
            <span>Volver a la plataforma principal</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default TermsPage;

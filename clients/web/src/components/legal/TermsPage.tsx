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
            Última actualización: Noviembre 2026 • Cobertura Comercial: Colombia y República Dominicana
          </p>
        </div>

        <div className="legal-sections">
          {/* Section 1: Scope */}
          <section className="legal-card">
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
          <section className="legal-card">
            <div className="legal-card-header">
              <div className="legal-card-icon" style={{ background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", color: "var(--accent-emerald)" }}>
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h2 className="legal-card-title">
                2. Garantía Técnica de Reemplazo
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
                Para activar la garantía técnica de reemplazo, el cliente únicamente debe remitir el log técnico o cabecera de rebote (SMTP bounce notification) a nuestro canal de soporte dentro del periodo de 7 días naturales posteriores a la entrega del archivo.
              </p>
            </div>
          </section>

          {/* Section 3: Habeas Data & Compliance */}
          <section className="legal-card">
            <div className="legal-card-header">
              <div className="legal-card-icon" style={{ background: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.3)", color: "var(--accent-amber)" }}>
                <Scale className="w-5 h-5" />
              </div>
              <h2 className="legal-card-title">
                3. Cumplimiento Normativo & Habeas Data Comercial
              </h2>
            </div>
            <div className="legal-card-body">
              <p>
                <strong>Fuentes Institucionales Públicas:</strong> Michito recopila y procesa exclusivamente datos de naturaleza pública, institucional y comercial provenientes de registros mercantiles oficiales, portales de contratación pública y sitios web de empresas activas.
              </p>
              <p>
                <strong>Cumplimiento Legal:</strong> Todo tratamiento de información comercial se realiza en estricto apego a la <strong>Ley 1581 de 2012</strong> y Decreto 1377 de 2013 de la República de Colombia, y a la <strong>Ley 172-13</strong> sobre Protección de Datos de Carácter Personal de la República Dominicana.
              </p>
              <p>
                <strong>Garantía de Cobro Justo:</strong> El sistema factura exclusivamente por las cuentas corporativas que superan con éxito todos los filtros técnicos de calificación en vivo. Si una cuenta no pasa los filtros, no se debita de la orden del cliente.
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

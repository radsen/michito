import React, { useEffect } from "react";
import { useSelector } from "react-redux";
import { RootState } from "../../store";
import { ShieldCheck, Scale, FileText, ArrowLeft, CheckCircle2, UserCheck } from "lucide-react";

interface TermsPageProps {
  onBack: () => void;
}

export const TermsPage: React.FC<TermsPageProps> = ({ onBack }) => {
  const { dict } = useSelector((state: RootState) => state.language);
  const l = (dict as any).legal || {};

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  return (
    <div className="legal-page-container">
      <div className="legal-page-content">
        {/* Back Link */}
        <div style={{ marginBottom: "28px" }}>
          <button
            type="button"
            onClick={onBack}
            className="legal-back-btn"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>{l.backButton || "Volver a la plataforma principal"}</span>
          </button>
        </div>

        {/* Section Header matching site design system */}
        <div className="section-header text-center" style={{ marginBottom: "48px" }}>
          <span className="section-kicker">{l.kicker || "Marco Jurídico & Operativo"}</span>
          <h1 className="section-title" style={{ fontSize: "2.35rem", lineHeight: 1.25 }}>
            {l.title || "Términos del Servicio, Garantía & Habeas Data"}
          </h1>
          <p className="section-subtitle" style={{ fontSize: "0.95rem", maxWidth: "720px", margin: "10px auto 0" }}>
            {l.subtitle || "Última actualización: Noviembre 2026 • Cobertura Comercial: Colombia 🇨🇴, República Dominicana 🇩🇴, Ecuador 🇪🇨 y Mercados B2B 🌎"}
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
                {l.sec1Title || "1. Delimitación de Alcance Comercial"}
              </h2>
            </div>
            <div className="legal-card-body">
              <p>{l.sec1P1}</p>
              <p>{l.sec1P2}</p>
            </div>
          </section>

          {/* Section 2: Technical Replacement Guarantee */}
          <section className="legal-card" id="garantia">
            <div className="legal-card-header">
              <div className="legal-card-icon" style={{ background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", color: "var(--accent-emerald)" }}>
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h2 className="legal-card-title">
                {l.sec2Title || "2. Garantía Técnica de Reemplazo 2 por 1"}
              </h2>
            </div>
            <div className="legal-card-body">
              <div className="legal-guarantee-box">
                <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" />
                <span>{l.sec2Badge}</span>
              </div>
              <p>{l.sec2P1}</p>
              <p>
                <strong>{l.sec2P2 ? l.sec2P2.split(":")[0] + ":" : "Garantía de Cobro Justo:"}</strong>{" "}
                {l.sec2P2 ? l.sec2P2.split(":").slice(1).join(":") : ""}
              </p>
            </div>
          </section>

          {/* Section 3: Habeas Data & Multi-Country Compliance */}
          <section className="legal-card" id="habeas-data">
            <div className="legal-card-header">
              <div className="legal-card-icon" style={{ background: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.3)", color: "var(--accent-amber)" }}>
                <Scale className="w-5 h-5" />
              </div>
              <h2 className="legal-card-title">
                {l.sec3Title || "3. Marco Jurídico por Territorio & Habeas Data Comercial"}
              </h2>
            </div>
            <div className="legal-card-body">
              <p>{l.sec3P1}</p>

              <div className="legal-country-grid">
                {/* Colombia */}
                <div className="legal-country-card">
                  <div className="legal-country-title">
                    <span>{l.coTitle || "🇨🇴 Colombia — Ley 1581 de 2012 y Decreto 1377 de 2013"}</span>
                  </div>
                  <p className="legal-country-desc">{l.coDesc}</p>
                </div>

                {/* Dominican Republic */}
                <div className="legal-country-card">
                  <div className="legal-country-title">
                    <span>{l.doTitle || "🇩🇴 República Dominicana — Ley 172-13"}</span>
                  </div>
                  <p className="legal-country-desc">{l.doDesc}</p>
                </div>

                {/* Ecuador */}
                <div className="legal-country-card">
                  <div className="legal-country-title">
                    <span>{l.ecTitle || "🇪🇨 Ecuador — Ley Orgánica de Protección de Datos Personales (LOPDP)"}</span>
                  </div>
                  <p className="legal-country-desc">{l.ecDesc}</p>
                </div>

                {/* International Standards */}
                <div className="legal-country-card">
                  <div className="legal-country-title">
                    <span>{l.intlTitle || "🌎 Estándares Internacionales B2B & CAN-SPAM"}</span>
                  </div>
                  <p className="legal-country-desc">{l.intlDesc}</p>
                </div>
              </div>
            </div>
          </section>

          {/* Section 4: ARCO & Opt-Out */}
          <section className="legal-card" id="arco">
            <div className="legal-card-header">
              <div className="legal-card-icon" style={{ background: "rgba(168, 85, 247, 0.1)", border: "1px solid rgba(168, 85, 247, 0.3)", color: "#c084fc" }}>
                <UserCheck className="w-5 h-5" />
              </div>
              <h2 className="legal-card-title">
                {l.sec4Title || "4. Canales de Exclusión Voluntaria (Opt-Out) & Derechos ARCO"}
              </h2>
            </div>
            <div className="legal-card-body">
              <p>{l.sec4P1}</p>
              <p>
                {l.sec4P2 ? (
                  <>
                    {l.sec4P2.split("habeasdata@chiketto.com")[0]}
                    <strong style={{ color: "#38bdf8" }}>habeasdata@chiketto.com</strong>
                    {l.sec4P2.split("habeasdata@chiketto.com")[1]}
                  </>
                ) : (
                  "Para solicitar la exclusión inmediata, remite un correo a habeasdata@chiketto.com."
                )}
              </p>
            </div>
          </section>
        </div>

        {/* Bottom Back Action */}
        <div style={{ marginTop: "56px", textAlign: "center" }}>
          <button
            type="button"
            onClick={onBack}
            className="hero-primary-btn"
            style={{ margin: "0 auto", padding: "14px 32px" }}
          >
            <ArrowLeft className="w-4 h-4 mr-2 inline" />
            <span>{l.backButton || "Volver a la plataforma principal"}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default TermsPage;

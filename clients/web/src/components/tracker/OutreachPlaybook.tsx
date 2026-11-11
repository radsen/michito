import React, { useState } from "react";
import {
  Copy,
  Check,
  ExternalLink,
  MessageSquare,
  Mail,
  Phone,
  Building2,
  UserCheck,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Send,
  Linkedin,
} from "lucide-react";

export interface PlaybookCompany {
  index: number;
  company_name: string;
  clean_name?: string;
  tax_id?: string;
  tax_id_type?: string;
  country?: string;
  city?: string;
  website?: string;
  decision_maker_name?: string;
  decision_maker_title?: string;
  email?: string;
  phone?: string;
  recommended_angle?: string;
  touches?: {
    touch1_linkedin?: string;
    touch2_email?: {
      subject: string;
      body: string;
    };
    touch3_followup?: {
      subject: string;
      body: string;
    };
    touch4_social_proof?: {
      subject: string;
      body: string;
    };
    touch5_breakup?: {
      subject: string;
      body: string;
    };
  };
  triggers?: {
    contracts_won?: string;
    entity?: string;
    intent?: string;
    expansion?: string;
  };
}

interface OutreachPlaybookProps {
  companies: PlaybookCompany[];
}

export const OutreachPlaybook: React.FC<OutreachPlaybookProps> = ({ companies }) => {
  const [expandedIndex, setExpandedIndex] = useState<number>(0);
  const [activeTab, setActiveTab] = useState<{ [key: number]: number }>({});
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  if (!companies || companies.length === 0) {
    return (
      <div className="p-8 text-center text-slate-400 bg-slate-900/50 rounded-xl border border-slate-800">
        <Sparkles className="w-8 h-8 text-sky-400 mx-auto mb-2 opacity-70" />
        <p className="font-medium text-slate-300">Playbook en Generación</p>
        <p className="text-xs text-slate-500 mt-1">
          Los guiones multicanal y ángulos comerciales de prospección se activan al completar el lote.
        </p>
      </div>
    );
  }

  const handleCopy = (text: string, key: string) => {
    if (navigator?.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    }
  };

  const getCleanPhoneDigits = (rawPhone?: string): string => {
    if (!rawPhone) return "";
    return rawPhone.replace(/\D/g, "");
  };

  const openWhatsApp = (phone?: string, text?: string) => {
    const digits = getCleanPhoneDigits(phone);
    if (!digits) return;
    const url = `https://wa.me/${digits}?text=${encodeURIComponent(text || "")}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const getCountryFlag = (country?: string) => {
    const c = (country || "CO").toUpperCase();
    if (c === "EC") return "🇪🇨";
    if (c === "DO") return "🇩🇴";
    if (c === "MULTI") return "🌎";
    return "🇨🇴";
  };

  return (
    <div className="space-y-4" data-testid="outreach-playbook">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-slate-900/90 rounded-xl border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">🎯</span>
            <h4 className="text-base font-bold text-white tracking-tight">
              Playbook de Prospección & Guiones 1-Click
            </h4>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Cadencias de 5 toques omnicanal (LinkedIn, Email, WhatsApp, Follow-up). Copia o dispara en 1 clic.
          </p>
        </div>
        <div className="text-xs text-slate-400 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700/60 shrink-0">
          <span className="font-semibold text-sky-400">{companies.length}</span> cuentas con guiones listos
        </div>
      </div>

      <div className="space-y-3">
        {companies.map((comp, idx) => {
          const isExpanded = expandedIndex === idx;
          const currentTouchTab = activeTab[idx] || 1; // 1 to 5
          const flag = getCountryFlag(comp.country);

          const touches = comp.touches || {};
          const t1 = touches.touch1_linkedin || "";
          const t2 = touches.touch2_email || { subject: "", body: "" };
          const t3 = touches.touch3_followup || { subject: "", body: "" };
          const t4 = touches.touch4_social_proof || { subject: "", body: "" };
          const t5 = touches.touch5_breakup || { subject: "", body: "" };

          return (
            <div
              key={idx}
              className={`rounded-xl border transition-all duration-200 overflow-hidden ${
                isExpanded
                  ? "bg-slate-900/95 border-sky-500/50 shadow-lg shadow-sky-950/20"
                  : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
              }`}
            >
              {/* Accordion Header */}
              <button
                type="button"
                onClick={() => setExpandedIndex(isExpanded ? -1 : idx)}
                className="w-full text-left p-4 flex items-center justify-between gap-3 hover:bg-slate-800/30 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-7 h-7 rounded-lg bg-sky-950/80 border border-sky-800/60 flex items-center justify-center text-xs font-bold text-sky-300 shrink-0">
                    {idx + 1}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-base">{flag}</span>
                      <span className="font-semibold text-white truncate text-sm">
                        {comp.company_name}
                      </span>
                      {comp.tax_id && (
                        <span className="text-xs text-slate-400 font-mono">
                          {comp.tax_id_type || "NIT"}: {comp.tax_id}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-400 mt-0.5 flex items-center gap-2">
                      <span>{comp.city}</span>
                      <span>•</span>
                      <span className="text-sky-400 font-medium truncate">
                        {comp.decision_maker_name || "Contacto Registrado"} (
                        {comp.decision_maker_title || "Representante Legal"})
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {comp.triggers?.intent && (
                    <span className="hidden sm:inline-block px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-950/60 text-emerald-300 border border-emerald-800/40">
                      {comp.triggers.intent}
                    </span>
                  )}
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  )}
                </div>
              </button>

              {/* Expanded Card Body */}
              {isExpanded && (
                <div className="p-4 pt-0 border-t border-slate-800/80 space-y-4">
                  {/* Account Intelligence Strip */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-3">
                    <div className="bg-slate-950/70 p-2.5 rounded-lg border border-slate-800/80 text-xs">
                      <div className="text-slate-500 font-medium flex items-center gap-1.5 mb-1">
                        <Mail className="w-3.5 h-3.5 text-sky-400" />
                        <span>Correo Verificado</span>
                      </div>
                      <div className="font-mono text-slate-200 select-all truncate">
                        {comp.email || "No registrado"}
                      </div>
                    </div>

                    <div className="bg-slate-950/70 p-2.5 rounded-lg border border-slate-800/80 text-xs">
                      <div className="text-slate-500 font-medium flex items-center gap-1.5 mb-1">
                        <Phone className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Celular Directo / WhatsApp</span>
                      </div>
                      <div className="font-mono text-slate-200 select-all truncate flex items-center justify-between">
                        <span>{comp.phone || "No registrado"}</span>
                        {comp.phone && (
                          <button
                            type="button"
                            onClick={() =>
                              openWhatsApp(
                                comp.phone,
                                `Hola ${comp.decision_maker_name || ""}, te contacto de parte de nuestro equipo comercial.`
                              )
                            }
                            className="text-emerald-400 hover:text-emerald-300 text-[11px] font-semibold"
                            title="Abrir WhatsApp"
                          >
                            WhatsApp
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="bg-slate-950/70 p-2.5 rounded-lg border border-slate-800/80 text-xs">
                      <div className="text-slate-500 font-medium flex items-center gap-1.5 mb-1">
                        <Building2 className="w-3.5 h-3.5 text-purple-400" />
                        <span>Sitio Web Corporativo</span>
                      </div>
                      <div className="truncate">
                        {comp.website && comp.website.startsWith("http") ? (
                          <a
                            href={comp.website}
                            target="_blank"
                            rel="noreferrer"
                            className="text-sky-400 hover:underline flex items-center gap-1"
                          >
                            <span className="truncate">{comp.website}</span>
                            <ExternalLink className="w-3 h-3 shrink-0" />
                          </a>
                        ) : (
                          <span className="text-slate-400">{comp.website || "No disponible"}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Trigger Angle Alert */}
                  {comp.recommended_angle && (
                    <div className="p-3 bg-sky-950/30 border border-sky-800/40 rounded-lg text-xs flex items-start gap-2.5 text-sky-200">
                      <Sparkles className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold text-sky-300">Ángulo de Entrada Recomendado: </span>
                        <span>{comp.recommended_angle}</span>
                        {comp.triggers?.contracts_won && (
                          <span className="block text-slate-400 mt-0.5">
                            Contratos ganados: {comp.triggers.contracts_won} • {comp.triggers.entity}
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Touch Navigation Tabs */}
                  <div className="border-b border-slate-800 flex items-center gap-1 overflow-x-auto pb-1 text-xs">
                    {[
                      { num: 1, label: "Touch 1 (LinkedIn)" },
                      { num: 2, label: "Touch 2 (Cold Email)" },
                      { num: 3, label: "Touch 3 (Follow-up)" },
                      { num: 4, label: "Touch 4 (Social Proof)" },
                      { num: 5, label: "Touch 5 (Breakup)" },
                    ].map((tab) => (
                      <button
                        key={tab.num}
                        type="button"
                        onClick={() =>
                          setActiveTab((prev) => ({ ...prev, [idx]: tab.num }))
                        }
                        className={`px-3 py-1.5 rounded-t-lg font-medium transition-colors shrink-0 ${
                          currentTouchTab === tab.num
                            ? "bg-slate-800 text-sky-400 border-b-2 border-sky-400"
                            : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                        }`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>

                  {/* Touch Content Panel */}
                  <div className="bg-slate-950/80 p-3.5 rounded-lg border border-slate-800 space-y-3">
                    {/* Touch 1: LinkedIn */}
                    {currentTouchTab === 1 && (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-xs text-slate-400">
                          <span className="font-semibold text-slate-300">
                            Nota de Conexión LinkedIn (&lt;300 caracteres)
                          </span>
                          <button
                            type="button"
                            onClick={() => handleCopy(t1, `t1_${idx}`)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 bg-sky-900/60 hover:bg-sky-800 text-sky-200 rounded text-xs font-medium transition-colors"
                          >
                            {copiedKey === `t1_${idx}` ? (
                              <>
                                <Check className="w-3.5 h-3.5 text-emerald-400" />
                                <span>¡Copiado!</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3.5 h-3.5" />
                                <span>Copiar Nota</span>
                              </>
                            )}
                          </button>
                        </div>
                        <div className="p-3 bg-slate-900 rounded border border-slate-800 text-xs text-slate-200 leading-relaxed font-sans select-all">
                          {t1 || "Nota de conexión no provista para esta cuenta."}
                        </div>
                      </div>
                    )}

                    {/* Touch 2: Cold Email */}
                    {currentTouchTab === 2 && (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between text-xs">
                          <div className="text-slate-400">
                            <span className="font-semibold text-slate-300">Asunto: </span>
                            <span className="text-sky-300 font-medium">{t2.subject}</span>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleCopy(t2.subject, `t2_sub_${idx}`)}
                            className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[11px] transition-colors"
                          >
                            {copiedKey === `t2_sub_${idx}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                            <span>Copiar Asunto</span>
                          </button>
                        </div>

                        <div className="p-3 bg-slate-900 rounded border border-slate-800 text-xs text-slate-200 leading-relaxed whitespace-pre-wrap font-sans select-all">
                          {t2.body || "Cuerpo no disponible"}
                        </div>

                        <div className="flex items-center gap-2 pt-1">
                          <button
                            type="button"
                            onClick={() => handleCopy(`Asunto: ${t2.subject}\n\n${t2.body}`, `t2_all_${idx}`)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold transition-colors"
                          >
                            {copiedKey === `t2_all_${idx}` ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                            <span>Copiar Correo Completo</span>
                          </button>

                          {comp.phone && (
                            <button
                              type="button"
                              onClick={() => openWhatsApp(comp.phone, t2.body)}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition-colors"
                            >
                              <MessageSquare className="w-3.5 h-3.5" />
                              <span>Enviar por WhatsApp</span>
                            </button>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Touch 3: Follow-up */}
                    {currentTouchTab === 3 && (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between text-xs">
                          <div className="text-slate-400">
                            <span className="font-semibold text-slate-300">Asunto (Re:): </span>
                            <span className="text-sky-300 font-medium">{t3.subject}</span>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleCopy(t3.subject, `t3_sub_${idx}`)}
                            className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[11px] transition-colors"
                          >
                            {copiedKey === `t3_sub_${idx}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                            <span>Copiar Asunto</span>
                          </button>
                        </div>

                        <div className="p-3 bg-slate-900 rounded border border-slate-800 text-xs text-slate-200 leading-relaxed whitespace-pre-wrap font-sans select-all">
                          {t3.body || "Cuerpo no disponible"}
                        </div>

                        <div className="flex items-center gap-2 pt-1">
                          <button
                            type="button"
                            onClick={() => handleCopy(`Asunto: ${t3.subject}\n\n${t3.body}`, `t3_all_${idx}`)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold transition-colors"
                          >
                            {copiedKey === `t3_all_${idx}` ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                            <span>Copiar Follow-up</span>
                          </button>

                          {comp.phone && (
                            <button
                              type="button"
                              onClick={() => openWhatsApp(comp.phone, t3.body)}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition-colors"
                            >
                              <MessageSquare className="w-3.5 h-3.5" />
                              <span>Enviar por WhatsApp</span>
                            </button>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Touch 4: Social Proof */}
                    {currentTouchTab === 4 && (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between text-xs">
                          <div className="text-slate-400">
                            <span className="font-semibold text-slate-300">Asunto: </span>
                            <span className="text-sky-300 font-medium">{t4.subject}</span>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleCopy(t4.subject, `t4_sub_${idx}`)}
                            className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[11px] transition-colors"
                          >
                            {copiedKey === `t4_sub_${idx}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                            <span>Copiar Asunto</span>
                          </button>
                        </div>

                        <div className="p-3 bg-slate-900 rounded border border-slate-800 text-xs text-slate-200 leading-relaxed whitespace-pre-wrap font-sans select-all">
                          {t4.body || "Cuerpo no disponible"}
                        </div>

                        <div className="flex items-center gap-2 pt-1">
                          <button
                            type="button"
                            onClick={() => handleCopy(`Asunto: ${t4.subject}\n\n${t4.body}`, `t4_all_${idx}`)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold transition-colors"
                          >
                            {copiedKey === `t4_all_${idx}` ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                            <span>Copiar Prueba Social</span>
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Touch 5: Breakup */}
                    {currentTouchTab === 5 && (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between text-xs">
                          <div className="text-slate-400">
                            <span className="font-semibold text-slate-300">Asunto: </span>
                            <span className="text-sky-300 font-medium">{t5.subject}</span>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleCopy(t5.subject, `t5_sub_${idx}`)}
                            className="inline-flex items-center gap-1 px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[11px] transition-colors"
                          >
                            {copiedKey === `t5_sub_${idx}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                            <span>Copiar Asunto</span>
                          </button>
                        </div>

                        <div className="p-3 bg-slate-900 rounded border border-slate-800 text-xs text-slate-200 leading-relaxed whitespace-pre-wrap font-sans select-all">
                          {t5.body || "Cuerpo no disponible"}
                        </div>

                        <div className="flex items-center gap-2 pt-1">
                          <button
                            type="button"
                            onClick={() => handleCopy(`Asunto: ${t5.subject}\n\n${t5.body}`, `t5_all_${idx}`)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold transition-colors"
                          >
                            {copiedKey === `t5_all_${idx}` ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                            <span>Copiar Despedida / Catálogo</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};


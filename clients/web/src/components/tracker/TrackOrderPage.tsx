import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "../../store";
import { restoreOrder, resetOrder } from "../../store/slices/orderSlice";
import { LiveStatusTracker } from "./LiveStatusTracker";
import { Search, ArrowLeft, PackageCheck, Mail, MessageSquare, AlertCircle } from "lucide-react";

interface TrackOrderPageProps {
  onBack: () => void;
  initialOrderId?: string;
}

export const TrackOrderPage: React.FC<TrackOrderPageProps> = ({ onBack, initialOrderId }) => {
  const dispatch = useDispatch();
  const { activeOrderId } = useSelector((state: RootState) => state.order);
  const [searchInput, setSearchInput] = useState(initialOrderId || "");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
    if (initialOrderId && !activeOrderId) {
      dispatch(restoreOrder(initialOrderId));
    }
  }, [initialOrderId, activeOrderId, dispatch]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanId = searchInput.trim();
    if (!cleanId) {
      setErrorMsg("Ingresa un número de orden válido (ej: ord_20261109_4c2836).");
      return;
    }
    setErrorMsg(null);
    dispatch(restoreOrder(cleanId));
  };

  const handleReset = () => {
    dispatch(resetOrder());
    setSearchInput("");
    setErrorMsg(null);
  };

  return (
    <div className="track-page-container min-h-screen py-12 px-6">
      <div className="section-container max-w-4xl mx-auto">
        {/* Back Link */}
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 text-sm text-sky-400 hover:text-sky-300 font-semibold mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Volver a la plataforma principal</span>
        </button>

        {/* Page Header */}
        <div className="text-center max-w-2xl mx-auto mb-10">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-sky-500/10 border border-sky-500/30 text-sky-400 mb-4">
            <PackageCheck className="w-6 h-6" />
          </div>
          <h1 className="text-3xl font-extrabold text-white">
            Rastreo de Lotes B2B
          </h1>
          <p className="text-slate-400 text-sm mt-2">
            Ingresa el identificador de tu orden para consultar el avance del pipeline asíncrono, revisar la muestra calificada o descargar tus archivos.
          </p>
        </div>

        {/* Tracking Search Card */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 sm:p-8 max-w-2xl mx-auto mb-10 shadow-xl">
          <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <input
                id="track-order-page-input"
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Ej: ord_20261109_4c2836"
                className="w-full h-12 px-4 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 font-mono text-sm focus:outline-none focus:border-sky-500 transition-colors"
              />
            </div>
            <button
              type="submit"
              className="h-12 px-6 rounded-xl bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-sm flex items-center justify-center gap-2 transition-all shrink-0 shadow-lg shadow-sky-500/20"
            >
              <Search className="w-4 h-4" />
              <span>Consultar Estado</span>
            </button>
          </form>

          {errorMsg && (
            <div className="mt-3 text-xs text-rose-400 flex items-center gap-1.5">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {activeOrderId && (
            <div className="mt-4 pt-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
              <span>
                Orden activa: <strong className="text-sky-400 font-mono">{activeOrderId}</strong>
              </span>
              <button
                type="button"
                onClick={handleReset}
                className="text-slate-400 hover:text-white underline"
              >
                Buscar otra orden
              </button>
            </div>
          )}
        </div>

        {/* Order Display Area */}
        {activeOrderId ? (
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 sm:p-8">
            <LiveStatusTracker />
          </div>
        ) : (
          /* Helper Tips Card when no order is loaded */
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-6 max-w-2xl mx-auto">
            <h3 className="text-sm font-bold text-white mb-3">
              ¿Dónde encuentro mi ID de orden?
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs text-slate-400">
              <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <Mail className="w-5 h-5 text-sky-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-slate-200 block mb-0.5">Correo Corporativo</strong>
                  Te enviamos la confirmación con el código de seguimiento al email que indicaste al solicitar el lote.
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                <MessageSquare className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-slate-200 block mb-0.5">Mensaje WhatsApp</strong>
                  Si registraste tu celular, recibiste un mensaje con el enlace directo para consultar tu orden.
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TrackOrderPage;

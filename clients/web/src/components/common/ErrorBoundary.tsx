import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("[ErrorBoundary] Uncaught component error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            padding: "24px",
            margin: "24px auto",
            maxWidth: "600px",
            background: "rgba(15, 23, 42, 0.8)",
            border: "1px solid rgba(244, 63, 94, 0.3)",
            borderRadius: "12px",
            textAlign: "center",
            color: "#fff",
          }}
        >
          <div style={{ display: "inline-flex", padding: "10px", borderRadius: "50%", background: "rgba(244, 63, 94, 0.15)", marginBottom: "12px" }}>
            <AlertCircle style={{ width: 28, height: 28, color: "#f43f5e" }} />
          </div>
          <h3 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "8px" }}>
            {this.props.fallbackTitle || "Ocurrió un error inesperado en este componente"}
          </h3>
          <p style={{ fontSize: "0.85rem", color: "#94a3b8", marginBottom: "16px" }}>
            {this.state.error?.message || "Error al renderizar los datos."}
          </p>
          <button
            type="button"
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 16px",
              background: "#38bdf8",
              color: "#0f172a",
              border: "none",
              borderRadius: "8px",
              fontWeight: 600,
              fontSize: "0.85rem",
              cursor: "pointer",
            }}
          >
            <RefreshCw style={{ width: 14, height: 14 }} />
            <span>Recargar Página</span>
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}


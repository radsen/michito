import React, { useState } from "react";
import { Building2, Check, ChevronDown, Sparkles } from "lucide-react";
import { useSearchSectorsQuery } from "../../store/api/michitoApi";

export interface SectorSelectorProps {
  selectedSectors: string[];
  onChange: (sectors: string[]) => void;
  onKeywordsSuggested?: (keywords: string[]) => void;
}

export const SectorSelector: React.FC<SectorSelectorProps> = ({
  selectedSectors,
  onChange,
  onKeywordsSuggested,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  const { data: sectorsData } = useSearchSectorsQuery({
    q: searchTerm,
    limit: 25,
  });

  const sectors = sectorsData?.sectors || [];

  const toggleSector = (sectorId: string, sectorKeywords: string[] = []) => {
    if (selectedSectors.includes(sectorId)) {
      onChange(selectedSectors.filter((id) => id !== sectorId));
    } else {
      onChange([...selectedSectors, sectorId]);
      if (onKeywordsSuggested && sectorKeywords.length > 0) {
        onKeywordsSuggested(sectorKeywords.slice(0, 5));
      }
    }
  };

  const getSectorDisplayName = (id: string) => {
    const s = sectors.find((sec: any) => sec.sector_id === id);
    return s ? s.sector_name : id.replace(/_/g, " ");
  };

  return (
    <div className="sector-select-box">
      <label className="tag-pill-label">
        Sector Económico & Clasificación CIIU
      </label>

      {/* Selected Sectors Display / Dropdown Trigger */}
      <div style={{ position: "relative", width: "100%" }}>
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="sector-trigger-btn"
        >
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "6px" }}>
            <Building2 style={{ width: 15, height: 15, color: "#818cf8" }} />
            {selectedSectors.length > 0 ? (
              selectedSectors.map((secId) => (
                <span key={secId} className="sector-chip">
                  <span>{getSectorDisplayName(secId)}</span>
                </span>
              ))
            ) : (
              <span style={{ color: "var(--text-dim)", fontSize: "0.85rem" }}>
                Seleccionar sectores económicos (CIIU)...
              </span>
            )}
          </div>
          <ChevronDown
            style={{
              width: 16,
              height: 16,
              color: "var(--text-muted)",
              transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
              transition: "transform 0.2s ease",
            }}
          />
        </button>

        {/* Dropdown Menu */}
        {isOpen && (
          <div className="sector-dropdown-panel">
            {/* Search filter inside dropdown */}
            <div style={{ padding: "4px 4px 8px 4px" }}>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Filtrar por sector o código CIIU..."
                className="geo-search-input"
                style={{ padding: "6px 10px", fontSize: "0.8rem" }}
              />
            </div>

            {sectors.map((sec: any) => {
              const isSelected = selectedSectors.includes(sec.sector_id);
              return (
                <button
                  key={sec.sector_id}
                  type="button"
                  onClick={() => toggleSector(sec.sector_id, sec.default_keywords || [])}
                  className={`sector-item-row ${isSelected ? "selected" : ""}`}
                >
                  <div style={{ display: "flex", flexDirection: "column" }}>
                    <span style={{ fontWeight: 600 }}>{sec.sector_name}</span>
                    <span style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                      CIIU: {sec.ciiu_codes?.join(", ")}
                    </span>
                  </div>
                  {isSelected && (
                    <Check style={{ width: 14, height: 14, color: "#38bdf8" }} />
                  )}
                </button>
              );
            })}

            {sectors.length === 0 && (
              <div style={{ padding: "12px", textAlign: "center", fontSize: "0.78rem", color: "var(--text-dim)" }}>
                No se encontraron sectores que coincidan con la búsqueda.
              </div>
            )}
          </div>
        )}
      </div>

      <span style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
        Al seleccionar un sector, el motor consulta automáticamente los códigos CIIU correspondientes en registros oficiales.
      </span>
    </div>
  );
};

import React, { useState } from "react";
import { useSelector } from "react-redux";
import { RootState } from "../../store";
import { Building2, Check, ChevronDown, Plus, Loader2 } from "lucide-react";
import { useSearchSectorsQuery, useCreateCustomTaxonomyMutation } from "../../store/api/michitoApi";

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
  const { dict } = useSelector((state: RootState) => state.language);
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  const { data: sectorsData } = useSearchSectorsQuery({
    q: searchTerm,
    limit: 25,
  });

  const [createCustomTaxonomy, { isLoading: isCreating }] = useCreateCustomTaxonomyMutation();

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

  const hasExactMatch = sectors.some(
    (sec: any) => sec.sector_name.toLowerCase().trim() === searchTerm.toLowerCase().trim()
  );

  const handleCreateCustomSector = async () => {
    const clean = searchTerm.trim();
    if (!clean) return;
    try {
      const res = await createCustomTaxonomy({ type: "sector", name: clean }).unwrap();
      if (res?.item?.sector_id) {
        if (!selectedSectors.includes(res.item.sector_id)) {
          onChange([...selectedSectors, res.item.sector_id]);
        }
        setSearchTerm("");
      }
    } catch (err) {
      console.error("Failed to create custom sector:", err);
    }
  };

  return (
    <div className="sector-select-box">
      <label className="tag-pill-label">
        {dict.sector.label}
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
                {dict.sector.placeholder}
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
                onKeyDown={(e) => {
                  if (e.key === "Enter" && searchTerm.trim().length >= 3 && !hasExactMatch) {
                    e.preventDefault();
                    handleCreateCustomSector();
                  }
                }}
                placeholder={dict.sector.searchPlaceholder}
                className="geo-search-input"
                style={{ padding: "6px 10px", fontSize: "0.8rem" }}
              />
            </div>

            {/* Custom On-The-Fly Sector Creation Pill */}
            {searchTerm.trim().length >= 3 && !hasExactMatch && (
              <button
                type="button"
                onClick={handleCreateCustomSector}
                disabled={isCreating}
                className="sector-item-row"
                style={{
                  background: "rgba(99, 102, 241, 0.12)",
                  borderBottom: "1px dashed rgba(99, 102, 241, 0.3)",
                  color: "#a5b4fc",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  {isCreating ? (
                    <Loader2 className="spinner" style={{ width: 14, height: 14 }} />
                  ) : (
                    <Plus style={{ width: 14, height: 14 }} />
                  )}
                  <div style={{ display: "flex", flexDirection: "column", textAlign: "left" }}>
                    <span style={{ fontWeight: 600 }}>
                      {dict.sector.addCustomPrefix} "{searchTerm.trim()}"
                    </span>
                    <span style={{ fontSize: "0.70rem", color: "#818cf8" }}>
                      {dict.sector.addCustomHint}
                    </span>
                  </div>
                </div>
              </button>
            )}

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

            {sectors.length === 0 && !searchTerm.trim() && (
              <div style={{ padding: "12px", textAlign: "center", fontSize: "0.78rem", color: "var(--text-dim)" }}>
                {dict.sector.emptySearch}
              </div>
            )}
          </div>
        )}
      </div>

      <span style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
        {dict.sector.footerHint}
      </span>
    </div>
  );
};

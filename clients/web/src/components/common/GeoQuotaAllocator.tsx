import React, { useState } from "react";
import { useSelector } from "react-redux";
import { RootState } from "../../store";
import { MapPin, Plus, Trash2, AlertCircle, CheckCircle2 } from "lucide-react";
import { LocationAllocationPayload, useLazyValidateLocationQuery, useSearchLocationsQuery } from "../../store/api/michitoApi";

export interface GeoQuotaAllocatorProps {
  allocations: LocationAllocationPayload[];
  onChange: (allocations: LocationAllocationPayload[]) => void;
  totalVolume: number;
  onTotalVolumeChange?: (newTotal: number) => void;
}

export const GeoQuotaAllocator: React.FC<GeoQuotaAllocatorProps> = ({
  allocations,
  onChange,
  totalVolume,
  onTotalVolumeChange,
}) => {
  const { dict } = useSelector((state: RootState) => state.language);
  const [searchInput, setSearchInput] = useState("");
  const [selectedCountry, setSelectedCountry] = useState<string>("ALL");
  const [coverageNotice, setCoverageNotice] = useState<{ isSupported: boolean; message: string } | null>(null);

  const { data: locationData } = useSearchLocationsQuery({
    q: searchInput,
    country: selectedCountry === "ALL" ? undefined : selectedCountry,
    limit: 8,
  });

  const [triggerValidation] = useLazyValidateLocationQuery();

  const countryFlags: Record<string, string> = {
    CO: "🇨🇴",
    DO: "🇩🇴",
    EC: "🇪🇨",
  };

  const handleAddLocation = async (loc: any) => {
    // Check if already added
    if (allocations.some((a) => a.city.toLowerCase() === loc.city_name.toLowerCase())) {
      setCoverageNotice({
        isSupported: true,
        message: `${loc.city_name} ya está en la lista de asignación.`,
      });
      return;
    }

    const defaultQuota = Math.max(5, Math.round(totalVolume / (allocations.length + 1)));
    const newAlloc: LocationAllocationPayload = {
      country: loc.country_code,
      region: loc.region_name,
      city: loc.city_name,
      allocated_leads: defaultQuota,
    };

    const updated = [...allocations, newAlloc];
    onChange(updated);
    setSearchInput("");
    setCoverageNotice({
      isSupported: true,
      message: `Territorio ${loc.city_name} (${loc.country_name}) añadido exitosamente.`,
    });

    // Recalculate total if handler provided
    const newSum = updated.reduce((acc, curr) => acc + curr.allocated_leads, 0);
    if (onTotalVolumeChange && newSum !== totalVolume) {
      onTotalVolumeChange(newSum);
    }
  };

  const handleCustomValidation = async () => {
    if (!searchInput.trim()) return;
    try {
      const res = await triggerValidation(searchInput.trim()).unwrap();
      if (res.is_supported && res.location) {
        handleAddLocation(res.location);
      } else {
        setCoverageNotice({
          isSupported: false,
          message: res.message || `El territorio "${searchInput}" no cuenta con cobertura activa en registros mercantiles de 🇨🇴, 🇩🇴 o 🇪🇨.`,
        });
      }
    } catch {
      setCoverageNotice({
        isSupported: false,
        message: `No se pudo validar la cobertura de "${searchInput}".`,
      });
    }
  };

  const handleUpdateQuota = (city: string, quota: number) => {
    const updated = allocations.map((a) =>
      a.city === city ? { ...a, allocated_leads: Math.max(1, quota) } : a
    );
    onChange(updated);
    const newSum = updated.reduce((acc, curr) => acc + curr.allocated_leads, 0);
    if (onTotalVolumeChange) {
      onTotalVolumeChange(newSum);
    }
  };

  const handleRemoveAllocation = (city: string) => {
    const updated = allocations.filter((a) => a.city !== city);
    onChange(updated);
    const newSum = updated.reduce((acc, curr) => acc + curr.allocated_leads, 0);
    if (onTotalVolumeChange && updated.length > 0) {
      onTotalVolumeChange(newSum);
    }
  };

  const currentAllocatedSum = allocations.reduce((acc, curr) => acc + curr.allocated_leads, 0);

  return (
    <div className="geo-quota-box">
      {/* Header with Title and Current Quota Status */}
      <div className="geo-quota-header">
        <div className="geo-quota-title-wrap">
          <MapPin style={{ width: 18, height: 18, color: "#34d399" }} />
          <span className="geo-quota-title">{dict.geo.title}</span>
        </div>
        <span className="geo-quota-total-badge">
          {dict.geo.allocatedBadge.replace("{count}", String(currentAllocatedSum))}
        </span>
      </div>

      <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: 0 }}>
        {dict.geo.subtitle}
      </p>

      {/* Country Filter Tabs */}
      <div className="geo-filter-tabs">
        {[
          { code: "ALL", label: dict.geo.tabAll },
          { code: "CO", label: dict.geo.tabCo },
          { code: "DO", label: dict.geo.tabDo },
          { code: "EC", label: dict.geo.tabEc },
        ].map((c) => (
          <button
            key={c.code}
            type="button"
            onClick={() => setSelectedCountry(c.code)}
            className={`geo-filter-tab ${selectedCountry === c.code ? "active" : ""}`}
          >
            {c.label}
          </button>
        ))}
      </div>

      {/* Territory Search Box */}
      <div className="geo-search-wrapper">
        <div style={{ display: "flex", gap: "8px" }}>
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleCustomValidation();
              }
            }}
            placeholder={dict.geo.searchPlaceholder}
            className="geo-search-input"
          />
          <button
            type="button"
            onClick={handleCustomValidation}
            disabled={!searchInput.trim()}
            className="tag-pill-add-action-btn"
            style={{ padding: "0 14px", height: "auto" }}
          >
            <Plus style={{ width: 14, height: 14 }} />
            <span>{dict.geo.addBtn}</span>
          </button>
        </div>

        {/* Live Search Autocomplete Dropdown */}
        {searchInput.trim().length >= 2 && locationData?.locations && locationData.locations.length > 0 && (
          <div className="geo-search-dropdown">
            {locationData.locations.map((loc) => {
              const isAdded = allocations.some((a) => a.city.toLowerCase() === loc.city_name.toLowerCase());
              return (
                <button
                  key={loc.location_id}
                  type="button"
                  onClick={() => handleAddLocation(loc)}
                  disabled={isAdded}
                  className="geo-search-result-btn"
                  style={{ opacity: isAdded ? 0.5 : 1 }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span>{countryFlags[loc.country_code] || "🌎"}</span>
                    <div>
                      <strong style={{ color: "#fff", display: "block" }}>{loc.city_name}</strong>
                      <span style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                        {loc.region_name} • {loc.country_name}
                      </span>
                    </div>
                  </div>
                  <span style={{ fontSize: "0.72rem", color: isAdded ? "var(--text-dim)" : "#34d399" }}>
                    {isAdded ? dict.geo.alreadyAllocated : dict.geo.assign}
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Coverage Feedback Notice */}
      {coverageNotice && (
        <div className={`geo-coverage-notice ${coverageNotice.isSupported ? "valid" : "warning"}`}>
          {coverageNotice.isSupported ? (
            <CheckCircle2 style={{ width: 16, height: 16, flexShrink: 0 }} />
          ) : (
            <AlertCircle style={{ width: 16, height: 16, flexShrink: 0 }} />
          )}
          <span>{coverageNotice.message}</span>
        </div>
      )}

      {/* Active Territory Allocations List */}
      {allocations.length > 0 ? (
        <div className="geo-allocations-table">
          {allocations.map((alloc) => (
            <div key={alloc.city} className="geo-alloc-row">
              <div className="geo-alloc-city-info">
                <span>{countryFlags[alloc.country] || "🌎"}</span>
                <div>
                  <span style={{ fontWeight: 600, color: "#fff", fontSize: "0.85rem", display: "block" }}>
                    {alloc.city}
                  </span>
                  <span style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                    {alloc.region} ({alloc.country})
                  </span>
                </div>
              </div>

              <div className="geo-alloc-controls">
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{dict.geo.quotaLabel}</span>
                <input
                  type="number"
                  min="1"
                  max="1000"
                  value={alloc.allocated_leads}
                  onChange={(e) => handleUpdateQuota(alloc.city, parseInt(e.target.value, 10) || 1)}
                  className="geo-alloc-num-input"
                />
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{dict.geo.leadsUnit}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveAllocation(alloc.city)}
                  className="geo-alloc-delete-btn"
                  title={dict.geo.deleteTooltip}
                >
                  <Trash2 style={{ width: 14, height: 14 }} />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ textAlign: "center", padding: "16px", border: "1px dashed var(--border-color)", borderRadius: "8px" }}>
          <p style={{ fontSize: "0.8rem", color: "var(--text-dim)", margin: 0 }}>
            {dict.geo.emptyNotice}
          </p>
        </div>
      )}
    </div>
  );
};

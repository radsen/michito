import React, { useState, KeyboardEvent } from "react";
import { X, Plus } from "lucide-react";

export interface TagPillInputProps {
  tags?: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  suggestions?: string[];
  color?: "indigo" | "rose" | "emerald" | "amber";
  label?: string;
  helperText?: string;
}

export const TagPillInput: React.FC<TagPillInputProps> = ({
  tags = [],
  onChange,
  placeholder = "Escribe y presiona Enter...",
  suggestions = [],
  color = "indigo",
  label,
  helperText,
}) => {
  const [inputValue, setInputValue] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);

  // Defensively ensure tags is an array of non-empty strings
  const safeTags = (Array.isArray(tags) ? tags : []).filter(
    (t): t is string => typeof t === "string" && Boolean(t.trim())
  );

  // Defensively ensure suggestions is an array of non-empty strings
  const safeSuggestions = (Array.isArray(suggestions) ? suggestions : []).filter(
    (s): s is string => typeof s === "string" && Boolean(s.trim())
  );

  const addTag = (text: string) => {
    if (!text || typeof text !== "string") return;
    const trimmed = text.trim();
    if (!trimmed) return;
    if (!safeTags.some((t) => t.toLowerCase() === trimmed.toLowerCase())) {
      onChange([...safeTags, trimmed]);
    }
    setInputValue("");
    setShowDropdown(false);
  };

  const removeTag = (indexToRemove: number) => {
    onChange(safeTags.filter((_, idx) => idx !== indexToRemove));
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag(inputValue);
    } else if (e.key === "Backspace" && !inputValue && safeTags.length > 0) {
      removeTag(safeTags.length - 1);
    }
  };

  const search = (inputValue || "").trim().toLowerCase();

  const filteredSuggestions = safeSuggestions.filter(
    (s) =>
      s.toLowerCase().includes(search) &&
      !safeTags.some((t) => t.toLowerCase() === s.toLowerCase())
  );

  return (
    <div className="tag-pill-container">
      {label && <label className="tag-pill-label">{label}</label>}

      <div className="tag-pill-wrapper">
        <div className="tag-pill-box">
          {safeTags.map((tag, idx) => (
            <span key={`${tag}-${idx}`} className={`tag-pill-chip ${color}`}>
              <span>{tag}</span>
              <button
                type="button"
                onClick={() => removeTag(idx)}
                className="tag-pill-remove-btn"
                aria-label={`Eliminar ${tag}`}
              >
                <X style={{ width: 12, height: 12 }} />
              </button>
            </span>
          ))}

          <input
            type="text"
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value);
              setShowDropdown(true);
            }}
            onFocus={() => setShowDropdown(true)}
            onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
            onKeyDown={handleKeyDown}
            placeholder={safeTags.length === 0 ? placeholder : "Agregar otro..."}
            className="tag-pill-input-field"
          />

          {inputValue.trim() && (
            <button
              type="button"
              onClick={() => addTag(inputValue)}
              className="tag-pill-add-action-btn"
            >
              <Plus style={{ width: 12, height: 12 }} />
              <span>Añadir</span>
            </button>
          )}
        </div>

        {/* Autocomplete Dropdown */}
        {showDropdown && filteredSuggestions.length > 0 && (
          <div className="tag-pill-dropdown-menu">
            {filteredSuggestions.slice(0, 8).map((suggestion, idx) => (
              <button
                key={`${suggestion}-${idx}`}
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault();
                  addTag(suggestion);
                }}
                className="tag-pill-dropdown-item"
              >
                <span>{suggestion}</span>
                <Plus style={{ width: 12, height: 12, opacity: 0.6 }} />
              </button>
            ))}
          </div>
        )}
      </div>

      {helperText && <p className="tag-pill-helper">{helperText}</p>}
    </div>
  );
};

import React, { useState, useEffect } from "react";
import { useSelector } from "react-redux";
import { RootState } from "../../store";
import { Zap } from "lucide-react";

export const MobileStickyCta: React.FC = () => {
  const [visible, setVisible] = useState(false);
  const { dict } = useSelector((state: RootState) => state.language);
  const { activeOrderId } = useSelector((state: RootState) => state.order);

  useEffect(() => {
    const handleScroll = () => {
      // Show when scrolled past 300px
      if (window.scrollY > 300) {
        setVisible(true);
      } else {
        setVisible(false);
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  if (!visible || activeOrderId) return null;

  const scrollToGenerator = () => {
    const el = document.getElementById("generador");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div className="mobile-sticky-cta-bar">
      <button onClick={scrollToGenerator} className="mobile-sticky-btn">
        <Zap className="w-4 h-4 fill-current text-sky-400" />
        <span>Pedir Lote de Leads</span>
      </button>
    </div>
  );
};


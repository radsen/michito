import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "../../store";
import { selectCampaign } from "../../store/slices/campaignSlice";
import { Building2, ShieldCheck, FileSpreadsheet, Warehouse, Fuel, Sparkles, Check, ArrowRight } from "lucide-react";

export const VerticalProfiles: React.FC = () => {
  const dispatch = useDispatch();
  const { dict } = useSelector((state: RootState) => state.language);
  const { selectedCampaignId } = useSelector((state: RootState) => state.campaign);
  const v = dict.verticals;

  const verticalList = [
    {
      id: "tinkko_enterprise_offices",
      icon: Building2,
      country: v.card1Country,
      title: v.card1Title,
      desc: v.card1Desc,
      meta: v.card1Meta,
    },
    {
      id: "hebi",
      icon: ShieldCheck,
      country: v.card2Country,
      title: v.card2Title,
      desc: v.card2Desc,
      meta: v.card2Meta,
    },
    {
      id: "chiketto",
      icon: FileSpreadsheet,
      country: v.card3Country,
      title: v.card3Title,
      desc: v.card3Desc,
      meta: v.card3Meta,
    },
    {
      id: "warehouse_aburra_norte",
      icon: Warehouse,
      country: v.card4Country,
      title: v.card4Title,
      desc: v.card4Desc,
      meta: v.card4Meta,
    },
    {
      id: "blueoil",
      icon: Fuel,
      country: v.card5Country,
      title: v.card5Title,
      desc: v.card5Desc,
      meta: v.card5Meta,
    },
    {
      id: "facility_services_b2b",
      icon: Sparkles,
      country: v.card6Country,
      title: v.card6Title,
      desc: v.card6Desc,
      meta: v.card6Meta,
    },
  ];

  const handleSelect = (id: string) => {
    dispatch(selectCampaign(id));
    const el = document.getElementById("generador");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <section id="verticales" className="verticals-section">
      <div className="section-container">
        <div className="section-header">
          <span className="section-kicker">{v.kicker}</span>
          <h2 className="section-title">{v.title}</h2>
          <p className="section-subtitle">{v.subtitle}</p>
        </div>

        <div className="verticals-grid">
          {verticalList.map((item) => {
            const Icon = item.icon;
            const isSelected = item.id === selectedCampaignId;
            return (
              <div
                key={item.id}
                className={`vertical-card ${isSelected ? "selected-card" : ""}`}
              >
                <div className="vertical-header">
                  <div className="vertical-icon-box">
                    <Icon className="w-6 h-6 text-sky-400" />
                  </div>
                  <span className="vertical-country-tag">{item.country}</span>
                </div>

                <h3 className="vertical-name">{item.title}</h3>
                <p className="vertical-desc">{item.desc}</p>

                <div className="vertical-meta-bar">
                  <span>{item.meta}</span>
                </div>

                <button
                  onClick={() => handleSelect(item.id)}
                  className={`vertical-select-btn ${isSelected ? "selected-btn" : ""}`}
                >
                  {isSelected ? (
                    <>
                      <Check className="w-4 h-4" /> Perfil Seleccionado
                    </>
                  ) : (
                    <>
                      <span>Elegir Vertical</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

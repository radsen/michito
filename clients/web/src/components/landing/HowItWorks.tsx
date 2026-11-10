import React from "react";
import { useSelector } from "react-redux";
import { RootState } from "../../store";
import { Sliders, Database, MailCheck, Download } from "lucide-react";

export const HowItWorks: React.FC = () => {
  const { dict } = useSelector((state: RootState) => state.language);

  const steps = [
    {
      icon: Sliders,
      title: dict.process.step1Title,
      desc: dict.process.step1Desc,
      color: "text-blue-400",
      bg: "bg-blue-500/10",
    },
    {
      icon: Database,
      title: dict.process.step2Title,
      desc: dict.process.step2Desc,
      color: "text-amber-400",
      bg: "bg-amber-500/10",
    },
    {
      icon: MailCheck,
      title: dict.process.step3Title,
      desc: dict.process.step3Desc,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
    },
    {
      icon: Download,
      title: dict.process.step4Title,
      desc: dict.process.step4Desc,
      color: "text-purple-400",
      bg: "bg-purple-500/10",
    },
  ];

  return (
    <section id="como-funciona" className="process-section">
      <div className="section-container">
        <div className="section-header">
          <span className="section-kicker">{dict.process.kicker}</span>
          <h2 className="section-title">{dict.process.title}</h2>
          <p className="section-subtitle">{dict.process.subtitle}</p>
        </div>

        <div className="process-grid">
          {steps.map((step, idx) => {
            const Icon = step.icon;
            return (
              <div key={idx} className="process-step-card">
                <div className={`step-icon-wrapper ${step.color} ${step.bg}`}>
                  <Icon className="w-6 h-6" />
                </div>
                <h3 className="step-title">{step.title}</h3>
                <p className="step-desc">{step.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};


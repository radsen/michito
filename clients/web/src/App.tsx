import React from "react";
import { Navbar } from "./components/layout/Navbar";
import { Hero } from "./components/landing/Hero";
import { ComparisonTable } from "./components/landing/ComparisonTable";
import { IntentTriggers } from "./components/landing/IntentTriggers";
import { HowItWorks } from "./components/landing/HowItWorks";
import { VerticalProfiles } from "./components/landing/VerticalProfiles";
import { DeliverablesStandards } from "./components/landing/DeliverablesStandards";
import { PricingMatrix } from "./components/pricing/PricingMatrix";
import { OrderGenerator } from "./components/order/OrderGenerator";
import { Footer } from "./components/layout/Footer";
import { MobileStickyCta } from "./components/layout/MobileStickyCta";

export const App: React.FC = () => {
  return (
    <div className="app-root">
      <Navbar />
      <main>
        <Hero />
        <ComparisonTable />
        <IntentTriggers />
        <HowItWorks />
        <VerticalProfiles />
        <DeliverablesStandards />
        <PricingMatrix />
        <OrderGenerator />
      </main>
      <Footer />
      <MobileStickyCta />
    </div>
  );
};

export default App;


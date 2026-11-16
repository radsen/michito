"""
Underwrite Lead Use Case (Tier 3 Solvency & Risk Screening Pipeline)
Orchestrates audited EBITDA solvency extraction, litigation screening (Rama Judicial),
and fiscal sanctions checks (Contraloría BDME) to produce an authoritative
Corporate Underwriting Profile.
"""

from dataclasses import dataclass
from decimal import Decimal
import re
from typing import List, Dict, Any, Optional

from src.domain.entities.litigation_record import LitigationRecord
from src.domain.value_objects.ebitda_margin import SolvencyTier, EbitdaMargin
from src.application.ports.financial_statements_port import FinancialStatementsPort
from src.application.ports.litigation_port import LitigationScreeningPort
from src.application.use_cases.calculate_ebitda import CalculateCompanyEbitdaUseCase
from src.application.use_cases.screen_litigation_risk import ScreenLitigationRiskUseCase
from src.adapters.registries.colombia.supersociedades_soda_adapter import SupersociedadesSodaAdapter
from src.adapters.litigation.rama_judicial_adapter import RamaJudicialAdapter
from src.adapters.litigation.contraloria_bdme_adapter import ContraloriaBdmeAdapter


@dataclass
class UnderwritingResult:
    tax_id: str
    company_name: str
    operating_revenue: Decimal
    cost_of_sales: Decimal
    operating_expenses: Decimal
    depreciation: Decimal
    amortization: Decimal
    ebit: Decimal
    ebitda: Decimal
    ebitda_margin: EbitdaMargin
    solvency_tier: SolvencyTier
    solvency_summary: str
    litigation_records: List[LitigationRecord]
    litigation_risk_status: str  # "CLEAN", "WARNING", "CRITICAL"
    litigation_summary: str
    revenue_score: float
    ebitda_score: float
    litigation_score: float
    deliverability_score: float
    composite_score: float
    underwriting_grade: str
    credit_recommendation: str
    has_audited_financials: bool = False
    financial_source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tax_id": self.tax_id,
            "company_name": self.company_name,
            "has_audited_financials": self.has_audited_financials,
            "financial_source": self.financial_source,
            "operating_revenue": float(self.operating_revenue),
            "cost_of_sales": float(self.cost_of_sales),
            "operating_expenses": float(self.operating_expenses),
            "depreciation": float(self.depreciation),
            "amortization": float(self.amortization),
            "ebit": float(self.ebit),
            "ebitda": float(self.ebitda),
            "ebitda_margin_percent": round(float(self.ebitda_margin.value * 100), 2),
            "solvency_tier": self.solvency_tier.value,
            "solvency_summary": self.solvency_summary,
            "litigation_count": len(self.litigation_records),
            "litigation_risk_status": self.litigation_risk_status,
            "litigation_summary": self.litigation_summary,
            "revenue_score": self.revenue_score,
            "ebitda_score": self.ebitda_score,
            "litigation_score": self.litigation_score,
            "deliverability_score": self.deliverability_score,
            "composite_score": self.composite_score,
            "underwriting_grade": self.underwriting_grade,
            "credit_recommendation": self.credit_recommendation,
        }


class UnderwriteLeadUseCase:
    """
    Automated Tier 3 Underwriting Pipeline.
    Evaluates corporate solvency, EBITDA health, court litigations, and fiscal sanctions.
    """

    def __init__(
        self,
        financial_statements_port: Optional[FinancialStatementsPort] = None,
        ebitda_calculator: Optional[CalculateCompanyEbitdaUseCase] = None,
        litigation_adapters: Optional[List[LitigationScreeningPort]] = None,
    ):
        self.financial_statements = financial_statements_port or SupersociedadesSodaAdapter()
        self.ebitda_calculator = ebitda_calculator or CalculateCompanyEbitdaUseCase()
        lit_adapters = litigation_adapters or [RamaJudicialAdapter(), ContraloriaBdmeAdapter()]
        self.litigation_screener = ScreenLitigationRiskUseCase(adapters=lit_adapters)

    def execute(self, lead: Dict[str, Any], email_status: str = "valid") -> UnderwritingResult:
        """
        Executes complete financial solvency and risk underwriting for a lead entity.
        """
        raw_nit = str(lead.get("nit") or lead.get("tax_id") or "000000000")
        clean_nit = raw_nit.replace(".", "").split("-")[0].strip()
        company_name = lead.get("clean_name") or lead.get("company_name") or "Empresa Evaluada"

        # 1. Financial Statements & EBITDA Analysis
        raw_financials = self.financial_statements.fetch_raw_financials(clean_nit)
        has_audited_financials = raw_financials.get("has_audited_financials", False)
        op_rev = raw_financials.get("operating_revenue", 0)
        financial_source = raw_financials.get("financial_source", "")

        contracts = lead.get("contracts_data", {})
        has_contracts = bool(contracts.get("has_contracts", False))
        contracts_won_cop = float(contracts.get("total_value_cop", 0)) if has_contracts else 0.0
        if has_contracts and contracts_won_cop == 0.0:
            disp_digits = re.sub(r"\D", "", str(contracts.get("total_value_display") or ""))
            if disp_digits:
                try:
                    contracts_won_cop = float(disp_digits)
                except ValueError:
                    contracts_won_cop = 0.0
        contracts_display = contracts.get("total_value_display", "$0 COP")

        if has_audited_financials and op_rev > 0:
            ebitda_res = self.ebitda_calculator.execute(raw_financials)
            ebit = Decimal(str(ebitda_res["ebit"]))
            ebitda = Decimal(str(ebitda_res["ebitda"]))
            margin: EbitdaMargin = ebitda_res["ebitda_margin"]
            solvency_tier = margin.tier
            margin_percent = float(margin.value * 100)

            if solvency_tier == SolvencyTier.AAA:
                solvency_summary = f"Rentabilidad sobresaliente auditada (Margen EBITDA {margin_percent:.1f}%). Alta liquidez operativa. Fuente: {financial_source}."
            elif solvency_tier == SolvencyTier.AA:
                solvency_summary = f"Operación saludable y solvente (Margen EBITDA {margin_percent:.1f}%). Fuente: {financial_source}."
            elif solvency_tier == SolvencyTier.A:
                solvency_summary = f"Margen operativo estándar ({margin_percent:.1f}%). Fuente: {financial_source}."
            else:
                solvency_summary = f"Alerta financiera: Margen EBITDA deficitario ({margin_percent:.1f}%). Quema de caja operativa. Fuente: {financial_source}."

            revenue_score = min(max((float(op_rev) / 10_000_000_000.0) * 100.0, 20.0), 100.0)
            if margin_percent > 15.0:
                ebitda_score = 100.0
            elif margin_percent >= 8.0:
                ebitda_score = 80.0
            elif margin_percent >= 1.0:
                ebitda_score = 55.0
            elif margin_percent >= 0.0:
                ebitda_score = 40.0
            else:
                ebitda_score = 10.0
        else:
            # Fact-based solvency without financial hallucinations:
            # Avoids fabricating artificial billions in revenue or synthetic cost ratios.
            ebit = Decimal("0")
            ebitda = Decimal("0")
            margin = EbitdaMargin(Decimal("0.0"))
            margin_percent = 0.0

            if contracts_won_cop > 0:
                solvency_tier = SolvencyTier.AA if contracts_won_cop >= 500_000_000 else SolvencyTier.A
                solvency_summary = (
                    f"Capacidad operativa respaldada en contratación pública ({contracts_display}). "
                    "Empresa comercial activa en Cámara de Comercio sin balance NIIF centralizado en Supersociedades."
                )
                revenue_score = min(max((contracts_won_cop / 1_000_000_000.0) * 100.0, 40.0), 90.0)
                ebitda_score = 75.0
            else:
                solvency_tier = SolvencyTier.A
                solvency_summary = (
                    "Empresa comercial activa en Cámara de Comercio (RUES / SECOP). "
                    "No obligada a reporte público centralizado NIIF ante Supersociedades (PYME no supervisada)."
                )
                revenue_score = 45.0
                ebitda_score = 50.0

        # 2. Legal Litigation & Fiscal Sanction Screening
        litigation_records = self.litigation_screener.execute(clean_nit)

        has_insolvency = any("insolvency" in r.status.lower() or "1116" in r.status.lower() for r in litigation_records)
        has_executory = any("ejecutivo" in r.status.lower() or "cobro" in r.status.lower() for r in litigation_records)
        has_fiscal_debt = any("fiscal" in r.status.lower() or "bdme" in r.status.lower() for r in litigation_records)
        has_labor = any("laboral" in r.status.lower() for r in litigation_records)

        if has_insolvency or has_executory or has_fiscal_debt:
            litigation_risk_status = "CRITICAL"
            reasons = []
            if has_insolvency:
                reasons.append("Proceso de Reorganización / Insolvencia (Ley 1116)")
            if has_executory:
                reasons.append("Proceso Ejecutivo de Cobro de Deuda")
            if has_fiscal_debt:
                reasons.append("Sanción Fiscal en Boletín BDME Contraloría")
            litigation_summary = f"ALERTA CRÍTICA: {', '.join(reasons)}."
            credit_recommendation = "Alto Riesgo de Iliquidez o Insolvencia. No otorgar crédito comercial; ventas estrictamente de contado o anticipo 100%."
            litigation_score = 0.0
        elif has_labor or len(litigation_records) > 0:
            litigation_risk_status = "WARNING"
            litigation_summary = f"Advertencia: {len(litigation_records)} litigio(s) ordinario(s) detectado(s) (ej. Proceso Laboral)."
            credit_recommendation = "Riesgo Moderado. Términos comerciales estándar a 15-30 días bajo monitoreo."
            litigation_score = 65.0
        else:
            litigation_risk_status = "CLEAN"
            litigation_summary = "Paz y salvo en registros mercantiles oficiales. Sin sanciones, multas ni inhabilidades en SECOP II."
            credit_recommendation = "Solvente y con operación comercial activa. Aprobado para términos de crédito estándar a 30-60 días."
            litigation_score = 100.0

        # 3. Composite Scoring Algorithm
        rev_val = float(raw_financials.get("operating_revenue", 0))
        revenue_score = min(max((rev_val / 10_000_000_000.0) * 100.0, 15.0), 100.0)

        if margin_percent > 15.0:
            ebitda_score = 100.0
        elif margin_percent >= 8.0:
            ebitda_score = 80.0
        elif margin_percent >= 1.0:
            ebitda_score = 55.0
        elif margin_percent >= 0.0:
            ebitda_score = 40.0
        else:
            ebitda_score = 10.0

        if email_status.lower() in ("valid", "verified", "active"):
            deliverability_score = 100.0
        elif email_status.lower() == "catch-all":
            deliverability_score = 50.0
        else:
            deliverability_score = 30.0

        composite_score = round(
            (revenue_score * 0.25)
            + (ebitda_score * 0.30)
            + (litigation_score * 0.25)
            + (deliverability_score * 0.20),
            1
        )

        # 4. Underwriting Grade Assignment
        if litigation_risk_status == "CRITICAL" or composite_score < 45.0:
            underwriting_grade = "D - Alerta de Iliquidez / Riesgo Crítico"
        elif composite_score >= 82.0:
            underwriting_grade = "AAA - Solvente y de Máxima Confianza"
        elif composite_score >= 68.0:
            underwriting_grade = "AA - Saludable y Operativo"
        else:
            underwriting_grade = "A - Aprobado con Precaución"

        return UnderwritingResult(
            tax_id=clean_nit,
            company_name=company_name,
            operating_revenue=Decimal(str(raw_financials.get("operating_revenue", 0))),
            cost_of_sales=Decimal(str(raw_financials.get("cost_of_sales", 0))),
            operating_expenses=Decimal(str(raw_financials.get("operating_expenses", 0))),
            depreciation=Decimal(str(raw_financials.get("depreciation", 0))),
            amortization=Decimal(str(raw_financials.get("amortization", 0))),
            ebit=ebit,
            ebitda=ebitda,
            ebitda_margin=margin,
            solvency_tier=solvency_tier,
            solvency_summary=solvency_summary,
            litigation_records=litigation_records,
            litigation_risk_status=litigation_risk_status,
            litigation_summary=litigation_summary,
            revenue_score=round(revenue_score, 1),
            ebitda_score=round(ebitda_score, 1),
            litigation_score=round(litigation_score, 1),
            deliverability_score=round(deliverability_score, 1),
            composite_score=composite_score,
            underwriting_grade=underwriting_grade,
            credit_recommendation=credit_recommendation,
            has_audited_financials=has_audited_financials,
            financial_source=financial_source,
        )


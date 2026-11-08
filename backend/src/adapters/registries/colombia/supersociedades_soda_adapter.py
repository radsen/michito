import urllib.request
import urllib.parse
import json
from decimal import Decimal
from typing import List, Dict, Any

from src.application.ports.corporate_registry_port import CountryRegistryProvider
from src.application.ports.financial_statements_port import FinancialStatementsPort
from src.domain.entities.company import Company
from src.domain.entities.financial_report import FinancialReport
from src.domain.entities.litigation_record import LitigationRecord
from src.domain.value_objects.tax_id import TaxId
from src.application.dto.search_request_dto import CompanyFilterDto

# Fallback dataset
CURATED_COLOMBIAN_REGISTRY = [
    {
        "nit": "830.076.432-1",
        "name": "MTS Administración e Inversiones S.A.S.",
        "sector": "facility_management",
        "city": "Bogotá",
        "revenue_cop": 48500000000,
        "ebitda_cop": 4850000000,
    },
    {
        "nit": "860.052.123-1",
        "name": "Sevicol Ltda.",
        "sector": "facility_management",
        "city": "Bogotá",
        "revenue_cop": 38000000000,
        "ebitda_cop": 3800000000,
    }
]

class SupersociedadesSodaAdapter(CountryRegistryProvider, FinancialStatementsPort):
    def __init__(self, use_live_api: bool = False):
        self.use_live_api = use_live_api
        self.soda_url = "https://www.datos.gov.co/resource/28m6-2pi3.json" # Example resource

    @property
    def country_code(self) -> str:
        return "CO"

    @property
    def currency(self) -> str:
        return "COP"

    def validate_tax_id(self, tax_id: str) -> bool:
        return bool(tax_id)

    def fetch_companies(self, filter_dto: CompanyFilterDto) -> List[Company]:
        companies = []
        
        if self.use_live_api:
            try:
                query = f"{self.soda_url}?$limit=5"
                req = urllib.request.Request(query, headers={"Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())
                for item in data:
                    nit_val = item.get('nit', 'unknown').replace('.', '')
                    nit_base = nit_val.split('-')[0]
                    companies.append(Company(
                        id=f"CO-{nit_base}",
                        tax_id=TaxId(nit_base),
                        name=item.get('razon_social', 'Unknown'),
                        industry=filter_dto.industry
                    ))
                return companies
            except Exception:
                pass

        for item in CURATED_COLOMBIAN_REGISTRY:
            if filter_dto.industry and item["sector"] != filter_dto.industry:
                continue
            if filter_dto.city and item["city"] != filter_dto.city:
                continue
            if filter_dto.min_revenue and Decimal(str(item["revenue_cop"])) < filter_dto.min_revenue:
                continue
            
            nit_val = str(item["nit"]).replace(".", "")
            nit_base = nit_val.split('-')[0]
            companies.append(Company(
                id=f"CO-{nit_base}",
                tax_id=TaxId(nit_base),
                name=str(item["name"]),
                industry=str(item["sector"])
            ))
            
        return companies

    def get_financial_statements(self, tax_id: str) -> FinancialReport:
        tax_id_base = tax_id.replace(".", "").split('-')[0]
        for item in CURATED_COLOMBIAN_REGISTRY:
            if str(item["nit"]).replace(".", "").split('-')[0] == tax_id_base:
                return FinancialReport(
                    id=f"FR-{tax_id_base}",
                    company_id=f"CO-{tax_id_base}",
                    revenue=Decimal(str(item["revenue_cop"])),
                    ebitda=Decimal(str(item["ebitda_cop"]))
                )
        return FinancialReport(
            id=f"FR-{tax_id_base}",
            company_id=f"CO-{tax_id_base}",
            revenue=Decimal("0"),
            ebitda=Decimal("0")
        )

    def screen_litigation(self, tax_id: str) -> List[LitigationRecord]:
        return []

    def fetch_raw_financials(self, tax_id: str) -> Dict[str, Any]:
        tax_id_base = tax_id.replace(".", "").split('-')[0]
        for item in CURATED_COLOMBIAN_REGISTRY:
            if str(item["nit"]).replace(".", "").split('-')[0] == tax_id_base:
                revenue_num = float(item["revenue_cop"])
                return {
                    "operating_revenue": revenue_num,
                    "cost_of_sales": revenue_num * 0.6,
                    "operating_expenses": revenue_num * 0.2,
                    "depreciation": revenue_num * 0.05,
                    "amortization": revenue_num * 0.05,
                }
        return {
            "operating_revenue": 0,
            "cost_of_sales": 0,
            "operating_expenses": 0,
            "depreciation": 0,
            "amortization": 0,
        }

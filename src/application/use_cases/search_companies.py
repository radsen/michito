from typing import List
from src.application.ports.corporate_registry_port import CorporateRegistryPort
from src.application.ports.financial_statements_port import FinancialStatementsPort
from src.application.ports.litigation_port import LitigationScreeningPort
from src.application.ports.mailbox_verifier_port import MailboxVerifierPort
from src.application.dto.search_request_dto import CompanyFilterDto
from src.application.dto.lead_dossier_dto import LeadDossierDto
from src.application.use_cases.calculate_ebitda import CalculateCompanyEbitdaUseCase
from decimal import Decimal

class SearchQualifiedCompaniesUseCase:
    def __init__(
        self,
        corporate_registry: CorporateRegistryPort,
        financial_statements: FinancialStatementsPort,
        litigation_screening: LitigationScreeningPort,
        mailbox_verifier: MailboxVerifierPort,
        ebitda_calculator: CalculateCompanyEbitdaUseCase
    ):
        self.corporate_registry = corporate_registry
        self.financial_statements = financial_statements
        self.litigation_screening = litigation_screening
        self.mailbox_verifier = mailbox_verifier
        self.ebitda_calculator = ebitda_calculator

    def execute(self, filter_dto: CompanyFilterDto) -> List[LeadDossierDto]:
        provider = self.corporate_registry.get_provider(filter_dto.country_code)
        companies = provider.fetch_companies(filter_dto)
        
        results = []
        for company in companies:
            tax_id_str = company.tax_id.value
            
            raw_financials = self.financial_statements.fetch_raw_financials(tax_id_str)
            ebitda_res = self.ebitda_calculator.execute(raw_financials)
            
            rev_raw = raw_financials.get('operating_revenue')
            if rev_raw is None:
                rev_raw = 0
            revenue = Decimal(str(rev_raw))
            
            # Litigation screening
            litigation_records = self.litigation_screening.screen_litigation(tax_id_str)
            
            # Mailbox verification - assume a standard email constructed from company id
            email_to_verify = f"contact@{company.id}.com"
            email_status = self.mailbox_verifier.verify_email(email_to_verify)
            
            # Calculate Composite Score
            revenue_score = min(max(float(revenue) / 10_000_000_000.0 * 100, 0), 100)
            
            margin_percent = float(ebitda_res["ebitda_margin"].value * 100)
            if margin_percent > 15:
                ebitda_score = 100
            elif margin_percent >= 0:
                ebitda_score = (margin_percent / 15.0) * 100
            else:
                ebitda_score = 0
                
            has_insolvency = any(r.status.lower() == 'insolvency' for r in litigation_records)
            if has_insolvency or len(litigation_records) > 1:
                litigation_score = 0
            elif len(litigation_records) == 1:
                litigation_score = 70
            else:
                litigation_score = 100
                
            if email_status == 'valid':
                deliverability_score = 100
            elif email_status == 'catch-all':
                deliverability_score = 50
            else:
                deliverability_score = 0
                
            composite_score = (
                (revenue_score * 0.25) +
                (ebitda_score * 0.30) +
                (litigation_score * 0.25) +
                (deliverability_score * 0.20)
            )
            
            dossier = LeadDossierDto(
                company_id=company.id,
                company_name=company.name,
                tax_id=tax_id_str,
                industry=company.industry or "Unknown",
                revenue=revenue,
                ebitda=ebitda_res["ebitda"],
                ebitda_margin=ebitda_res["ebitda_margin"].value,
                litigation_count=len(litigation_records),
                email_deliverability=email_status,
                composite_score=composite_score
            )
            results.append(dossier)
            
        results.sort(key=lambda x: x.composite_score, reverse=True)
        return results

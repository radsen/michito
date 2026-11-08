from google.cloud import firestore
from src.application.ports.lead_order_repository_port import LeadOrderRepositoryPort
from src.domain.entities.lead_order import LeadOrder
from src.domain.entities.company import Company
from src.domain.entities.decision_maker import DecisionMaker
from src.domain.entities.financial_report import FinancialReport
from src.domain.entities.litigation_record import LitigationRecord
from src.domain.value_objects.tax_id import TaxId
from src.domain.value_objects.confidence_score import ConfidenceScore
from decimal import Decimal

class FirestoreRepositoryAdapter(LeadOrderRepositoryPort):
    def __init__(self, project_id: str = "demo-project"):
        self.db = firestore.Client(project=project_id)
        self.collection = self.db.collection("lead_orders")

    def save(self, lead_order: LeadOrder) -> None:
        doc_ref = self.collection.document(lead_order.id)
        
        company_data = {
            "id": lead_order.company.id,
            "tax_id": lead_order.company.tax_id.value,
            "name": lead_order.company.name,
            "industry": lead_order.company.industry
        }
        
        dms_data = [{
            "id": dm.id,
            "name": dm.name,
            "role": dm.role,
            "email": dm.email,
            "linkedin_url": dm.linkedin_url
        } for dm in lead_order.decision_makers]
        
        financials_data = [{
            "id": fr.id,
            "company_id": fr.company_id,
            "revenue": str(fr.revenue),
            "ebitda": str(fr.ebitda)
        } for fr in lead_order.financial_reports]
        
        litigation_data = [{
            "id": lr.id,
            "company_id": lr.company_id,
            "case_number": lr.case_number,
            "status": lr.status,
            "filing_date": lr.filing_date.isoformat() if lr.filing_date else None
        } for lr in lead_order.litigation_records]
        
        data = {
            "id": lead_order.id,
            "company": company_data,
            "decision_makers": dms_data,
            "financial_reports": financials_data,
            "litigation_records": litigation_data,
            "confidence_score": lead_order.confidence_score.value if lead_order.confidence_score else None
        }
        
        doc_ref.set(data)

    def get_by_id(self, order_id: str) -> LeadOrder:
        doc = self.collection.document(order_id).get()
        if not doc.exists:
            raise KeyError(f"LeadOrder {order_id} not found in Firestore")
        
        data = doc.to_dict()
        
        company = Company(
            id=data["company"]["id"],
            tax_id=TaxId(data["company"]["tax_id"]),
            name=data["company"]["name"],
            industry=data["company"].get("industry")
        )
        
        lead_order = LeadOrder(
            id=data["id"],
            company=company
        )
        
        for dm in data.get("decision_makers", []):
            raw_email = dm.get("email")
            email_val = raw_email if isinstance(raw_email, EmailAddress) else EmailAddress(raw_email or "unknown@domain.com")
            lead_order.add_decision_maker(DecisionMaker(
                id=dm["id"],
                name=dm["name"],
                role=dm.get("role"),
                email=email_val,
                linkedin_url=dm.get("linkedin_url")
            ))
            
        for fr in data.get("financial_reports", []):
            lead_order.add_financial_report(FinancialReport(
                id=fr["id"],
                company_id=fr["company_id"],
                revenue=Decimal(fr["revenue"]),
                ebitda=Decimal(fr["ebitda"])
            ))
            
        for lr in data.get("litigation_records", []):
            import datetime
            filing_date = datetime.date.fromisoformat(lr["filing_date"]) if lr.get("filing_date") else None
            lead_order.add_litigation_record(LitigationRecord(
                id=lr["id"],
                company_id=lr["company_id"],
                case_number=lr["case_number"],
                status=lr["status"],
                filing_date=filing_date
            ))
            
        if data.get("confidence_score") is not None:
            lead_order.confidence_score = ConfidenceScore(Decimal(str(data["confidence_score"])))
            
        return lead_order

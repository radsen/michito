from dataclasses import dataclass, field
from typing import List, Optional
from src.domain.entities.company import Company
from src.domain.entities.decision_maker import DecisionMaker
from src.domain.entities.financial_report import FinancialReport
from src.domain.entities.litigation_record import LitigationRecord
from src.domain.value_objects.confidence_score import ConfidenceScore

@dataclass
class LeadOrder:
    id: str
    company: Company
    decision_makers: List[DecisionMaker] = field(default_factory=list)
    financial_reports: List[FinancialReport] = field(default_factory=list)
    litigation_records: List[LitigationRecord] = field(default_factory=list)
    confidence_score: Optional[ConfidenceScore] = None
    
    def __post_init__(self):
        if not self.id:
            raise ValueError("Lead Order must have an ID.")
        if not isinstance(self.company, Company):
            raise ValueError("Lead Order must have a valid company.")
            
    def add_decision_maker(self, dm: DecisionMaker):
        self.decision_makers.append(dm)
        
    def add_financial_report(self, report: FinancialReport):
        if report.company_id != self.company.id:
            raise ValueError("Financial report must belong to the Lead's company.")
        self.financial_reports.append(report)
        
    def add_litigation_record(self, record: LitigationRecord):
        if record.company_id != self.company.id:
            raise ValueError("Litigation record must belong to the Lead's company.")
        self.litigation_records.append(record)

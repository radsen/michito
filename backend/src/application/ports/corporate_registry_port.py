from abc import ABC, abstractmethod
from typing import List
from src.domain.entities.company import Company
from src.domain.entities.financial_report import FinancialReport
from src.domain.entities.litigation_record import LitigationRecord
from src.application.dto.search_request_dto import CompanyFilterDto

class CountryRegistryProvider(ABC):
    @property
    @abstractmethod
    def country_code(self) -> str:
        pass
        
    @property
    @abstractmethod
    def currency(self) -> str:
        pass
        
    @abstractmethod
    def validate_tax_id(self, tax_id: str) -> bool:
        pass
        
    @abstractmethod
    def fetch_companies(self, filter_dto: CompanyFilterDto) -> List[Company]:
        pass
        
    @abstractmethod
    def get_financial_statements(self, tax_id: str) -> FinancialReport:
        pass
        
    @abstractmethod
    def screen_litigation(self, tax_id: str) -> List[LitigationRecord]:
        pass

class CorporateRegistryPort(ABC):
    @abstractmethod
    def get_provider(self, country_code: str) -> CountryRegistryProvider:
        pass

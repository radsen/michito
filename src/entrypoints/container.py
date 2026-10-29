import os
from typing import List, Dict
from src.adapters.registries.colombia.supersociedades_soda_adapter import SupersociedadesSodaAdapter
from src.adapters.payments.wompi_adapter import WompiPaymentGatewayAdapter
from src.adapters.litigation.contraloria_bdme_adapter import ContraloriaBdmeAdapter
from src.adapters.litigation.rama_judicial_adapter import RamaJudicialAdapter
from src.adapters.verifiers.socket_smtp_verifier_adapter import SocketSmtpVerifierAdapter
from src.adapters.repositories.memory_repository_adapter import MemoryRepositoryAdapter

from src.application.ports.litigation_port import LitigationScreeningPort
from src.application.ports.corporate_registry_port import CorporateRegistryPort, CountryRegistryProvider
from src.domain.entities.litigation_record import LitigationRecord

from src.application.use_cases.search_companies import SearchQualifiedCompaniesUseCase
from src.application.use_cases.calculate_ebitda import CalculateCompanyEbitdaUseCase
from src.application.use_cases.verify_mailbox import VerifyContactMailboxUseCase
from src.application.use_cases.create_lead_order import CreateLeadOrderUseCase
from src.application.use_cases.fulfill_wompi_webhook import FulfillPaymentWebhookUseCase
from src.application.use_cases.screen_litigation_risk import ScreenLitigationRiskUseCase

class AggregateLitigationScreeningAdapter(LitigationScreeningPort):
    def __init__(self, adapters: List[LitigationScreeningPort]):
        self.adapters = adapters

    def screen_litigation(self, tax_id: str) -> List[LitigationRecord]:
        aggregated_records = []
        for adapter in self.adapters:
            records = adapter.screen_litigation(tax_id)
            if records:
                aggregated_records.extend(records)
        return aggregated_records

class RegistryDispatcher(CorporateRegistryPort):
    def __init__(self, providers: Dict[str, CountryRegistryProvider]):
        self.providers = providers

    def get_provider(self, country_code: str) -> CountryRegistryProvider:
        if country_code not in self.providers:
            raise ValueError(f"No provider found for country code: {country_code}")
        return self.providers[country_code]


class Container:
    def __init__(self):
        # Adapters
        self.supersociedades = SupersociedadesSodaAdapter(use_live_api=False)
        self.corporate_registry = RegistryDispatcher({"CO": self.supersociedades})
        self.financial_statements = self.supersociedades
        
        self.contraloria_bdme = ContraloriaBdmeAdapter()
        self.rama_judicial = RamaJudicialAdapter()
        self.aggregate_litigation = AggregateLitigationScreeningAdapter([self.contraloria_bdme, self.rama_judicial])
        
        self.mailbox_verifier = SocketSmtpVerifierAdapter()
        
        self.payment_gateway = WompiPaymentGatewayAdapter(
            public_key=os.environ.get("WOMPI_PUBLIC_KEY", "pub_test_123"),
            webhook_secret=os.environ.get("WOMPI_WEBHOOK_SECRET", "secret_123")
        )
        self.repository = MemoryRepositoryAdapter()

        # Use Cases
        self.calculate_ebitda_use_case = CalculateCompanyEbitdaUseCase()
        
        self.search_companies_use_case = SearchQualifiedCompaniesUseCase(
            corporate_registry=self.corporate_registry,
            financial_statements=self.financial_statements,
            litigation_screening=self.aggregate_litigation,
            mailbox_verifier=self.mailbox_verifier,
            ebitda_calculator=self.calculate_ebitda_use_case
        )
        
        self.verify_mailbox_use_case = VerifyContactMailboxUseCase(
            verifier=self.mailbox_verifier
        )
        
        self.create_lead_order_use_case = CreateLeadOrderUseCase(
            payment_gateway=self.payment_gateway,
            repository=self.repository,
            redirect_url=os.environ.get("REDIRECT_URL", "https://example.com/checkout/success")
        )
        
        self.fulfill_webhook_use_case = FulfillPaymentWebhookUseCase(
            payment_gateway=self.payment_gateway,
            repository=self.repository
        )
        
        self.screen_litigation_use_case = ScreenLitigationRiskUseCase(
            adapters=[self.contraloria_bdme, self.rama_judicial]
        )

container = Container()

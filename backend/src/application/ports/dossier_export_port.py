from abc import ABC, abstractmethod
from typing import List
from src.application.dto.lead_dossier_dto import LeadDossierDto

class DossierExportPort(ABC):
    @abstractmethod
    def export(self, dossiers: List[LeadDossierDto], output_path: str) -> str:
        """
        Exports the list of dossiers to a specific format (e.g. CSV, Excel).
        Returns the output path.
        """
        pass

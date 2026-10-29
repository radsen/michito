import pytest
from src.adapters.repositories.memory_repository_adapter import MemoryRepositoryAdapter
from src.adapters.repositories.firestore_repository_adapter import FirestoreRepositoryAdapter
from src.domain.entities.lead_order import LeadOrder
from src.domain.entities.company import Company
from src.domain.value_objects.tax_id import TaxId
import os
from unittest import mock

def test_memory_repository():
    repo = MemoryRepositoryAdapter()
    company = Company(id="C1", tax_id=TaxId("830076432"), name="Test Co", industry="IT")
    lead_order = LeadOrder(id="L1", company=company)
    
    repo.save(lead_order)
    retrieved = repo.get_by_id("L1")
    assert retrieved.id == "L1"
    assert retrieved.company.name == "Test Co"

    with pytest.raises(KeyError):
        repo.get_by_id("L2")

@mock.patch("google.cloud.firestore.Client")
def test_firestore_repository(mock_client):
    mock_db = mock.MagicMock()
    mock_client.return_value = mock_db
    
    mock_collection = mock.MagicMock()
    mock_db.collection.return_value = mock_collection
    
    mock_doc = mock.MagicMock()
    mock_collection.document.return_value = mock_doc
    
    repo = FirestoreRepositoryAdapter()
    
    company = Company(id="C1", tax_id=TaxId("830076432"), name="Test Co", industry="IT")
    lead_order = LeadOrder(id="L1", company=company)
    
    repo.save(lead_order)
    mock_doc.set.assert_called_once()
    
    # Test retrieval
    mock_doc_snapshot = mock.MagicMock()
    mock_doc_snapshot.exists = True
    mock_doc_snapshot.to_dict.return_value = {
        "id": "L1",
        "company": {
            "id": "C1",
            "tax_id": "830076432",
            "name": "Test Co",
            "industry": "IT"
        }
    }
    mock_doc.get.return_value = mock_doc_snapshot
    
    retrieved = repo.get_by_id("L1")
    assert retrieved.id == "L1"
    assert retrieved.company.name == "Test Co"

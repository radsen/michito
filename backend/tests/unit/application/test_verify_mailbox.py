import pytest
from unittest.mock import MagicMock
from src.application.use_cases.verify_mailbox import VerifyContactMailboxUseCase

def test_verify_contact_mailbox_valid():
    mock_verifier = MagicMock()
    mock_verifier.verify_email.return_value = "valid"
    
    use_case = VerifyContactMailboxUseCase(verifier=mock_verifier)
    
    result = use_case.execute("user@example.com")
    assert result == "valid"
    mock_verifier.verify_email.assert_called_once_with("user@example.com")

def test_verify_contact_mailbox_catch_all():
    mock_verifier = MagicMock()
    mock_verifier.verify_email.return_value = "catch-all"
    
    use_case = VerifyContactMailboxUseCase(verifier=mock_verifier)
    
    result = use_case.execute("user@example.com")
    assert result == "catch-all"
    mock_verifier.verify_email.assert_called_once_with("user@example.com")

def test_verify_contact_mailbox_empty():
    mock_verifier = MagicMock()
    use_case = VerifyContactMailboxUseCase(verifier=mock_verifier)
    
    result = use_case.execute("")
    assert result == "invalid"
    mock_verifier.verify_email.assert_not_called()

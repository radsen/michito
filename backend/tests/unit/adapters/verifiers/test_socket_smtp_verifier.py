import pytest
from unittest.mock import patch, MagicMock
import socket

from src.adapters.verifiers.socket_smtp_verifier_adapter import SocketSmtpVerifierAdapter

@pytest.fixture
def adapter():
    return SocketSmtpVerifierAdapter(sender_email="test@example.com")

@patch('src.adapters.verifiers.socket_smtp_verifier_adapter.dns.resolver.resolve')
@patch('src.adapters.verifiers.socket_smtp_verifier_adapter.socket.socket')
def test_verify_email_valid(mock_socket, mock_resolve, adapter):
    # Mock DNS
    mock_mx = MagicMock()
    mock_mx.preference = 10
    mock_mx.exchange.to_text.return_value = "mx.example.com"
    mock_resolve.return_value = [mock_mx]

    # Mock Socket responses
    mock_sock_instance = MagicMock()
    mock_socket.return_value = mock_sock_instance
    
    # We have two checks:
    # 1. Catch-all probe
    # 2. Actual email probe
    # For catch-all probe to fail (return 550), it must send 4 commands (banner, HELO, MAIL FROM, RCPT TO)
    # Then it calls QUIT, which is 5th command.
    # _send_command is called with: "", "HELO test.com", "MAIL FROM:<test@example.com>", "RCPT TO:<uuid@domain>", "QUIT"
    
    responses = [
        # Catch-all check
        b"220 mx.example.com ESMTP\r\n",  # Banner
        b"250 mx.example.com Hello\r\n",  # HELO
        b"250 Sender OK\r\n",             # MAIL FROM
        b"550 User unknown\r\n",          # RCPT TO (catch-all is false)
        b"221 Bye\r\n",                   # QUIT
        
        # Actual email check
        b"220 mx.example.com ESMTP\r\n",  # Banner
        b"250 mx.example.com Hello\r\n",  # HELO
        b"250 Sender OK\r\n",             # MAIL FROM
        b"250 Recipient OK\r\n",          # RCPT TO (valid email)
        b"221 Bye\r\n",                   # QUIT
    ]
    mock_sock_instance.recv.side_effect = responses

    result = adapter.verify_email("user@example.com")
    assert result == "valid"

@patch('src.adapters.verifiers.socket_smtp_verifier_adapter.dns.resolver.resolve')
@patch('src.adapters.verifiers.socket_smtp_verifier_adapter.socket.socket')
def test_verify_email_catch_all(mock_socket, mock_resolve, adapter):
    mock_mx = MagicMock()
    mock_mx.preference = 10
    mock_mx.exchange.to_text.return_value = "mx.example.com"
    mock_resolve.return_value = [mock_mx]

    mock_sock_instance = MagicMock()
    mock_socket.return_value = mock_sock_instance
    
    responses = [
        # Catch-all check
        b"220 mx.example.com ESMTP\r\n",
        b"250 Hello\r\n",
        b"250 Sender OK\r\n",
        b"250 Recipient OK\r\n", # Catch-all accepts random UUID
        b"221 Bye\r\n",
        
        # Actual email check
        b"220 mx.example.com ESMTP\r\n",
        b"250 Hello\r\n",
        b"250 Sender OK\r\n",
        b"250 Recipient OK\r\n", # Actual email also accepted
        b"221 Bye\r\n",
    ]
    mock_sock_instance.recv.side_effect = responses

    result = adapter.verify_email("user@example.com")
    assert result == "catch-all"

@patch('src.adapters.verifiers.socket_smtp_verifier_adapter.dns.resolver.resolve')
@patch('src.adapters.verifiers.socket_smtp_verifier_adapter.socket.socket')
def test_verify_email_invalid(mock_socket, mock_resolve, adapter):
    mock_mx = MagicMock()
    mock_mx.preference = 10
    mock_mx.exchange.to_text.return_value = "mx.example.com"
    mock_resolve.return_value = [mock_mx]

    mock_sock_instance = MagicMock()
    mock_socket.return_value = mock_sock_instance
    
    responses = [
        # Catch-all check
        b"220 mx.example.com ESMTP\r\n",
        b"250 Hello\r\n",
        b"250 Sender OK\r\n",
        b"550 User unknown\r\n", # Catch-all is false
        b"221 Bye\r\n",
        
        # Actual email check
        b"220 mx.example.com ESMTP\r\n",
        b"250 Hello\r\n",
        b"250 Sender OK\r\n",
        b"550 User unknown\r\n", # Actual email is false
        b"221 Bye\r\n",
    ]
    mock_sock_instance.recv.side_effect = responses

    result = adapter.verify_email("invalid_user@example.com")
    assert result == "invalid"

@patch('src.adapters.verifiers.socket_smtp_verifier_adapter.dns.resolver.resolve')
def test_verify_email_no_mx(mock_resolve, adapter):
    mock_resolve.side_effect = Exception("No MX")
    result = adapter.verify_email("user@bad-domain.com")
    assert result == "invalid"

def test_verify_email_malformed(adapter):
    result = adapter.verify_email("not-an-email")
    assert result == "invalid"

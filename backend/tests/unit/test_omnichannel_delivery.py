import pytest
from unittest.mock import MagicMock, patch
from src.adapters.delivery.omnichannel_delivery_adapter import OmnichannelDeliveryAdapter
from src.application.use_cases.deliver_order_use_case import DeliverOrderUseCase

def test_omnichannel_delivery_adapter_extracts_paths(caplog):
    import logging
    caplog.set_level(logging.INFO)
    
    adapter = OmnichannelDeliveryAdapter()
    
    order = {
        "customer_email": "test@example.com",
        "customer_phone": "1234567890",
        "delivery": {
            "csv_download_url": "/downloads/test.csv",
            "dossier_download_url": "/downloads/test.md"
        }
    }
    
    success = adapter.send_delivery(order)
    
    assert success is True
    assert "Sending to 1234567890" in caplog.text
    assert "Sending to test@example.com" in caplog.text
    assert "/downloads/test.csv" in caplog.text
    assert "/downloads/test.md" in caplog.text

def test_deliver_order_use_case_success():
    adapter_mock = MagicMock()
    adapter_mock.send_delivery.return_value = True
    
    repo_mock = MagicMock()
    repo_mock.get_order.return_value = {
        "order_id": "ord_123",
        "status": "paid",
        "delivery": {
            "csv_download_url": "url1",
            "dossier_download_url": "url2"
        }
    }
    
    use_case = DeliverOrderUseCase(adapter_mock, repo_mock)
    
    result = use_case.execute("ord_123")
    
    assert result is True
    repo_mock.get_order.assert_called_once_with("ord_123")
    adapter_mock.send_delivery.assert_called_once()

def test_deliver_order_use_case_unpaid_raises_error():
    adapter_mock = MagicMock()
    
    repo_mock = MagicMock()
    repo_mock.get_order.return_value = {
        "order_id": "ord_123",
        "status": "awaiting_payment",
    }
    
    use_case = DeliverOrderUseCase(adapter_mock, repo_mock)
    
    with pytest.raises(ValueError, match="Order not paid"):
        use_case.execute("ord_123")
        
    adapter_mock.send_delivery.assert_not_called()

def test_deliver_order_use_case_not_found():
    adapter_mock = MagicMock()
    
    repo_mock = MagicMock()
    repo_mock.get_order.return_value = None
    
    use_case = DeliverOrderUseCase(adapter_mock, repo_mock)
    
    with pytest.raises(ValueError, match="Order ord_123 not found"):
        use_case.execute("ord_123")
        
    adapter_mock.send_delivery.assert_not_called()


def test_omnichannel_delivery_archives_artifacts(tmp_path):
    adapter = OmnichannelDeliveryAdapter(outputs_dir=str(tmp_path))
    order = {
        "order_id": "ord_test_archive",
        "client": {
            "name": "Carlos Gomez",
            "email": "carlos@empresa.co",
            "phone": "+573001234567"
        },
        "request": {
            "campaign_id": "tinkko_enterprise_offices",
            "city": "Medellín",
            "tier": 3,
        },
        "delivery": {
            "total_qualified": 25,
            "csv_download_url": "/api/v1/orders/ord_test_archive/download/csv",
            "dossier_download_url": "/api/v1/orders/ord_test_archive/download/md"
        }
    }
    
    success = adapter.send_delivery(order)
    assert success is True
    
    email_html = tmp_path / "dispatched_emails" / "ord_test_archive.html"
    email_json = tmp_path / "dispatched_emails" / "ord_test_archive.json"
    wa_json = tmp_path / "dispatched_whatsapp" / "ord_test_archive.json"
    
    assert email_html.exists()
    assert email_json.exists()
    assert wa_json.exists()
    
    html_text = email_html.read_text(encoding="utf-8")
    assert "ord_test_archive" in html_text
    assert "Carlos Gomez" in html_text
    assert "Medellín" in html_text
    assert "25 empresas" in html_text
    assert "Garantía de Calidad Michito" in html_text


@patch("smtplib.SMTP")
def test_omnichannel_delivery_dispatches_smtp_with_attachment(mock_smtp_cls, tmp_path, monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test-resend.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "resend_api_user")
    monkeypatch.setenv("SMTP_PASSWORD", "secret_pass")
    monkeypatch.setenv("DEV_DELIVERY_EMAIL", "developer@chiketto.com")

    # Create dummy csv deliverable
    dummy_csv = tmp_path / "prospects.csv"
    dummy_csv.write_text("Company,Email,NIT\nEmpresa A,a@a.com,900123\n", encoding="utf-8")

    mock_server = MagicMock()
    mock_smtp_cls.return_value = mock_server

    adapter = OmnichannelDeliveryAdapter(outputs_dir=str(tmp_path))
    order = {
        "order_id": "ord_smtp_123",
        "client": {
            "name": "Elena Soto",
            "email": "elena@empresa.com",
            "phone": "+573105556677"
        },
        "csv_path": str(dummy_csv),
        "delivery": {
            "total_qualified": 10,
            "csv_download_url": "/api/v1/orders/ord_smtp_123/download/csv",
        }
    }

    success = adapter.send_delivery(order)
    assert success is True

    # Assert SMTP methods were called
    mock_smtp_cls.assert_called_once_with("smtp.test-resend.com", 587, timeout=10)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("resend_api_user", "secret_pass")
    mock_server.send_message.assert_called_once()
    mock_server.quit.assert_called_once()

    # Check recipient list passed to send_message
    call_args, call_kwargs = mock_server.send_message.call_args
    assert "elena@empresa.com" in call_kwargs.get("to_addrs", [])
    assert "developer@chiketto.com" in call_kwargs.get("to_addrs", [])


def test_omnichannel_delivery_ready_for_review_archives_artifacts(tmp_path):
    adapter = OmnichannelDeliveryAdapter(outputs_dir=str(tmp_path))
    order = {
        "order_id": "ord_review_test",
        "client": {
            "name": "Mariana Ruiz",
            "email": "mariana@logistica.co",
            "phone": "+573123456789",
        },
        "request": {
            "campaign_id": "logistica_bodegas_bogota",
            "city": "Bogotá",
            "limit": 100,
        },
        "requested_limit": 100,
        "verified_yield": 24,
        "payment": {
            "amount_in_cents": 28800000,
            "currency": "COP",
        },
    }

    success = adapter.send_ready_for_review_notification(order)
    assert success is True

    review_html = tmp_path / "dispatched_emails" / "review_ord_review_test.html"
    review_json = tmp_path / "dispatched_emails" / "review_ord_review_test.json"
    wa_json = tmp_path / "dispatched_whatsapp" / "review_ord_review_test.json"

    assert review_html.exists()
    assert review_json.exists()
    assert wa_json.exists()

    html_content = review_html.read_text(encoding="utf-8")
    assert "Mariana Ruiz" in html_content
    assert "ord_review_test" in html_content
    assert "24 empresas" in html_content
    assert "Garantía de Precio Justo Michito" in html_content
    assert "/rastrear?order_id=ord_review_test" in html_content

    wa_content = wa_json.read_text(encoding="utf-8")
    assert "/rastrear?order_id=ord_review_test" in wa_content
    assert "24 empresas verificadas" in wa_content


@patch("smtplib.SMTP")
def test_omnichannel_delivery_ready_for_review_dispatches_smtp_without_deliverables(mock_smtp_cls, tmp_path, monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test-resend.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "resend_api_user")
    monkeypatch.setenv("SMTP_PASSWORD", "secret_pass")
    monkeypatch.setenv("DEV_DELIVERY_EMAIL", "developer@chiketto.com")

    mock_server = MagicMock()
    mock_smtp_cls.return_value = mock_server

    adapter = OmnichannelDeliveryAdapter(outputs_dir=str(tmp_path))
    order = {
        "order_id": "ord_review_smtp",
        "client": {
            "name": "Santiago Botero",
            "email": "santiago@empresa.com",
            "phone": "+573009876543",
        },
        "requested_limit": 50,
        "verified_yield": 50,
        "payment": {
            "amount_in_cents": 50000000,
            "currency": "COP",
        },
    }

    success = adapter.send_ready_for_review_notification(order)
    assert success is True

    mock_smtp_cls.assert_called_once()
    mock_server.send_message.assert_called_once()
    msg = mock_server.send_message.call_args[0][0]

    # Review emails MUST NOT attach deliverables (.csv/.xlsx/.pdf)
    payloads = msg.get_payload()
    for part in payloads:
        content_disposition = part.get("Content-Disposition") or ""
        assert "attachment" not in content_disposition

@patch("smtplib.SMTP")
def test_omnichannel_delivery_never_attaches_gcs_files_on_unpaid_reviews(mock_smtp_cls, tmp_path, monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test-resend.com")
    monkeypatch.setenv("GCS_BUCKET_NAME", "michito-staging-deliverables")
    monkeypatch.setenv("FRONTEND_URL", "https://michito-web-limgi3puaq-uc.a.run.app")

    mock_server = MagicMock()
    mock_smtp_cls.return_value = mock_server

    adapter = OmnichannelDeliveryAdapter(outputs_dir=str(tmp_path))
    order = {
        "order_id": "ord_review_leak_prevention",
        "client": {
            "name": "Andres Solano",
            "email": "andres@empresa.com",
            "phone": "+573001234567",
        },
        "requested_limit": 1000,
        "verified_yield": 96,
        "payment": {
            "amount_in_cents": 13680000,
            "currency": "COP",
        },
    }

    success = adapter.send_ready_for_review_notification(order)
    assert success is True

    msg = mock_server.send_message.call_args[0][0]
    payloads = msg.get_payload()
    for part in payloads:
        content_disposition = part.get("Content-Disposition") or ""
        assert "attachment" not in content_disposition
        assert "prospectos" not in content_disposition
        assert "dossier" not in content_disposition


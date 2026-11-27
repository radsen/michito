import unittest
from src.adapters.verifiers.website_auditor import WebsiteAuditor

class TestWebsiteAuditor(unittest.TestCase):
    def setUp(self):
        self.auditor = WebsiteAuditor(timeout=3)

    def test_domain_alignment(self):
        # Mismatched domain (e.g. outsourced accountant or web agency)
        self.assertFalse(
            self.auditor.check_domain_alignment("archivosdelestado.com", "Robotic International S.A.S.")
        )
        self.assertFalse(
            self.auditor.check_domain_alignment("gmail.com", "Tech Solutions S.A.S.")
        )

        # Matched domains
        self.assertTrue(
            self.auditor.check_domain_alignment("delgadorocha.com", "Delgado & Rocha Abogados S.A.S.")
        )
        self.assertTrue(
            self.auditor.check_domain_alignment("impactoefectivobtl.com", "Impacto Efectivo BTL-Eventos S.A.S.")
        )
        self.assertTrue(
            self.auditor.check_domain_alignment("sysmedicalgroup.com", "Sysmedical Group S.A.S.")
        )

    def test_audit_empty_or_no_provisto(self):
        ok, display_url, note = self.auditor.audit("", "Empresa Ejemplo S.A.S.")
        self.assertFalse(ok)
        self.assertEqual(display_url, "Presencia en LinkedIn Corporativo")

        ok2, display_url2, note2 = self.auditor.audit("No Provisto", "Empresa Ejemplo S.A.S.")
        self.assertFalse(ok2)
        self.assertEqual(display_url2, "Presencia en LinkedIn Corporativo")

    def test_audit_mismatched_domain(self):
        ok, display_url, note = self.auditor.audit(
            "https://archivosdelestado.com.co", "Robotic International S.A.S."
        )
        self.assertFalse(ok)
        self.assertEqual(display_url, "Presencia en LinkedIn Corporativo")
        self.assertIn("no alineado", note)

    def test_extract_contacts_from_html(self):
        sample_html = """
        <html>
        <head><title>Pinturas y Diseños S.A.S.</title></head>
        <body>
            <header>
                <a href="https://wa.me/573105551234">Escríbenos al WhatsApp</a>
                <a href="mailto:ventas@pinturasydisenos.com">ventas@pinturasydisenos.com</a>
                <img src="/assets/logo.png" alt="logo" />
            </header>
            <footer>
                <p>Teléfono: +57 320 987 6543 | PBX: 601 7654321</p>
                <p>Email soporte: info@pinturasydisenos.com</p>
                <p>Email dummy: test@example.com</p>
            </footer>
        </body>
        </html>
        """
        contacts = WebsiteAuditor.extract_contacts_from_html(sample_html, target_domain="pinturasydisenos.com")
        self.assertEqual(contacts["whatsapp"], "+573105551234")
        self.assertIn("ventas@pinturasydisenos.com", contacts["emails"])
        self.assertIn("info@pinturasydisenos.com", contacts["emails"])
        self.assertNotIn("test@example.com", contacts["emails"])
        self.assertEqual(contacts["primary_email"], "ventas@pinturasydisenos.com")
        self.assertTrue(any("320" in p or "310" in p for p in contacts["phones"]))

if __name__ == "__main__":
    unittest.main()


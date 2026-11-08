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

if __name__ == "__main__":
    unittest.main()


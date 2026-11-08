import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import unittest
from unittest.mock import patch, MagicMock
from generate_prospects import run_prospecting_job, run_prospector
from src.domain.value_objects.ciiu_code import CiiuCode

class TestProspectingJobWorker(unittest.TestCase):
    def test_worker_aliases(self):
        """Verify run_prospecting_job is an exact alias of run_prospector"""
        self.assertIs(run_prospecting_job, run_prospector)

    @patch("generate_prospects.DgcpDrAdapter")
    def test_run_prospecting_job_no_leads(self, mock_adapter_cls):
        """Verify structured response when no leads pass quality gates"""
        mock_instance = MagicMock()
        mock_instance.fetch_candidates.return_value = []
        mock_adapter_cls.return_value = mock_instance

        res = run_prospecting_job(
            campaign="tinkko_dr_offices",
            limit=5,
            dry_run=True,
            output_format="csv"
        )

        self.assertIsInstance(res, dict)
        self.assertEqual(res["status"], "no_leads_found")
        self.assertEqual(res["country"], "DO")
        self.assertEqual(res["currency"], "DOP")
        self.assertEqual(res["total_qualified"], 0)
        self.assertEqual(res["leads"], [])
        self.assertIn("metrics", res)
        self.assertIn("total_elapsed_seconds", res["metrics"])

    @patch("generate_prospects.DgcpDrAdapter")
    @patch("generate_prospects.WebsiteAuditor")
    @patch("generate_prospects.verify_mx")
    def test_run_prospecting_job_success(self, mock_verify_mx, mock_auditor_cls, mock_adapter_cls):
        """Verify structured success response with qualified leads and metrics"""
        mock_verify_mx.return_value = (True, "mail.techdominicana.com")

        mock_auditor = MagicMock()
        mock_auditor.audit.return_value = (True, "https://www.techdominicana.com", "Active Audited Site")
        mock_auditor_cls.return_value = mock_auditor

        mock_adapter = MagicMock()
        mock_adapter.fetch_candidates.return_value = [
            {
                "nit": "131999888",
                "rnc": "131999888",
                "company_name": "Tech Dominicana, SRL",
                "city": "Santo Domingo",
                "address": "Av. Winston Churchill 100",
                "email": "director@techdominicana.com",
                "phone": "+1 (809) 555-1234",
                "decision_maker_name": "Marcos Gomez",
                "decision_maker_title": "Director General",
                "sector": "Desarrollo de software y tecnología",
                "contract_val_dop": 450000.0,
                "contract_val_display": "$450,000 DOP",
                "contract_entity": "Ministerio de Hacienda",
                "contract_object": "Plataforma de software",
                "linkedin_xray_url": "https://google.com/search?q=linkedin",
            }
        ]
        mock_adapter_cls.return_value = mock_adapter

        res = run_prospecting_job(
            campaign="tinkko_dr_offices",
            city="Santo Domingo",
            limit=1,
            dry_run=True,
            output_format="both"
        )

        self.assertIsInstance(res, dict)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["country"], "DO")
        self.assertEqual(res["total_qualified"], 1)
        self.assertEqual(len(res["leads"]), 1)
        self.assertTrue(res["csv_path"].endswith(".csv"))
        self.assertTrue(res["dossier_path"].endswith(".md"))
        self.assertEqual(len(res["sample_teaser"]), 1)
        self.assertEqual(res["sample_teaser"][0]["company_name"], "Tech Dominicana")
        self.assertIn("metrics", res)
        self.assertGreaterEqual(res["metrics"]["candidates_evaluated"], 1)

if __name__ == "__main__":
    unittest.main()


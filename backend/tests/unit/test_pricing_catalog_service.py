import unittest
from src.domain.services.pricing_catalog_service import PricingCatalogService

class TestPricingCatalogService(unittest.TestCase):
    def setUp(self):
        self.service = PricingCatalogService.get_instance()

    def test_get_active_catalog_cop(self):
        catalog = self.service.get_active_catalog("COP")
        self.assertEqual(catalog["status"], "success")
        self.assertEqual(catalog["currency"], "COP")
        self.assertEqual(catalog["min_order_leads"], 25)
        self.assertEqual(catalog["tier_prices"][1], 1500.0)
        self.assertEqual(catalog["tier_prices"][2], 6200.0)
        self.assertEqual(catalog["tier_prices"][3], 15000.0)
        self.assertGreaterEqual(len(catalog["products"]), 3)

    def test_get_active_catalog_usd(self):
        catalog = self.service.get_active_catalog("USD")
        self.assertEqual(catalog["currency"], "USD")
        self.assertEqual(catalog["tier_prices"][1], 0.38)
        self.assertEqual(catalog["tier_prices"][2], 1.55)
        self.assertEqual(catalog["tier_prices"][3], 3.75)

    def test_calculate_quote_courtesy_micro_batch(self):
        # < 5 leads returns 0 cents (courtesy sample policy)
        quote = self.service.calculate_quote(total_qualified=3, tier=2, currency="COP")
        self.assertEqual(quote["total_cents"], 0)
        self.assertTrue(quote["is_courtesy_sample"])
        self.assertEqual(quote["discount_percentage"], 100.0)

    def test_calculate_quote_min_batch_25_cop(self):
        # 25 leads, Tier 2 COP: 25 * 620.000 = 15.500.000 cents ($155.000 COP) with 0% volume discount
        quote = self.service.calculate_quote(total_qualified=25, tier=2, currency="COP")
        self.assertEqual(quote["total_cents"], 15500000)
        self.assertEqual(quote["volume_discount_percentage"], 0.0)
        self.assertFalse(quote["is_courtesy_sample"])

    def test_calculate_quote_100_leads_volume_discount(self):
        # 100 leads gets 10% volume discount: unit = 620.000 * 0.90 = 558.000 cents -> 100 * 558.000 = 55.800.000 cents ($558.000 COP)
        quote = self.service.calculate_quote(total_qualified=100, tier=2, currency="COP")
        self.assertEqual(quote["volume_discount_percentage"], 10.0)
        self.assertEqual(quote["discounted_unit_cents"], 558000)
        self.assertEqual(quote["total_cents"], 55800000)

    def test_calculate_quote_partner_discount_tinkko(self):
        # 100 leads Tier 2 with Tinkko: 10% volume + 10% partner = 20% discount
        # unit = 620.000 * 0.80 = 496.000 cents -> 100 * 496.000 = 49.600.000 cents ($496.000 COP)
        # partner commission = 25%
        quote = self.service.calculate_quote(total_qualified=100, tier=2, currency="COP", partner_id="tinkko")
        self.assertEqual(quote["discount_percentage"], 20.0)
        self.assertEqual(quote["partner_discount_percentage"], 10.0)
        self.assertEqual(quote["partner_commission_percentage"], 25.0)
        self.assertEqual(quote["total_cents"], 49600000)
        self.assertEqual(quote["partner_commission_cents"], int(49600000 * 0.25))

    def test_calculate_quote_min_floor_enforcement(self):
        # 10 leads Tier 1 COP: 10 * 150.000 = 1.500.000 cents -> below floor 2.500.000 cents -> enforced floor
        quote = self.service.calculate_quote(total_qualified=10, tier=1, currency="COP")
        self.assertEqual(quote["total_cents"], 2500000)
        self.assertTrue(quote["min_floor_applied"])

if __name__ == "__main__":
    unittest.main()

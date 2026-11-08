import unittest
from src.domain.value_objects.ciiu_code import CiiuCode, OFFICIAL_CIIU_CATALOG

class TestCiiuCode(unittest.TestCase):
    def test_known_ciiu_codes(self):
        c_6201 = CiiuCode.from_code("6201")
        self.assertEqual(c_6201.code, "6201")
        self.assertEqual(c_6201.sector_macro, "Tecnología, Software & Analítica")
        self.assertIn("planificación", c_6201.description)

        c_7020 = CiiuCode.from_code("7020")
        self.assertEqual(c_7020.code, "7020")
        self.assertEqual(c_7020.sector_macro, "Consultoría Empresarial & Gestión")

        c_6910 = CiiuCode.from_code("6910")
        self.assertEqual(c_6910.sector_macro, "Servicios Legales & Corporativos")

    def test_display_string(self):
        c = CiiuCode.from_code("6201")
        self.assertEqual(c.to_display_string(), "CIIU 6201: Tecnología, Software & Analítica")

    def test_infer_from_text(self):
        c_tech = CiiuCode.infer_from_text("Global Tech Software Solutions S.A.S.", "admin@globaltech.com")
        self.assertEqual(c_tech.code, "6201")
        self.assertEqual(c_tech.sector_macro, "Tecnología, Software & Analítica")

        c_law = CiiuCode.infer_from_text("Delgado & Rocha Abogados Asociados S.A.S.")
        self.assertEqual(c_law.code, "6910")
        self.assertEqual(c_law.sector_macro, "Servicios Legales & Corporativos")

        c_consult = CiiuCode.infer_from_text("Estrategia y Consultores de Gestión S.A.S.")
        self.assertEqual(c_consult.code, "7020")
        self.assertEqual(c_consult.sector_macro, "Consultoría Empresarial & Gestión")

    def test_unknown_code_fallback(self):
        c = CiiuCode.from_code("9999")
        self.assertEqual(c.code, "9999")
        self.assertEqual(c.sector_macro, "Servicios Empresariales & Comerciales")

if __name__ == "__main__":
    unittest.main()

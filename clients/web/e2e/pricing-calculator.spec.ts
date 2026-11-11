import { test, expect } from "@playwright/test";

test.describe("Pricing Matrix & Volume Discount Curves", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/#precios");
  });

  test("should display the 3 intelligence tiers with correct base prices", async ({ page }) => {
    const pricingSection = page.locator("#precios");
    await expect(pricingSection).toBeVisible();

    // Verify Tier 1
    await expect(page.locator(".tier-name", { hasText: "DIRECTORIO BASE" })).toBeVisible();
    await expect(page.locator(".tier-price", { hasText: "$5.000 COP" })).toBeVisible();

    // Verify Tier 2 (Featured)
    await expect(page.locator(".tier-name", { hasText: "CONTACTOS DIRECTOS" })).toBeVisible();
    await expect(page.locator(".tier-price", { hasText: "$30.000 COP" })).toBeVisible();

    // Verify Tier 3
    await expect(page.locator(".tier-name", { hasText: "AUDITORÍA COMPLETA" })).toBeVisible();
    await expect(page.locator(".tier-price", { hasText: "$65.000 COP" })).toBeVisible();
  });

  test("should update generator calculation when switching tiers in pricing matrix", async ({ page }) => {
    // Choose Tier 1 in pricing matrix
    const chooseTier1Btn = page.locator("button:has-text('Elegir Directorio')");
    await chooseTier1Btn.click();

    // Verify that the generator updates to Tier 1 pricing
    const calcBox = page.locator(".calc-summary-box");
    await expect(calcBox).toContainText("Directorio Base");
    await expect(calcBox).toContainText("5.000 COP");

    // Choose Tier 3 in generator pills
    const tier3Pill = page.locator("button:has-text('Auditoría Completa')");
    await tier3Pill.click();
    await expect(calcBox).toContainText("Auditoría Completa");
    await expect(calcBox).toContainText("65.000 COP");
  });

  test("should apply volume discounts correctly (50 leads = 12%, 100 leads = 20%, 1000 leads = 42%)", async ({ page }) => {
    await page.goto("/#generador");

    // Default is Tier 2 ($30.000 COP)
    // Select 10 leads (0% discount)
    const preset10 = page.locator(".preset-btn", { hasText: "10" }).first();
    await preset10.click();

    const calcBox = page.locator(".calc-summary-box");
    await expect(calcBox).toContainText("Subtotal (10 cuentas):");
    await expect(calcBox).toContainText("300.000 COP");
    await expect(calcBox).toContainText("300.000 COP"); // Total

    // Select 50 leads (12% discount)
    const preset50 = page.locator(".preset-btn", { hasText: "50" });
    await preset50.click();
    await expect(calcBox).toContainText("Subtotal (50 cuentas):");
    await expect(calcBox).toContainText("1.500.000 COP");
    await expect(calcBox).toContainText("Descuento por volumen (-12%):");
    // 1.500.000 * 0.88 = 1.320.000
    await expect(calcBox).toContainText("1.320.000 COP");

    // Select 100 leads (20% discount)
    const preset100 = page.locator(".preset-btn", { hasText: "100" });
    await preset100.click();
    await expect(calcBox).toContainText("Subtotal (100 cuentas):");
    await expect(calcBox).toContainText("3.000.000 COP");
    await expect(calcBox).toContainText("Descuento por volumen (-20%):");
    // 3.000.000 * 0.80 = 2.400.000
    await expect(calcBox).toContainText("2.400.000 COP");

    // Select 1000 leads (42% discount)
    const preset1000 = page.locator(".preset-btn", { hasText: "1.000" });
    await preset1000.click();
    await expect(calcBox).toContainText("Subtotal (1000 cuentas):");
    await expect(calcBox).toContainText("30.000.000 COP");
    await expect(calcBox).toContainText("Descuento por volumen (-42%):");
    // 30.000.000 * 0.58 = 17.400.000
    await expect(calcBox).toContainText("17.400.000 COP");
  });
});

import { test, expect } from "@playwright/test";

test.describe("Pricing Matrix & Volume Discount Curves", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/#precios");
  });

  test("should display the 3 intelligence tiers with correct base prices", async ({ page }) => {
    const pricingSection = page.locator("#precios");
    await expect(pricingSection).toBeVisible();

    // Verify Tier 1
    await expect(page.locator(".tier-name", { hasText: "TIER 1" })).toBeVisible();
    await expect(page.locator(".tier-price", { hasText: "$5.000 COP" })).toBeVisible();

    // Verify Tier 2 (Featured)
    await expect(page.locator(".tier-name", { hasText: "TIER 2" })).toBeVisible();
    await expect(page.locator(".tier-price", { hasText: "$30.000 COP" })).toBeVisible();

    // Verify Tier 3
    await expect(page.locator(".tier-name", { hasText: "TIER 3" })).toBeVisible();
    await expect(page.locator(".tier-price", { hasText: "$65.000 COP" })).toBeVisible();
  });

  test("should update generator calculation when switching tiers in pricing matrix", async ({ page }) => {
    // Choose Tier 1 in pricing matrix
    const chooseTier1Btn = page.locator("button:has-text('Elegir Tier 1')");
    await chooseTier1Btn.click();

    // Verify that the generator updates to Tier 1 pricing
    const calcBox = page.locator(".calc-summary-box");
    await expect(calcBox).toContainText("Precio unitario (Tier 1):");
    await expect(calcBox).toContainText("5.000 COP");

    // Choose Tier 3 in generator pills
    const tier3Pill = page.locator("button:has-text('Tier 3: Auditoría Financiera')");
    await tier3Pill.click();
    await expect(calcBox).toContainText("Precio unitario (Tier 3):");
    await expect(calcBox).toContainText("65.000 COP");
  });

  test("should apply volume discounts correctly (50 leads = 5%, 100 leads = 10%, 500 leads = 20%)", async ({ page }) => {
    await page.goto("/#generador");

    // Default is Tier 2 ($30.000 COP)
    // Select 10 leads (0% discount)
    const preset10 = page.locator(".preset-btn", { hasText: "10" }).first();
    await preset10.click();

    const calcBox = page.locator(".calc-summary-box");
    await expect(calcBox).toContainText("Subtotal (10 cuentas):");
    await expect(calcBox).toContainText("300.000 COP");
    await expect(calcBox).toContainText("300.000 COP"); // Total

    // Select 50 leads (5% discount in pricingSlice)
    const preset50 = page.locator(".preset-btn", { hasText: "50" });
    await preset50.click();
    await expect(calcBox).toContainText("Subtotal (50 cuentas):");
    await expect(calcBox).toContainText("1.500.000 COP");
    await expect(calcBox).toContainText("Descuento por volumen (-5%):");
    // 1.500.000 - 75.000 = 1.425.000
    await expect(calcBox).toContainText("1.425.000 COP");

    // Select 100 leads (10% discount)
    const preset100 = page.locator(".preset-btn", { hasText: "100" });
    await preset100.click();
    await expect(calcBox).toContainText("Subtotal (100 cuentas):");
    await expect(calcBox).toContainText("3.000.000 COP");
    await expect(calcBox).toContainText("Descuento por volumen (-10%):");
    // 3.000.000 - 300.000 = 2.700.000
    await expect(calcBox).toContainText("2.700.000 COP");
  });
});

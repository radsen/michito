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

    // Verify calculator summary updates to Tier 1 pricing
    const calcSummary = page.locator(".pricing-calc-summary");
    await expect(calcSummary).toContainText("DIRECTORIO BASE");
    await expect(calcSummary).toContainText("5.000 COP");

    // Choose Tier 3 in pricing matrix
    const chooseTier3Btn = page.locator("button:has-text('Elegir Auditoría')");
    await chooseTier3Btn.click();
    await expect(calcSummary).toContainText("AUDITORÍA COMPLETA");
    await expect(calcSummary).toContainText("65.000 COP");
  });

  test("should apply volume discounts correctly (50 leads = 12%, 100 leads = 20%, 1000 leads = 42%)", async ({ page }) => {
    // Default is Tier 2 ($30.000 COP)
    // Select 10 leads (0% discount)
    const preset10 = page.locator(".pricing-preset-btn", { hasText: "10" }).first();
    await preset10.click();

    const calcSummary = page.locator(".pricing-calc-summary");
    await expect(calcSummary).toContainText("Subtotal (10 cuentas):");
    await expect(calcSummary).toContainText("300.000 COP");

    // Select 50 leads (12% discount)
    const preset50 = page.locator(".pricing-preset-btn", { hasText: "50 (-12%)" });
    await preset50.click();
    await expect(calcSummary).toContainText("Subtotal (50 cuentas):");
    await expect(calcSummary).toContainText("1.500.000 COP");
    await expect(calcSummary).toContainText("Descuento por volumen (-12%):");
    await expect(calcSummary).toContainText("1.320.000 COP");

    // Select 100 leads (20% discount)
    const preset100 = page.locator(".pricing-preset-btn", { hasText: "100 (-20%)" });
    await preset100.click();
    await expect(calcSummary).toContainText("Subtotal (100 cuentas):");
    await expect(calcSummary).toContainText("3.000.000 COP");
    await expect(calcSummary).toContainText("Descuento por volumen (-20%):");
    await expect(calcSummary).toContainText("2.400.000 COP");

    // Select 1000 leads (42% discount)
    const preset1000 = page.locator(".pricing-preset-btn", { hasText: "1.000+ (-42%)" });
    await preset1000.click();
    await expect(calcSummary).toContainText("Subtotal (1000 cuentas):");
    await expect(calcSummary).toContainText("30.000.000 COP");
    await expect(calcSummary).toContainText("Descuento por volumen (-42%):");
    await expect(calcSummary).toContainText("17.400.000 COP");
  });
});

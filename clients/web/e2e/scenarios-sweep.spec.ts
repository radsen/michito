import { test, expect } from "@playwright/test";

test.describe("Multi-Scenario & Industry Sweep", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/#generador");
  });

  test("Scenario 1: B2B Software, APIs & SaaS (Chiketto) seeking tech buyers in Bogotá", async ({ page }) => {
    // Select Software Empresarial vertical
    const campaignSelect = page.locator("select.form-select");
    await campaignSelect.selectOption("chiketto");

    // City should automatically update to Bogotá
    const cityInput = page.locator(".form-group:has-text('Ciudad') input.form-input");
    await expect(cityInput).toHaveValue("Bogotá");

    // Select Contactos Directos
    const tier2Pill = page.locator("button:has-text('Contactos Directos')");
    await tier2Pill.click();

    // Select 50 accounts batch
    await page.locator(".preset-btn", { hasText: "50" }).click();

    // Verify summary reflects software campaign in Bogotá
    const calcBox = page.locator(".calc-summary-box");
    await expect(calcBox).toContainText("Subtotal (50 cuentas):");
    await expect(calcBox).toContainText("1.500.000 COP");
  });

  test("Scenario 2: Fuel Supply & Heavy Transport Fleets (Blueoil / Hebi) in Medellín", async ({ page }) => {
    const campaignSelect = page.locator("select.form-select");
    await campaignSelect.selectOption("blueoil");

    const cityInput = page.locator(".form-group:has-text('Ciudad') input.form-input");
    await expect(cityInput).toHaveValue("Medellín");

    // Set custom city (e.g., Rionegro / Oriente Antioqueño)
    await cityInput.fill("Rionegro");
    await expect(cityInput).toHaveValue("Rionegro");

    // Select Auditoría Completa
    const tier3Pill = page.locator("button:has-text('Auditoría Completa')");
    await tier3Pill.click();

    const calcBox = page.locator(".calc-summary-box");
    await expect(calcBox).toContainText("Auditoría Completa");
    await expect(calcBox).toContainText("65.000 COP");
  });

  test("Scenario 3: Corporate Real Estate & Coworking Offices (Tinkko) in Medellín", async ({ page }) => {
    const campaignSelect = page.locator("select.form-select");
    await campaignSelect.selectOption("tinkko_enterprise_offices");

    const cityInput = page.locator(".form-group:has-text('Ciudad') input.form-input");
    await expect(cityInput).toHaveValue("Medellín");

    // Volume of 25 leads
    const preset25 = page.locator(".preset-btn", { hasText: "25" });
    await preset25.click();

    // Verify calculator updates
    const calcBox = page.locator(".calc-summary-box");
    await expect(calcBox).toContainText("Subtotal (25 cuentas):");
  });

  test("Scenario 4: Industrial Warehouses & Logistics Hubs (Aburrá Norte)", async ({ page }) => {
    const campaignSelect = page.locator("select.form-select");
    await campaignSelect.selectOption("warehouse_aburra_norte");

    const cityInput = page.locator(".form-group:has-text('Ciudad') input.form-input");
    await expect(cityInput).toHaveValue("Medellín");

    // Change city to Girardota / Bello
    await cityInput.fill("Girardota");
    await expect(cityInput).toHaveValue("Girardota");

    const calcBox = page.locator(".calc-summary-box");
    await expect(calcBox).toBeVisible();
  });

  test("Scenario 5: Facility Management, Security & Corporate Cleaning", async ({ page }) => {
    const campaignSelect = page.locator("select.form-select");
    await campaignSelect.selectOption("facility_services_b2b");

    const cityInput = page.locator(".form-group:has-text('Ciudad') input.form-input");
    await expect(cityInput).toHaveValue("Medellín");

    // Select Directorio Base
    const tier1Pill = page.locator("button:has-text('Directorio Base')");
    await tier1Pill.click();

    const calcBox = page.locator(".calc-summary-box");
    await expect(calcBox).toContainText("Directorio Base");
    await expect(calcBox).toContainText("5.000 COP");
  });
});

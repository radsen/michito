import { test, expect } from "@playwright/test";

test.describe("Multi-Scenario & Industry Sweep", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/#generador");
    // Switch to manual mode to access industry presets & territory allocator
    await page.locator(".generator-mode-tab").nth(1).click();
  });

  test("Scenario 1: B2B Software, APIs & SaaS (Chiketto) seeking tech buyers in Bogotá", async ({ page }) => {
    // Select Software Empresarial preset
    await page.locator("button:has-text('🇨🇴 Software Empresarial')").click();

    // Territory allocations should feature Bogotá
    const geoTable = page.locator(".geo-allocations-table");
    await expect(geoTable).toContainText("Bogotá");

    // Select Contactos Directos (Tier 2)
    const tier2Pill = page.locator(".tier-pill").nth(1);
    await tier2Pill.click();

    // Select 50 accounts batch
    await page.getByRole("button", { name: "50", exact: true }).click();

    // Verify summary reflects software campaign
    const calcBox = page.locator(".calc-summary-box");
    await expect(calcBox).toContainText("Subtotal (50 cuentas):");
    await expect(calcBox).toContainText("1.500.000 COP");
  });

  test("Scenario 2: Fuel Supply & Heavy Transport Fleets (Blueoil / Hebi) in Medellín", async ({ page }) => {
    // Select Combustibles preset
    await page.locator("button:has-text('🇨🇴 Combustibles & Flotas')").click();

    const geoTable = page.locator(".geo-allocations-table");
    await expect(geoTable).toContainText("Medellín");

    // Select Auditoría Completa (Tier 3)
    const tier3Pill = page.locator(".tier-pill").nth(2);
    await tier3Pill.click();

    const calcBox = page.locator(".calc-summary-box");
    await expect(calcBox).toContainText("Auditoría Completa");
    await expect(calcBox).toContainText("65.000 COP");
  });

  test("Scenario 3: Corporate Real Estate & Coworking Offices (Tinkko) in Medellín", async ({ page }) => {
    // Select Coworking & Oficinas preset
    await page.locator("button:has-text('🇨🇴 Espacios & Sedes')").click();

    const geoTable = page.locator(".geo-allocations-table");
    await expect(geoTable).toContainText("Medellín");

    // Volume of 25 leads
    await page.getByRole("button", { name: "25", exact: true }).click();

    // Verify calculator updates
    const calcBox = page.locator(".calc-summary-box");
    await expect(calcBox).toContainText("Subtotal (25 cuentas):");
  });

  test("Scenario 4: Industrial Warehouses & Logistics Hubs (Aburrá Norte)", async ({ page }) => {
    // Select Parques Industriales preset
    await page.locator("button:has-text('🇨🇴 Parques Industriales')").click();

    const geoTable = page.locator(".geo-allocations-table");
    await expect(geoTable).toContainText("Bello");

    const calcBox = page.locator(".calc-summary-box");
    await expect(calcBox).toBeVisible();
  });

  test("Scenario 5: Facility Management, Security & Corporate Cleaning", async ({ page }) => {
    // Select Facility Services preset
    await page.locator("button:has-text('🇨🇴 Facility Services')").click();

    const geoTable = page.locator(".geo-allocations-table");
    await expect(geoTable).toContainText("Medellín");

    // Select Directorio Base (Tier 1)
    const tier1Pill = page.locator(".tier-pill").nth(0);
    await tier1Pill.click();

    const calcBox = page.locator(".calc-summary-box");
    await expect(calcBox).toContainText("Directorio Base");
    await expect(calcBox).toContainText("5.000 COP");
  });
});

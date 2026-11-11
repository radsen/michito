import { test, expect } from "@playwright/test";

test.describe("Multi-Currency Support (COP, DOP, USD)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("should display currency switcher in navbar with default 🇨🇴 COP", async ({ page }) => {
    const currencyDropdown = page.locator("[data-testid='currency-dropdown']");
    await expect(currencyDropdown).toBeVisible();
    await expect(currencyDropdown).toContainText("🇨🇴");
    await expect(currencyDropdown).toContainText("COP");
  });

  test("should switch currency to 🇩🇴 DOP and update pricing cards and generator", async ({ page }) => {
    // Open currency dropdown and select DOP
    const currencyDropdownBtn = page.locator(".currency-switcher-btn");
    await currencyDropdownBtn.click();

    const dopItem = page.locator(".currency-dropdown-item:has-text('DOP')");
    await expect(dopItem).toBeVisible();
    await dopItem.click();

    // Verify navbar displays DOP
    await expect(currencyDropdownBtn).toContainText("🇩🇴");
    await expect(currencyDropdownBtn).toContainText("DOP");

    // Scroll to pricing section and verify prices are in DOP
    await page.goto("/#precios");
    await expect(page.locator(".tier-price", { hasText: "RD$ 100 DOP" })).toBeVisible();
    await expect(page.locator(".tier-price", { hasText: "RD$ 350 DOP" })).toBeVisible();
    await expect(page.locator(".tier-price", { hasText: "RD$ 750 DOP" })).toBeVisible();

    // Verify generator calculation reflects DOP
    const calcBox = page.locator(".calc-summary-box");
    await expect(calcBox).toContainText("RD$ 350 DOP");
  });

  test("should switch currency to 🇺🇸 USD and display clean decimal pricing", async ({ page }) => {
    // Switch to USD via segmented control in pricing section
    await page.goto("/#precios");
    const usdSegmentedBtn = page.locator(".currency-segmented-btn:has-text('USD')");
    await usdSegmentedBtn.click();

    // Verify prices updated to USD
    await expect(page.locator(".tier-price", { hasText: "$1.50 USD" })).toBeVisible();
    await expect(page.locator(".tier-price", { hasText: "$7.50 USD" })).toBeVisible();
    await expect(page.locator(".tier-price", { hasText: "$16 USD" })).toBeVisible();

    // Verify navbar also synchronized to USD
    const currencyDropdownBtn = page.locator(".currency-switcher-btn");
    await expect(currencyDropdownBtn).toContainText("🇺🇸");
    await expect(currencyDropdownBtn).toContainText("USD");
  });

  test("should automatically switch to DOP when selecting Dominican Republic campaign", async ({ page }) => {
    await page.goto("/#generador");
    const campaignSelect = page.locator("select.form-select");
    await campaignSelect.selectOption("tinkko_dr_offices");

    // Navbar should now show DOP
    const currencyDropdownBtn = page.locator(".currency-switcher-btn");
    await expect(currencyDropdownBtn).toContainText("🇩🇴");
    await expect(currencyDropdownBtn).toContainText("DOP");

    // Calculation should display in DOP
    const calcBox = page.locator(".calc-summary-box");
    await expect(calcBox).toContainText("DOP");
  });

  test("should switch to USD and show Country Allocator when selecting Cross-Border campaign", async ({ page }) => {
    await page.goto("/#generador");
    const campaignSelect = page.locator("select.form-select");
    await campaignSelect.selectOption("eventos_ferias_b2b");

    // Navbar should now show USD
    const currencyDropdownBtn = page.locator(".currency-switcher-btn");
    await expect(currencyDropdownBtn).toContainText("USD");

    // Quota Allocator Card should be visible
    const allocator = page.locator(".bg-slate-900\\/80");
    await expect(allocator.getByText("Distribución de Cuota Multi-País")).toBeVisible();
    await expect(allocator.getByText("🇨🇴 Colombia", { exact: true })).toBeVisible();
    await expect(allocator.getByText("🇩🇴 Rep. Dom.", { exact: true })).toBeVisible();
    await expect(allocator.getByText("🇪🇨 Ecuador", { exact: true })).toBeVisible();
  });

  test("should switch to USD and suggest Ecuadorian cities when selecting Ecuador campaign", async ({ page }) => {
    await page.goto("/#generador");
    const campaignSelect = page.locator("select.form-select");
    await campaignSelect.selectOption("tinkko_ec_offices");

    // Navbar should now show USD
    const currencyDropdownBtn = page.locator(".currency-switcher-btn");
    await expect(currencyDropdownBtn).toContainText("USD");

    // City pills should show Ecuadorian cities
    await expect(page.locator(".city-pill:has-text('Quito')")).toBeVisible();
    await expect(page.locator(".city-pill:has-text('Guayaquil')")).toBeVisible();
  });
});


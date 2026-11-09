import { test, expect } from "@playwright/test";

test.describe("Landing Page & Value Proposition", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("should display the brand hero and core value proposition", async ({ page }) => {
    // Check main branding in navbar
    await expect(page.locator(".navbar-container .brand-name")).toContainText("MICHITO");
    await expect(page.locator(".navbar-container .brand-logo-badge")).toContainText("導人");

    // Check Hero title and kicker
    const heroTitle = page.locator(".hero-title");
    await expect(heroTitle).toBeVisible();
    await expect(heroTitle).toContainText("Inteligencia Comercial B2B");

    // Check statistical highlights
    await expect(page.locator(".hero-stats-grid")).toBeVisible();
    await expect(page.locator("text=Alta Entregabilidad")).toBeVisible();
    await expect(page.locator("text=Contacto Institucional")).toBeVisible();
  });

  test("should toggle language between Spanish (es_CO) and English (en_US)", async ({ page }) => {
    // Verify default Spanish copy
    await expect(page.locator(".hero-title")).toContainText("Inteligencia Comercial B2B");

    // Click language switcher button to toggle to English
    const langBtn = page.locator(".lang-switcher-btn");
    await expect(langBtn).toContainText("🇨🇴 ES");
    await langBtn.click();

    // Verify copy translated to English and button shows 🇺🇸 EN
    await expect(langBtn).toContainText("🇺🇸 EN");
    await expect(page.locator(".hero-title")).toContainText("B2B Sales Intelligence");

    // Toggle back to Spanish
    await langBtn.click();
    await expect(langBtn).toContainText("🇨🇴 ES");
    await expect(page.locator(".hero-title")).toContainText("Inteligencia Comercial B2B");
  });

  test("should display comparative table against legacy databases (Apollo / ZoomInfo)", async ({ page }) => {
    const comparisonSection = page.locator(".comparison-section");
    await expect(comparisonSection).toBeVisible();

    // Verify key comparative columns
    await expect(page.locator("text=Bases Tradicionales")).toBeVisible();
    await expect(page.locator("text=Inteligencia Fresca On-Demand")).toBeVisible();
  });

  test("should scroll smoothly to target sections via navbar", async ({ page }) => {
    const verticalsBtn = page.locator("nav.desktop-nav button:has-text('Verticales')");
    await verticalsBtn.click();
    await expect(page.locator("#verticales")).toBeInViewport();

    const pricingBtn = page.locator("nav.desktop-nav button:has-text('Precios')");
    await pricingBtn.click();
    await expect(page.locator("#precios")).toBeInViewport();
  });
});

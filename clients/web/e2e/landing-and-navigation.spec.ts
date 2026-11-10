import { test, expect } from "@playwright/test";

test.describe("Landing Page & Value Proposition", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("should display the brand hero and core value proposition", async ({ page }) => {
    // Check main branding in navbar
    await expect(page.locator(".navbar-container .brand-name")).toContainText("MICHITO");
    await expect(page.locator(".navbar-container .brand-logo-badge")).toContainText("M");

    // Check Hero title and kicker
    const heroTitle = page.locator(".hero-title");
    await expect(heroTitle).toBeVisible();
    await expect(heroTitle).toContainText("Clientes Potenciales Verificados");

    // Check statistical highlights
    await expect(page.locator(".hero-stats-grid")).toBeVisible();
    await expect(page.locator("text=>95% Entregabilidad")).toBeVisible();
    await expect(page.locator("text=Contactos Directos")).toBeVisible();
  });

  test("should toggle language between Spanish (es_CO) and English (en_US)", async ({ page }) => {
    // Verify default Spanish copy
    await expect(page.locator(".hero-title")).toContainText("Clientes Potenciales Verificados");

    // Click language switcher button to toggle to English
    const langBtn = page.locator(".lang-switcher-btn");
    await expect(langBtn).toContainText("🇨🇴 ES");
    await langBtn.click();

    // Verify copy translated to English and button shows 🇺🇸 EN
    await expect(langBtn).toContainText("🇺🇸 EN");
    await expect(page.locator(".hero-title")).toContainText("Verified B2B Leads");

    // Toggle back to Spanish
    await langBtn.click();
    await expect(langBtn).toContainText("🇨🇴 ES");
    await expect(page.locator(".hero-title")).toContainText("Clientes Potenciales Verificados");
  });

  test("should display comparative table against legacy databases (Apollo / ZoomInfo)", async ({ page }) => {
    const comparisonSection = page.locator(".comparison-section");
    await expect(comparisonSection).toBeVisible();

    // Verify key comparative columns
    await expect(page.locator("text=Bases Tradicionales")).toBeVisible();
    await expect(page.locator("text=Lotes en Vivo Michito")).toBeVisible();
  });

  test("should scroll smoothly to target sections via navbar", async ({ page }) => {
    const howItWorksBtn = page.locator("nav.desktop-nav button:has-text('Cómo Funciona')");
    await howItWorksBtn.click();
    await expect(page.locator("#como-funciona")).toBeInViewport();

    const pricingBtn = page.locator("nav.desktop-nav button:has-text('Precios')");
    await pricingBtn.click();
    await expect(page.locator("#precios")).toBeInViewport();
  });
});

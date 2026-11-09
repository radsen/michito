import { test, expect } from "@playwright/test";

test.describe("v1.2 Multi-Partner Affiliate & Commission Tracking", () => {
  test("should detect ?ref=tinkko, display partner co-branding banner, and submit order with tinkko attribution", async ({ page }) => {
    // Intercept Partner API
    await page.route("**/api/v1/partners/tinkko", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "success",
          partner: {
            partner_id: "tinkko",
            name: "Tinkko Coworking & Sedes",
            commission_rate: 0.25,
            discount_rate: 0.10,
            badge_text: "🤝 Alianza Oficial: Beneficio Exclusivo para Residentes Tinkko",
            default_campaign_id: "tinkko_enterprise_offices",
            description: "Red de espacios corporativos y coworking en Medellín y Bogotá.",
            active: true,
          },
        }),
      });
    });

    let interceptedPartner: string | null = null;

    // Intercept Order Creation
    await page.route("**/api/v1/orders", async (route) => {
      if (route.request().method() === "POST") {
        const postData = JSON.parse(route.request().postData() || "{}");
        interceptedPartner = postData.client?.referral_partner;

        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            status: "success",
            order_id: "ord_playwright_tinkko_123",
            order_status: "awaiting_payment",
            amount_in_cents: 67500000,
            total_price_cop: 675000,
            message: "Orden con beneficio Tinkko creada exitosamente.",
          }),
        });
      } else {
        await route.continue();
      }
    });

    // 1. Visit landing page with referral query parameter
    await page.goto("/?ref=tinkko");

    // 2. Verify Partner Top Co-Branded Banner
    const banner = page.locator('[data-testid="partner-banner"]');
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("Alianza Oficial: Beneficio Exclusivo para Residentes Tinkko");
    await expect(banner).toContainText("10% OFF APLICADO");

    // 3. Verify Partner Notice inside Generator Form Card
    const partnerNotice = page.locator('[data-testid="partner-order-notice"]');
    await expect(partnerNotice).toBeVisible();
    await expect(partnerNotice).toContainText("Tinkko Coworking & Sedes");

    // 4. Fill contact information
    await page.locator("input[placeholder='Ej: Juan Carlos Pérez']").fill("Tinkko Resident Buyer");
    await page.locator("input[placeholder='director@empresa.com']").fill("resident@tinkkocompany.com");
    await page.locator("input[placeholder='+57 300 123 4567']").fill("+573009998888");

    // 5. Submit order
    const submitBtn = page.locator(".generator-submit-btn");
    await submitBtn.click();

    // 6. Verify intercepted order payload carried 'tinkko' referral partner
    await expect.poll(() => interceptedPartner).toBe("tinkko");
  });

  test("should detect ?ref=eventos_medellin for Trade Show & Hosted Buyers and auto-select campaign", async ({ page }) => {
    await page.route("**/api/v1/partners/eventos_medellin", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "success",
          partner: {
            partner_id: "eventos_medellin",
            name: "Plaza Mayor & Eventos B2B",
            commission_rate: 0.20,
            discount_rate: 0.10,
            badge_text: "🎪 Partner Oficial de Ferias y Convenciones",
            default_campaign_id: "eventos_ferias_b2b",
            description: "Operadores de ferias comerciales, congresos y matchmaking de compradores.",
            active: true,
          },
        }),
      });
    });

    let interceptedPartner: string | null = null;
    let interceptedCampaign: string | null = null;

    await page.route("**/api/v1/orders", async (route) => {
      if (route.request().method() === "POST") {
        const postData = JSON.parse(route.request().postData() || "{}");
        interceptedPartner = postData.client?.referral_partner;
        interceptedCampaign = postData.request?.campaign_id;

        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            status: "success",
            order_id: "ord_playwright_eventos_456",
            order_status: "awaiting_payment",
            amount_in_cents: 67500000,
            total_price_cop: 675000,
          }),
        });
      } else {
        await route.continue();
      }
    });

    await page.goto("/?ref=eventos_medellin");

    // Verify Banner
    const banner = page.locator('[data-testid="partner-banner"]');
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("Partner Oficial de Ferias y Convenciones");

    // Verify campaign dropdown auto-selected
    const campaignSelect = page.locator("select.form-select");
    await expect(campaignSelect).toHaveValue("eventos_ferias_b2b");

    // Fill contact information & submit order
    await page.locator("input[placeholder='Ej: Juan Carlos Pérez']").fill("Fair Organizer Pro");
    await page.locator("input[placeholder='director@empresa.com']").fill("director@eventosferias.com");

    const submitBtn = page.locator(".generator-submit-btn");
    await submitBtn.click();

    await expect.poll(() => interceptedPartner).toBe("eventos_medellin");
    await expect.poll(() => interceptedCampaign).toBe("eventos_ferias_b2b");
  });

  test("should default to direct organic attribution when no partner query param is present", async ({ page }) => {
    let interceptedPartner: string | null = null;

    await page.route("**/api/v1/orders", async (route) => {
      if (route.request().method() === "POST") {
        const postData = JSON.parse(route.request().postData() || "{}");
        interceptedPartner = postData.client?.referral_partner;

        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            status: "success",
            order_id: "ord_playwright_direct_789",
            order_status: "awaiting_payment",
            amount_in_cents: 75000000,
            total_price_cop: 750000,
          }),
        });
      } else {
        await route.continue();
      }
    });

    await page.goto("/");

    // Banner should NOT exist
    const banner = page.locator('[data-testid="partner-banner"]');
    await expect(banner).not.toBeVisible();

    // Fill contact information & submit order
    await page.locator("input[placeholder='Ej: Juan Carlos Pérez']").fill("Organic Direct Buyer");
    await page.locator("input[placeholder='director@empresa.com']").fill("direct@buyer.co");

    const submitBtn = page.locator(".generator-submit-btn");
    await submitBtn.click();

    await expect.poll(() => interceptedPartner).toBe("direct");
  });
});

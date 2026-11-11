import { test, expect } from "@playwright/test";

test.describe("Order Creation, Wompi Payment & Delivery Tracking", () => {
  test("should create order, launch Wompi modal, and transition to live tracking", async ({ page }) => {
    // Intercept POST /api/v1/orders to return a deterministic test order
    await page.route("**/api/v1/orders", async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            status: "success",
            order_id: "ord_playwright_e2e_999",
            order_status: "awaiting_payment",
            amount_in_cents: 142500000,
            total_price_cop: 1425000,
            message: "Orden creada exitosamente.",
          }),
        });
      } else {
        await route.continue();
      }
    });

    // Intercept GET /api/v1/orders/ord_playwright_e2e_999
    await page.route("**/api/v1/orders/ord_playwright_e2e_999", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          order_id: "ord_playwright_e2e_999",
          status: "awaiting_payment",
          payment_status: "pending",
          limit: 50,
          tier: 2,
          total_price_cop: 1425000,
          amount_in_cents: 142500000,
          client: {
            name: "Radsen Tech Buyer",
            email: "radsen@chiketto.com",
            phone: "+573009998888",
          },
          sample_leads: [
            {
              company_name: "Fintech Soluciones Colombia S.A.S.",
              nit: "901.234.567-8",
              decision_maker_name: "Alejandro Restrepo Gómez",
              decision_maker_role: "Chief Technology Officer (CTO)",
              email: "a***@fintechcolombia.co",
              phone: "+57 310 *** **99",
              intent_trigger: "Ampliación de Infraestructura Cloud & APIs",
              solvency_tier: "A+",
              underwriting_grade: "EXCELLENT",
            },
            {
              company_name: "Logística y Transporte del Valle S.A.S.",
              nit: "890.111.222-3",
              decision_maker_name: "María Camila Morales",
              decision_maker_role: "Gerente General",
              email: "m***@logisticavalle.com",
              phone: "+57 320 *** **11",
              intent_trigger: "Renovación de Flota & Control de Combustible",
              solvency_tier: "A",
              underwriting_grade: "GOOD",
            },
          ],
          csv_download_url: "/downloads/ord_playwright_e2e_999_leads.csv",
          dossier_download_url: "/downloads/ord_playwright_e2e_999_dossier.xlsx",
        }),
      });
    });

    // Intercept POST /api/v1/orders/ord_playwright_e2e_999/pay
    await page.route("**/api/v1/orders/ord_playwright_e2e_999/pay", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "success",
          order: {
            order_id: "ord_playwright_e2e_999",
            status: "paid",
            csv_download_url: "/downloads/ord_playwright_e2e_999_leads.csv",
            dossier_download_url: "/downloads/ord_playwright_e2e_999_dossier.xlsx",
          },
        }),
      });
    });

    await page.goto("/#generador");

    // Advance from Step 1 to Step 2: Datos de Entrega
    await page.locator("button:has-text('Continuar a Datos de Entrega')").click();

    // Fill in buyer information
    const nameInput = page.locator("input[placeholder='Ej: Juan Carlos Pérez']");
    await nameInput.fill("Radsen Tech Buyer");

    const emailInput = page.locator("input[placeholder='director@empresa.com']");
    await emailInput.fill("radsen@chiketto.com");

    const phoneInput = page.locator("input[placeholder='+57 300 123 4567']");
    await phoneInput.fill("+573009998888");

    // Click submit order button
    const submitBtn = page.locator(".generator-submit-btn");
    await submitBtn.click();

    // Verify LiveStatusTracker displays the active order reference
    const trackerArea = page.locator(".generator-tracker-area");
    await expect(trackerArea).toBeVisible();
    await expect(trackerArea).toContainText("ord_playwright_e2e_999");

    // Verify Sample Teaser Table renders masked leads
    const teaserTable = page.locator(".teaser-table");
    await expect(teaserTable).toBeVisible();
    await expect(page.locator("text=Fintech Soluciones Colombia S.A.S.")).toBeVisible();
    await expect(page.locator("text=Alejandro Restrepo Gómez")).toBeVisible();
    await expect(page.locator("text=Chief Technology Officer (CTO)")).toBeVisible();

    // Click unlock / pay button in the teaser bar
    const unlockBtn = page.locator(".teaser-pay-btn");
    await unlockBtn.click();

    // Verify Wompi Modal Card is visible
    const modalCard = page.locator(".modal-card");
    await expect(modalCard).toBeVisible();
    await expect(modalCard).toContainText("ord_playwright_e2e_999");

    // Click simulated payment confirmation
    const directPayBtn = modalCard.locator("button:has-text('Aprobar Directo')");
    await directPayBtn.click();

    // Modal closes upon successful payment
    await expect(modalCard).not.toBeVisible();

    // Unlocked download card is rendered
    const unlockedCard = page.locator(".deliverables-unlocked-card");
    await expect(unlockedCard).toBeVisible();
    await expect(unlockedCard).toContainText("Entregables Listos para Descarga Inmediata");
    await expect(page.locator("a.csv-download")).toBeVisible();
    await expect(page.locator("a.dossier-download")).toBeVisible();
  });
});

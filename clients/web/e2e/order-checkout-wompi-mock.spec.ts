import { test, expect } from "@playwright/test";

test.describe("Order Creation, Wompi Payment & Delivery Tracking", () => {
  const setupOrderMocks = async (page: any, orderId: string = "ord_playwright_e2e_999") => {
    // Intercept POST /api/v1/orders to return a deterministic test order
    await page.route("**/api/v1/orders", async (route: any) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            status: "success",
            order_id: orderId,
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

    // Intercept GET /api/v1/orders/{orderId}
    await page.route(`**/api/v1/orders/${orderId}`, async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          order_id: orderId,
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
          csv_download_url: `/downloads/${orderId}_leads.csv`,
          dossier_download_url: `/downloads/${orderId}_dossier.xlsx`,
        }),
      });
    });

    // Intercept POST /api/v1/orders/{orderId}/pay
    await page.route(`**/api/v1/orders/${orderId}/pay`, async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "success",
          order: {
            order_id: orderId,
            status: "paid",
            csv_download_url: `/downloads/${orderId}_leads.csv`,
            dossier_download_url: `/downloads/${orderId}_dossier.xlsx`,
          },
        }),
      });
    });
  };

  const advanceToCheckoutModal = async (page: any, orderId: string = "ord_playwright_e2e_999") => {
    await setupOrderMocks(page, orderId);
    await page.goto("/#generador");

    // Advance to Step 2
    await page.locator("button:has-text('Continuar a Datos de Entrega')").click();

    // Fill buyer details
    await page.locator("input[placeholder='Ej: Juan Carlos Pérez']").fill("Radsen Tech Buyer");
    await page.locator("input[placeholder='director@empresa.com']").fill("radsen@chiketto.com");
    await page.locator("input[placeholder='+57 300 123 4567']").fill("+573009998888");

    // Submit order
    await page.locator(".generator-submit-btn").click();

    // Verify radar scan result in tracker
    const trackerArea = page.locator(".generator-tracker-area");
    await expect(trackerArea).toBeVisible();
    await expect(trackerArea).toContainText(orderId);

    // Open Wompi modal from teaser bar
    const unlockBtn = page.locator(".teaser-pay-btn");
    await unlockBtn.click();

    const modalCard = page.locator(".modal-card");
    await expect(modalCard).toBeVisible();
    await expect(modalCard).toContainText(orderId);
    return modalCard;
  };

  test("should create order, launch Wompi modal, and transition to live tracking (Direct Approval)", async ({ page }) => {
    const modalCard = await advanceToCheckoutModal(page, "ord_playwright_e2e_999");

    // Click direct simulated payment confirmation
    const directPayBtn = modalCard.locator("button:has-text('Aprobar Directo')");
    await directPayBtn.click();

    // Modal closes upon successful payment
    await expect(modalCard).not.toBeVisible();

    // Unlocked download card is rendered
    const unlockedCard = page.locator(".deliverables-unlocked-card");
    await expect(unlockedCard).toBeVisible();
    await expect(unlockedCard).toContainText("Entregables Listos para Descarga Inmediata");
    await expect(page.locator("a.csv-download")).toBeVisible();
    await expect(page.locator("a.xlsx-download")).toBeVisible();
    await expect(page.locator("a.pdf-download")).toBeVisible();
  });

  test("Scenario A: Wompi Approved Card (4242 4242 4242 4242) via Widget", async ({ page }) => {
    // Inject mock Wompi WidgetCheckout returning APPROVED
    await page.addInitScript(() => {
      (window as any).WidgetCheckout = function (config: any) {
        this.config = config;
        this.open = function (callback: (result: any) => void) {
          callback({
            transaction: {
              id: "tx_wompi_app_4242",
              status: "APPROVED",
              amount_in_cents: config.amountInCents,
              reference: config.reference,
              payment_method_type: "CARD",
            },
          });
        };
      };
    });

    const modalCard = await advanceToCheckoutModal(page, "ord_playwright_wompi_app");

    // Click "Pagar con Pasarela Wompi"
    const payBtn = modalCard.locator(".modal-primary-btn");
    await payBtn.click();

    // Modal closes upon successful payment
    await expect(modalCard).not.toBeVisible();

    // Unlocked download card appears with verified deliverables
    const unlockedCard = page.locator(".deliverables-unlocked-card");
    await expect(unlockedCard).toBeVisible();
    await expect(unlockedCard).toContainText("Entregables Listos para Descarga Inmediata");
    await expect(page.locator("a.csv-download")).toBeVisible();
    await expect(page.locator("a.xlsx-download")).toBeVisible();
    await expect(page.locator("a.pdf-download")).toBeVisible();
  });

  test("Scenario B: Wompi Declined Card (4242 4242 4242 4241)", async ({ page }) => {
    // Inject mock Wompi WidgetCheckout returning DECLINED
    await page.addInitScript(() => {
      (window as any).WidgetCheckout = function (config: any) {
        this.config = config;
        this.open = function (callback: (result: any) => void) {
          callback({
            transaction: {
              id: "tx_wompi_dec_4241",
              status: "DECLINED",
              status_message: "La tarjeta fue rechazada por la entidad emisora.",
              reference: config.reference,
            },
          });
        };
      };
    });

    const modalCard = await advanceToCheckoutModal(page, "ord_playwright_wompi_dec");

    // Click "Pagar con Pasarela Wompi"
    const payBtn = modalCard.locator(".modal-primary-btn");
    await payBtn.click();

    // Modal closes after transaction completes
    await expect(modalCard).not.toBeVisible();

    // Deliverables MUST remain locked since payment was declined
    const unlockedCard = page.locator(".deliverables-unlocked-card");
    await expect(unlockedCard).not.toBeVisible();

    // Teaser pay button remains available to retry payment
    const unlockBtn = page.locator(".teaser-pay-btn");
    await expect(unlockBtn).toBeVisible();
  });

  test("Scenario C: Wompi High Risk / Fraud Card (4000 0000 0000 0005)", async ({ page }) => {
    // Inject mock Wompi WidgetCheckout returning ERROR / RISK
    await page.addInitScript(() => {
      (window as any).WidgetCheckout = function (config: any) {
        this.config = config;
        this.open = function (callback: (result: any) => void) {
          callback({
            transaction: {
              id: "tx_wompi_risk_0005",
              status: "ERROR",
              status_message: "Transacción rechazada por scoring de riesgo y prevención de fraude.",
              reference: config.reference,
            },
          });
        };
      };
    });

    const modalCard = await advanceToCheckoutModal(page, "ord_playwright_wompi_risk");

    // Click "Pagar con Pasarela Wompi"
    const payBtn = modalCard.locator(".modal-primary-btn");
    await payBtn.click();

    // Modal closes
    await expect(modalCard).not.toBeVisible();

    // Deliverables MUST remain locked
    const unlockedCard = page.locator(".deliverables-unlocked-card");
    await expect(unlockedCard).not.toBeVisible();

    // Order status in tracker still shows awaiting payment
    const trackerArea = page.locator(".generator-tracker-area");
    await expect(trackerArea).toContainText("ord_playwright_wompi_risk");
  });

  test("Scenario D: Wompi PSE Online Bank Transfer (Banco Unión Colombiano)", async ({ page }) => {
    // Inject mock Wompi WidgetCheckout returning APPROVED via PSE
    await page.addInitScript(() => {
      (window as any).WidgetCheckout = function (config: any) {
        this.config = config;
        this.open = function (callback: (result: any) => void) {
          callback({
            transaction: {
              id: "tx_wompi_pse_union",
              status: "APPROVED",
              payment_method_type: "PSE",
              amount_in_cents: config.amountInCents,
              reference: config.reference,
            },
          });
        };
      };
    });

    const modalCard = await advanceToCheckoutModal(page, "ord_playwright_wompi_pse");

    // Click "Pagar con Pasarela Wompi"
    const payBtn = modalCard.locator(".modal-primary-btn");
    await payBtn.click();

    // Modal closes
    await expect(modalCard).not.toBeVisible();

    // Deliverables are unlocked
    const unlockedCard = page.locator(".deliverables-unlocked-card");
    await expect(unlockedCard).toBeVisible();
    await expect(unlockedCard).toContainText("Entregables Listos para Descarga Inmediata");
  });

  test("should support regional territory allocation and customer exclusions", async ({ page }) => {
    let capturedPayload: any = null;
    await page.route("**/api/v1/orders", async (route) => {
      if (route.request().method() === "POST") {
        capturedPayload = JSON.parse(route.request().postData() || "{}");
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            status: "success",
            order_id: "ord_playwright_excl_101",
            order_status: "awaiting_payment",
            amount_in_cents: 30000000,
            total_price_cop: 300000,
            message: "Orden creada con exclusiones.",
          }),
        });
      } else {
        await route.continue();
      }
    });

    await page.goto("/#generador");

    // Switch to manual mode to configure territory allocations
    await page.locator(".generator-mode-tab").nth(1).click();

    // Verify default territory allocations are rendered
    const geoList = page.locator(".geo-allocations-table");
    await expect(geoList).toBeVisible();
    await expect(geoList).toContainText("Medellín");

    // Open Exclusion Drawer
    const exclusionToggle = page.locator(".exclusions-toggle-btn");
    await expect(exclusionToggle).toBeVisible();
    await exclusionToggle.click();

    // Fill in domains and NITs
    const exclusionTextarea = page.locator(".exclusions-textarea");
    await expect(exclusionTextarea).toBeVisible();
    await exclusionTextarea.fill("hebisend.com, 900123456, competitor.co");

    // Verify active exclusions badge is updated
    await expect(page.locator(".exclusions-count-badge")).toBeVisible();
    await expect(page.locator(".exclusions-count-badge")).toContainText("3 exclusiones activas");

    // Advance to Step 2
    await page.locator("button:has-text('Continuar a Datos de Entrega')").click();

    // Verify Recap Box reflects Exclusions
    const recapBox = page.locator(".generator-recap-box");
    await expect(recapBox).toBeVisible();
    await expect(recapBox).toContainText("3 cuentas excluidas");

    // Fill in buyer info and submit
    await page.locator("input[placeholder='Ej: Juan Carlos Pérez']").fill("Regional Lead Buyer");
    await page.locator("input[placeholder='director@empresa.com']").fill("buyer@hebisend-test.com");
    await page.locator(".generator-submit-btn").click();

    // Verify sent payload
    expect(capturedPayload).not.toBeNull();
    expect(capturedPayload.request.exclusions).toEqual(["hebisend.com", "900123456", "competitor.co"]);
  });
});


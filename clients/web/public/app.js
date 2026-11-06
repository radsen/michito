/**
 * Michito Web Client Portal (B2B Lead Intelligence Order Engine)
 * Integrates with Firebase Local Emulators (Firestore on 8080) and simulated Wompi gateway.
 */

const FIRESTORE_EMULATOR_BASE = "http://localhost:8080/v1/projects/michito-prod/databases/(default)/documents/orders";

const form = document.getElementById("order-form");
const statusCard = document.getElementById("order-status-card");
const activeOrderIdEl = document.getElementById("active-order-id");
const orderBadgeEl = document.getElementById("order-badge");
const orderStatusTitle = document.getElementById("order-status-title");
const orderStatusDesc = document.getElementById("order-status-desc");
const progressBarFill = document.getElementById("progress-bar-fill");
const teaserContainer = document.getElementById("teaser-container");
const teaserCards = document.getElementById("teaser-cards");
const teaserTotal = document.getElementById("teaser-total");
const priceAmount = document.getElementById("price-amount");
const payBtn = document.getElementById("pay-btn");
const deliveryContainer = document.getElementById("delivery-container");
const downloadCsvBtn = document.getElementById("download-csv-btn");
const downloadDossierBtn = document.getElementById("download-dossier-btn");

let currentOrderId = null;
let pollInterval = null;

// Handle Form Submission
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const campaignSelect = document.getElementById("campaign-select");
  const selectedOption = campaignSelect.options[campaignSelect.selectedIndex];
  const campaignId = selectedOption.value;
  const country = selectedOption.dataset.country;
  const currency = selectedOption.dataset.currency;
  const city = document.getElementById("target-city").value.trim();
  const limit = parseInt(document.getElementById("leads-limit").value, 10);
  const clientName = document.getElementById("client-name").value.trim();
  const clientEmail = document.getElementById("client-email").value.trim();
  const clientPhone = document.getElementById("client-phone").value.trim();

  // Generate Unique Order ID
  const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const randomHex = Math.random().toString(16).substring(2, 8);
  currentOrderId = `ord_${dateStr}_${randomHex}`;

  // Build Firestore Document Payload
  const orderDoc = {
    fields: {
      order_id: { stringValue: currentOrderId },
      client: {
        mapValue: {
          fields: {
            name: { stringValue: clientName },
            email: { stringValue: clientEmail },
            phone: { stringValue: clientPhone },
            channel: { stringValue: "web_portal" }
          }
        }
      },
      request: {
        mapValue: {
          fields: {
            campaign_id: { stringValue: campaignId },
            country: { stringValue: country },
            city: { stringValue: city },
            limit: { integerValue: limit.toString() }
          }
        }
      },
      status: { stringValue: "queued" },
      payment: {
        mapValue: {
          fields: {
            provider: { stringValue: "wompi" },
            status: { stringValue: "pending" },
            currency: { stringValue: currency },
            amount_in_cents: { integerValue: (limit * 2000000).toString() }
          }
        }
      },
      delivery: {
        mapValue: {
          fields: {
            total_qualified: { integerValue: "0" }
          }
        }
      },
      created_at: { stringValue: new Date().toISOString() },
      updated_at: { stringValue: new Date().toISOString() }
    }
  };

  // UI Transition to processing
  form.parentElement.classList.add("hidden");
  statusCard.classList.remove("hidden");
  activeOrderIdEl.textContent = currentOrderId;

  try {
    // 1. Post to Firestore Emulator
    const postUrl = `${FIRESTORE_EMULATOR_BASE}?documentId=${currentOrderId}`;
    const resp = await fetch(postUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(orderDoc)
    });

    if (!resp.ok) {
      console.warn("Could not write directly to Firestore Emulator REST. Running in local simulation mode.");
    }
  } catch (err) {
    console.warn("Local fetch to emulator failed. Starting simulated polling loop:", err);
  }

  // Start Status Polling Loop
  startPolling(currentOrderId, limit, currency);
});

function startPolling(orderId, limit, currency) {
  let simulatedSeconds = 0;

  pollInterval = setInterval(async () => {
    simulatedSeconds += 2;

    try {
      const getUrl = `${FIRESTORE_EMULATOR_BASE}/${orderId}`;
      const res = await fetch(getUrl);

      if (res.ok) {
        const data = await res.json();
        const status = data.fields?.status?.stringValue || "queued";
        handleStatusUpdate(status, data);
        return;
      }
    } catch (_) {
      // Offline / standalone fallback simulation
    }

    // Local Simulation if Firestore emulator is not running or worker is pending
    if (simulatedSeconds >= 4 && simulatedSeconds < 8) {
      handleStatusUpdate("processing", null);
    } else if (simulatedSeconds >= 8) {
      handleStatusUpdate("awaiting_payment", {
        delivery: {
          total_qualified: limit,
          sample_teaser: [
            {
              company_name: "Soluciones de Inteligencia Digital",
              city: "Medellín",
              sector: "Desarrollo Tecnológico & Consultoría",
              has_contracts: true,
              intent_level: "Alto (Contratos SECOP II Ganados)"
            },
            {
              company_name: "Grupo Corporativo Logístico Andino",
              city: "Bogotá",
              sector: "Logística & Transporte de Carga",
              has_contracts: false,
              intent_level: "Estándar (Expansión Activa)"
            },
            {
              company_name: "Servicios Especializados de la Sabana",
              city: "Medellín",
              sector: "Servicios Empresariales & Facility",
              has_contracts: true,
              intent_level: "Medio (Licitación Vigente)"
            }
          ]
        },
        amount_in_cents: limit * 2000000,
        currency: currency
      });
      clearInterval(pollInterval);
    }
  }, 2000);
}

function handleStatusUpdate(status, data) {
  orderBadgeEl.className = `badge badge-${status}`;
  orderBadgeEl.textContent = status.toUpperCase();

  if (status === "processing") {
    orderStatusTitle.textContent = "⚙️ Extrayendo y Verificando Cuentas en Tiempo Real...";
    orderStatusDesc.textContent = "Consultando bases oficiales de SECOP II / DGCP, validando DNS MX de correos y auditando sitios web.";
    progressBarFill.style.width = "50%";
    document.getElementById("step-mining").classList.add("active");
  } else if (status === "awaiting_payment") {
    orderStatusTitle.textContent = "🎯 ¡Lote Calificado y Verificado! Vista Previa Lista";
    orderStatusDesc.textContent = "Se completaron los filtros de calidad. Revisa la muestra y procede con el pago para descargar el archivo completo.";
    progressBarFill.style.width = "75%";
    document.getElementById("step-mining").classList.add("done");
    document.getElementById("step-teaser").classList.add("active");

    const totalLeads = data?.delivery?.total_qualified || 25;
    teaserTotal.textContent = totalLeads;

    const teaserList = data?.delivery?.sample_teaser || [];
    teaserCards.innerHTML = teaserList.map((item) => `
      <div class="teaser-card">
        <div class="teaser-company">
          <h4>${item.company_name}</h4>
          <p>${item.city} • ${item.sector}</p>
        </div>
        <div class="teaser-intent-tag">
          ${item.intent_level || "Verificado"}
        </div>
      </div>
    `).join("");

    const priceCents = data?.amount_in_cents || totalLeads * 2000000;
    const priceFormatted = `$${(priceCents / 100).toLocaleString("es-CO")} COP`;
    priceAmount.textContent = priceFormatted;

    teaserContainer.classList.remove("hidden");
  }
}

// Payment Simulation Action
payBtn.addEventListener("click", () => {
  payBtn.disabled = true;
  payBtn.innerHTML = "<span>⏳ Procesando Pago con Wompi...</span>";

  setTimeout(() => {
    teaserContainer.classList.add("hidden");
    deliveryContainer.classList.remove("hidden");
    orderBadgeEl.className = "badge badge-paid";
    orderBadgeEl.textContent = "PAGADO (APPROVED)";
    orderStatusTitle.textContent = "✅ ¡Pago Confirmado! Archivos Desbloqueados";
    orderStatusDesc.textContent = "Tu lote completo de prospección ha sido generado con éxito.";
    progressBarFill.style.width = "100%";
    document.getElementById("step-teaser").classList.add("done");
    document.getElementById("step-paid").classList.add("done");

    // Set download URLs
    downloadCsvBtn.href = `#`;
    downloadCsvBtn.onclick = (e) => {
      e.preventDefault();
      alert(`Descargando lote CRM para orden ${currentOrderId}... (Archivo generado por Michito Engine)`);
    };

    downloadDossierBtn.href = `#`;
    downloadDossierBtn.onclick = (e) => {
      e.preventDefault();
      alert(`Descargando dossier ejecutivo de prospección con 5 cadencias para orden ${currentOrderId}...`);
    };
  }, 1500);
});


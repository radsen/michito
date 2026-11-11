/**
 * Michito Web Client Portal (B2B Lead Intelligence Order Engine)
 * Directly connects to FastAPI backend on Port 8000 + PostgreSQL
 * Served via Firebase Hosting Emulator on Port 5000
 */

const API_BASE_URL = "http://localhost:8000/api/v1/orders";

const form = document.getElementById("order-form");
const submitBtn = document.getElementById("submit-btn");
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
let currentOrderAmount = null;
let currentOrderCurrency = null;

function calculateClientPrice(totalLeads, tier = 2, currency = "COP") {
  const baseRates = currency === "DOP"
    ? { 1: 10000, 2: 35000, 3: 75000 }
    : { 1: 500000, 2: 3000000, 3: 6500000 };
  const unit = baseRates[tier] || baseRates[2];

  let discount = 0.0;
  if (totalLeads >= 1000) discount = 0.42;
  else if (totalLeads >= 500) discount = 0.35;
  else if (totalLeads >= 250) discount = 0.28;
  else if (totalLeads >= 100) discount = 0.20;
  else if (totalLeads >= 50) discount = 0.12;
  else if (totalLeads >= 25) discount = 0.06;

  const discountedUnit = Math.floor(unit * (1.0 - discount));
  return totalLeads * discountedUnit;
}

// Dynamic City switch based on country selection
const campaignSelectEl = document.getElementById("campaign-select");
const targetCityEl = document.getElementById("target-city");
if (campaignSelectEl && targetCityEl) {
  campaignSelectEl.addEventListener("change", () => {
    const opt = campaignSelectEl.options[campaignSelectEl.selectedIndex];
    if (opt.dataset.country === "DO") {
      if (targetCityEl.value === "Medellín" || !targetCityEl.value) {
        targetCityEl.value = "Santo Domingo";
      }
    } else {
      if (targetCityEl.value === "Santo Domingo") {
        targetCityEl.value = "Medellín";
      }
    }
  });
}

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
  const tier = parseInt(document.getElementById("lead-tier")?.value || "2", 10);
  const clientName = document.getElementById("client-name").value.trim();
  const clientEmail = document.getElementById("client-email").value.trim();
  const clientPhone = document.getElementById("client-phone").value.trim();

  const orderPayload = {
    client: {
      name: clientName,
      email: clientEmail,
      phone: clientPhone,
      channel: "web_portal",
      referral_partner: "direct"
    },
    request: {
      campaign_id: campaignId,
      country: country,
      city: city,
      limit: limit,
      tier: tier
    }
  };

  // UI Transition to processing
  form.parentElement.classList.add("hidden");
  statusCard.classList.remove("hidden");
  statusCard.scrollIntoView({ behavior: "smooth" });
  activeOrderIdEl.textContent = "Connecting to API...";

  try {
    const resp = await fetch(API_BASE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(orderPayload)
    });

    if (!resp.ok) {
      const errText = await resp.text();
      throw new Error(`API Error (${resp.status}): ${errText}`);
    }

    const data = await resp.json();
    currentOrderId = data.order_id;
    activeOrderIdEl.textContent = currentOrderId;

    // Start Live Status Polling
    startPolling(currentOrderId);

  } catch (err) {
    console.error("Order submission failed:", err);
    orderStatusTitle.textContent = "⚠️ Error al enviar la orden al backend";
    orderStatusDesc.textContent = `Asegúrate de que FastAPI esté corriendo en http://localhost:8000. Detalle: ${err.message}`;
    orderBadgeEl.className = "badge badge-queued";
    orderBadgeEl.textContent = "ERROR";
  }
});

function startPolling(orderId) {
  if (pollInterval) clearInterval(pollInterval);

  pollInterval = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/${orderId}`);
      if (!res.ok) return;

      const order = await res.json();
      const status = order.status || "queued";
      handleStatusUpdate(status, order);

      if (status === "awaiting_payment" || status === "paid" || status === "completed") {
        clearInterval(pollInterval);
      }
    } catch (err) {
      console.warn("Polling connection error:", err);
    }
  }, 2000);
}

function handleStatusUpdate(status, order) {
  orderBadgeEl.className = `badge badge-${status}`;
  orderBadgeEl.textContent = status.toUpperCase();

  if (status === "queued") {
    orderStatusTitle.textContent = "⏳ Orden en Cola de Procesamiento...";
    orderStatusDesc.textContent = "La solicitud ha sido registrada en PostgreSQL. El Worker Daemon la tomará en breve.";
    progressBarFill.style.width = "25%";
  } else if (status === "processing") {
    orderStatusTitle.textContent = "⚙️ Calificando y Verificando Cuentas en Tiempo Real...";
    orderStatusDesc.textContent = "Procesando registros mercantiles, auditando sitios web y validando respuesta técnica de buzones corporativos.";
    progressBarFill.style.width = "50%";
    document.getElementById("step-mining").classList.add("active");
  } else if (status === "awaiting_payment") {
    orderStatusTitle.textContent = "🎯 ¡Lote Calificado y Verificado! Vista Previa Lista";
    orderStatusDesc.textContent = "Filtros de calidad completados. Revisa la muestra y confirma tu orden para desbloquear el lote completo.";
    progressBarFill.style.width = "75%";
    document.getElementById("step-mining").classList.add("done");
    document.getElementById("step-teaser").classList.add("active");

    const totalLeads = order?.delivery?.total_qualified || order?.total_qualified || order?.request?.limit || order?.limit || 25;
    teaserTotal.textContent = totalLeads;

    const teaserList = order?.delivery?.sample_teaser || [];
    if (teaserList.length > 0) {
      teaserCards.innerHTML = teaserList.map((item) => `
        <div class="teaser-card">
          <div class="teaser-company">
            <h4>${item.company_name}</h4>
            <p>${item.city || "Ciudad"} • ${item.sector || "Sector B2B"}</p>
            <div style="font-size: 0.8rem; color: #38bdf8; margin-top: 4px;">
              ${item.decision_maker_name || "Directivo Clave"} • ${item.decision_maker_role || item.decision_maker_title || "Tomador de Decisión"}
            </div>
            <div style="font-size: 0.75rem; color: #34d399; margin-top: 2px;">
              ✉️ ${item.email || "c***@empresa.com"} • 📞 ${item.phone || "+57 3•• ••• ••••"}
            </div>
          </div>
          <div class="teaser-intent-tag">
            ${item.intent_trigger || item.intent_level || "Contacto Institucional Verificado"}
          </div>
        </div>
      `).join("");
    } else {
      teaserCards.innerHTML = `
        <div class="teaser-card">
          <div class="teaser-company">
            <h4>${order.request?.limit} Cuentas B2B Calificadas</h4>
            <p>${order.request?.city} • Muestra lista para descarga</p>
          </div>
          <div class="teaser-intent-tag">Contacto Verificado</div>
        </div>
      `;
    }

    const currency = order?.payment?.currency || "COP";
    const tier = order?.request?.tier || 2;
    const priceCents = order?.payment?.amount_in_cents || calculateClientPrice(totalLeads, tier, currency);
    currentOrderAmount = priceCents;
    currentOrderCurrency = currency;
    const formattedPrice = (priceCents / 100).toLocaleString(currency === "DOP" ? "es-DO" : "es-CO");
    priceAmount.textContent = `${currency === "DOP" ? "RD$" : "$"}${formattedPrice} ${currency}`;

    teaserContainer.classList.remove("hidden");
  } else if (status === "paid" || status === "completed") {
    showPaidDeliveryUI(order);
  }
}

function showPaidDeliveryUI(order) {
  teaserContainer.classList.add("hidden");
  deliveryContainer.classList.remove("hidden");
  orderBadgeEl.className = "badge badge-paid";
  orderBadgeEl.textContent = "PAGADO (APPROVED)";
  orderStatusTitle.textContent = "✅ ¡Pago Confirmado! Archivos Desbloqueados";
  orderStatusDesc.textContent = "Tu lote completo de prospección ha sido generado con éxito y está listo para descarga.";
  progressBarFill.style.width = "100%";
  document.getElementById("step-teaser").classList.add("done");
  document.getElementById("step-paid").classList.add("done");

  const orderId = order.order_id || currentOrderId;
  downloadCsvBtn.href = `${API_BASE_URL}/${orderId}/download/csv`;
  downloadDossierBtn.href = `${API_BASE_URL}/${orderId}/download/dossier`;
}

async function generateWompiSignature(reference, amount, currency, secret) {
  const data = reference.toString() + amount.toString() + currency.toString() + secret;
  const encoder = new TextEncoder();
  const dataBuffer = encoder.encode(data);
  const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

// Payment Action (Opens Wompi Widget)
payBtn.addEventListener("click", async () => {
  payBtn.disabled = true;
  payBtn.innerHTML = "<span>⏳ Abriendo Wompi...</span>";

  try {
    const WOMPI_PUBLIC_KEY = 'pub_test_IcBzwUvqUDy85sD7i3snlgxvMLj4A1eL';
    const WOMPI_INTEGRITY_SECRET = 'test_integrity_r5SIpk6PnYywRaCxQlOXgySj28wNNlmj';
    
    const signature = await generateWompiSignature(
      currentOrderId,
      currentOrderAmount,
      currentOrderCurrency,
      WOMPI_INTEGRITY_SECRET
    );

    const checkout = new WidgetCheckout({
      currency: currentOrderCurrency,
      amountInCents: currentOrderAmount,
      reference: currentOrderId,
      publicKey: WOMPI_PUBLIC_KEY,
      signature: { integrity: signature }
    });

    checkout.open(function(result) {
      const transaction = result.transaction;
      if (transaction && transaction.status === 'APPROVED') {
        payBtn.innerHTML = "<span>✅ Pago Aprobado. Verificando...</span>";
        // Start polling again to wait for backend webhook
        pollForPayment(currentOrderId);
      } else {
        payBtn.disabled = false;
        payBtn.innerHTML = "<span>💳 Pagar Seguro con Wompi (PSE / Tarjeta)</span>";
      }
    });

  } catch (err) {
    alert(`Error procesando pago: ${err.message}`);
    payBtn.disabled = false;
    payBtn.innerHTML = "<span>💳 Pagar Seguro con Wompi (PSE / Tarjeta)</span>";
  }
});

// ------------------------------------------------------------------------------
// Dual Language Localization (es_CO Default, en_US Toggle)
// ------------------------------------------------------------------------------
const TRANSLATIONS = {
  es: {
    statusText: "Motor Activo",
    navCta: "🚀 Configurar Lote",
    heroTitle: 'Inteligencia Comercial B2B con <span class="gradient-text">Señales Reales de Actividad y Crecimiento</span>.',
    heroSubtitle: 'Dejamos atrás las listas estáticas y obsoletas. Michito procesa registros institucionales, audita presencia web operativa y valida la entregabilidad de cada buzón corporativo en tiempo real para conectar a tu equipo comercial con empresas en momento de compra.',
    heroCtaPrimary: "⚡ Configurar Lote de Prospección",
    heroCtaSecondary: "Ver Cómo Funciona la Metodología",
    formSubmit: "⚡ Iniciar Calificación Asíncrona",
  },
  en: {
    statusText: "Engine Active",
    navCta: "🚀 Configure Batch",
    heroTitle: 'B2B Sales Intelligence with <span class="gradient-text">Real Activity & Growth Triggers</span>.',
    heroSubtitle: 'Leave obsolete static lists behind. Michito scans statutory corporate registries, audits operational web presence, and verifies physical mailbox deliverability in real-time to connect your sales team with ready-to-buy accounts.',
    heroCtaPrimary: "⚡ Configure Prospecting Batch",
    heroCtaSecondary: "Explore Methodology",
    formSubmit: "⚡ Launch Asynchronous Extraction",
  }
};

let currentLang = localStorage.getItem("michito_lang") || "es";

function applyLanguage(lang) {
  currentLang = lang;
  localStorage.setItem("michito_lang", lang);

  const t = TRANSLATIONS[lang] || TRANSLATIONS.es;

  const btnEs = document.getElementById("btn-lang-es");
  const btnEn = document.getElementById("btn-lang-en");
  if (btnEs && btnEn) {
    if (lang === "es") {
      btnEs.classList.add("active");
      btnEn.classList.remove("active");
    } else {
      btnEn.classList.add("active");
      btnEs.classList.remove("active");
    }
  }

  const navStatus = document.getElementById("nav-status-text");
  if (navStatus) navStatus.textContent = t.statusText;

  const navCta = document.getElementById("nav-cta-btn");
  if (navCta) navCta.textContent = t.navCta;

  const heroTitle = document.querySelector(".hero-title");
  if (heroTitle) heroTitle.innerHTML = t.heroTitle;

  const heroSubtitle = document.querySelector(".hero-subtitle");
  if (heroSubtitle) heroSubtitle.textContent = t.heroSubtitle;

  const heroCta1 = document.querySelector(".btn-hero-primary");
  if (heroCta1) heroCta1.textContent = t.heroCtaPrimary;

  const heroCta2 = document.querySelector(".btn-hero-secondary");
  if (heroCta2) heroCta2.textContent = t.heroCtaSecondary;

  const submitBtnText = document.querySelector("#submit-btn .btn-text");
  if (submitBtnText) submitBtnText.textContent = t.formSubmit;
}

const btnEs = document.getElementById("btn-lang-es");
const btnEn = document.getElementById("btn-lang-en");
if (btnEs) btnEs.addEventListener("click", () => applyLanguage("es"));
if (btnEn) btnEn.addEventListener("click", () => applyLanguage("en"));

// Apply saved language preference on load
document.addEventListener("DOMContentLoaded", () => {
  applyLanguage(currentLang);
});

function pollForPayment(orderId) {
  let attempts = 0;
  const paymentInterval = setInterval(async () => {
    attempts++;
    try {
      const res = await fetch(`${API_BASE_URL}/${orderId}`);
      if (!res.ok) return;

      const order = await res.json();
      if (order.status === "paid" || order.status === "completed") {
        clearInterval(paymentInterval);
        showPaidDeliveryUI(order);
      } else if (attempts > 30) {
        clearInterval(paymentInterval);
        alert("El pago fue aprobado, pero el sistema está tardando en procesarlo. Por favor, recarga la página en unos minutos.");
        payBtn.disabled = false;
        payBtn.innerHTML = "<span>💳 Pagar Seguro con Wompi (PSE / Tarjeta)</span>";
      }
    } catch (err) {
      console.warn("Polling payment error:", err);
    }
  }, 2000);
}

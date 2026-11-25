# Michito B2B Engine — Staging Human QA Test Scenarios

This document serves as the master checklist and guide for conducting human end-to-end evaluations of the **Michito Intent Engine** on the Staging environment.

---

## 1. Test Environment & Access Details

| Resource | URL / Configuration |
| :--- | :--- |
| **Batch Request Stepper (Staging)** | `https://michito-web-limgi3puaq-uc.a.run.app/solicitar` |
| **Landing Web Client (Staging)** | `https://michito-web-limgi3puaq-uc.a.run.app` |
| **Backend API (Staging)** | `https://michito-api-limgi3puaq-uc.a.run.app` |
| **API Health Check** | `https://michito-api-limgi3puaq-uc.a.run.app/health` |
| **Order Tracker Pattern** | `https://michito-web-limgi3puaq-uc.a.run.app/rastrear?order_id=<ORDER_ID>` |

---

## 2. Core Quality Gates to Verify in Every Scenario

When executing any test scenario, verify these 5 foundational behaviors:
1. **AI Discovery Button**: Clicking *"Descubrir con IA"* rotates the loading spinner continuously without freezing.
2. **Transparent Post-Audit Pricing**:
   - Step 1 button displays *"Configurar Solicitud de Auditoría (N cuentas)"*.
   - Subtitle pill shows transparent reference: *"Tarifa desde $X COP / cuenta • $0 anticipo"*.
   - Step 2 button displays *"Solicitar Auditoría y Cotización Exacta"*.
   - Step 2 recap displays *"Inversión: Cotización calculada post-auditoría sobre cuentas verificadas ($0 anticipo)"*.
3. **Async Handoff State**:
   - Once submitted, the screen presents the **Async Handoff Card**: *"¡Solicitud Recibida! Tu auditoría está en marcha... No necesitas quedarte esperando en esta página. Te notificaremos por correo y WhatsApp."*
4. **Unpaid Review Email Security (Zero File Leakage)**:
   - When the batch finishes, the notification email arrives with the adjusted fair quote.
   - **CRITICAL**: The review email must contain **0 file attachments** (no `.xlsx`, `.csv`, `.pdf` attached prior to payment).
   - Email text must read *"nuestros filtros de validación"* (no *"100%"* phrasing).
5. **Paid Delivery Email Links**:
   - Upon payment (or simulating payment in test), the delivery email download buttons point to `https://michito-web-limgi3puaq-uc.a.run.app/api/v1/orders/.../download/...` (never `localhost:8000`).
   - The delivery email contains the 3 pre-compiled attachments.

---

## 3. Human Test Scenarios Matrix

---

### PART A: Client Acquisition Scenarios (Vendor Seeking Buyers)

#### Scenario 1: High-Volume Base Directory (1,000 Leads • Tier 1 • Bogotá) 🇨🇴
* **Purpose**: Test maximum volume ceiling (1,000 leads), cold harvest execution, and fair-billing downward adjustment.
* **Flow Setup**:
  1. Direction: **"Quiero Vender (Captar Clientes)"**
  2. Search Query (AI Input): `Empresas de tecnología, desarrollo de software y servicios cloud en Bogotá`
  3. Desired Volume: **1.000+**
  4. Tier: **Tier 1 (Directorio Verificado)**
  5. Territory: **Bogotá, Colombia 🇨🇴**
  6. Contact Data:
     - Name: `Andrés Solano`
     - Email: `andres@chiketto.com`
     - Phone: `+573001234567`
* **Execution & Verification**:
  - [ ] AI discovery recognizes CIIU `6201` / `6202` (Tecnología y Software).
  - [ ] Submits with 1,000 requested leads without 400 Bad Request limit error.
  - [ ] Async handoff card appears with clear reassurance.
  - [ ] Background Cloud Run worker completes harvest.
  - [ ] Quote email arrives with adjusted Fair Price for verified accounts (e.g. 96 verified).
  - [ ] Email has **0 attachments**.

---

#### Scenario 2: Mid-Volume Decision-Makers (500 Leads • Tier 2 • Medellín) 🇨🇴
* **Purpose**: Test mid-volume harvesting with verified mobile numbers and active MX sockets.
* **Flow Setup**:
  1. Direction: **"Quiero Vender (Captar Clientes)"**
  2. Search Query (AI Input): `Empresas de manufactura textil, confección y calzado en Medellín`
  3. Desired Volume: **500**
  4. Tier: **Tier 2 (Decisores + Móvil)**
  5. Target Roles: `Director de Operaciones`, `Gerente General`, `Jefe de Compras`
  6. Territory: **Medellín, Colombia 🇨🇴**
  7. Contact Data: Your corporate email & mobile phone.
* **Execution & Verification**:
  - [ ] Preset or AI identifies relevant textile sectors.
  - [ ] Live quality radar verifies MX deliverability for decision-maker inboxes.
  - [ ] Tracker displays masked sample teaser table (names/emails partially masked).
  - [ ] Approval link can be copied and shared.

---

#### Scenario 3: Deep Financial & Solvency Audit (100 Leads • Tier 3 • Cali/Barranquilla) 🇨🇴
* **Purpose**: Test Tier 3 deep underwriting, commercial risk rating, and executive dossier synthesis.
* **Flow Setup**:
  1. Direction: **"Quiero Vender (Captar Clientes)"**
  2. Search Query (AI Input): `Empresas distribuidoras de alimentos al por mayor e insumos para restaurantes`
  3. Desired Volume: **100**
  4. Tier: **Tier 3 (Auditoría Financiera y Solvencia Completa)**
  5. Territory: **Cali** (50) y **Barranquilla** (50), **Colombia 🇨🇴**
  6. Contact Data: Your corporate email & mobile phone.
* **Execution & Verification**:
  - [ ] System allocates cuota between Cali and Barranquilla.
  - [ ] Background worker processes statutory solvency checks.
  - [ ] Sample teaser demonstrates financial indicators (EBITDA, solvency classification).
  - [ ] Payment unlock generates Executive Dossier (`.PDF` and `.MD`) with commercial talking points and underwriting recommendations.

---

### PART B: Sourcing & Supplier Discovery Scenarios (Buyer Seeking Vendors)

#### Scenario 4: Niche Local Providers (50 Providers • Tier 2 • Bogotá) 🇨🇴
* **Purpose**: Verify supplier discovery directionality (Client-to-Vendors) and niche procurement extraction.
* **Flow Setup**:
  1. Direction: **"Buscar Proveedores / Suplidores (Reverse RFQ)"**
  2. Search Query (AI Input): `Fabricantes de empaques biodegradables, cajas de cartón corrugado y bolsas compostables`
  3. Desired Volume: **50**
  4. Tier: **Tier 2**
  5. Territory: **Bogotá, Colombia 🇨🇴**
  6. Specifications / RFQ: `Requerimos proveedores con capacidad de entrega semanal de 10,000 unidades.`
* **Execution & Verification**:
  - [ ] UI highlights green procurement badges for supplier directionality.
  - [ ] RFQ specifications textarea is captured in order payload.
  - [ ] Extracted companies correspond to manufacturing / packaging suppliers.
  - [ ] Teasers display institutional procurement contacts.

---

#### Scenario 5: Industrial Technical Contractors (150 Providers • Tier 2 • Medellín) 🇨🇴
* **Purpose**: Test mid-volume vendor search for industrial technical services.
* **Flow Setup**:
  1. Direction: **"Buscar Proveedores / Suplidores (Reverse RFQ)"**
  2. Search Query: `Talleres industriales de mecanizado CNC, corte láser y soldadura certificada`
  3. Desired Volume: **150**
  4. Tier: **Tier 2**
  5. Territory: **Medellín, Colombia 🇨🇴**
* **Execution & Verification**:
  - [ ] System extracts precision metalworking and industrial engineering companies.
  - [ ] Validates active websites and verified corporate phone numbers.
  - [ ] Review email provides tailored supplier quote.

---

#### Scenario 6: High-Volume National Suppliers (500 Providers • Tier 1 • Multi-City) 🇨🇴
* **Purpose**: Test high-volume supplier catalog search across multiple Colombian logistics hubs.
* **Flow Setup**:
  1. Direction: **"Buscar Proveedores / Suplidores (Reverse RFQ)"**
  2. Search Query: `Distribuidores mayoristas de insumos médicos, quirúrgicos y material descartable para clínicas`
  3. Desired Volume: **500**
  4. Tier: **Tier 1**
  5. Multi-City Quota: **Bogotá (250)**, **Medellín (150)**, **Cali (100)**
* **Execution & Verification**:
  - [ ] Multi-city quota allocator divides volume correctly.
  - [ ] Harvester aggregates vendors across all 3 territories into a unified database.
  - [ ] Export files contain city breakdown and verified tax IDs.

---

### PART C: Cross-Border LatAm Expansion Scenarios

#### Scenario 7: Dominican Republic Official Directory (50 Leads • Santo Domingo) 🇩🇴
* **Purpose**: Test DGCP / DGII public procurement and RNC directory integration.
* **Flow Setup**:
  1. Territory: **República Dominicana 🇩🇴**
  2. City: **Santo Domingo**
  3. Search Query: `Empresas constructoras y contratistas de obras civiles en Santo Domingo`
  4. Desired Volume: **50**
  5. Currency: **DOP** (or USD)
* **Execution & Verification**:
  - [ ] Badges show *"✓ RNC Vigente en DGII"*.
  - [ ] Pricing automatically displays in DOP with regional pricing catalog rate.
  - [ ] Previews reflect authentic Dominican commercial entities.

---

#### Scenario 8: Ecuador Statutory Registry (50 Leads • Quito/Guayaquil) 🇪🇨
* **Purpose**: Test SRI RUC validation and SERCOP public contracts engine.
* **Flow Setup**:
  1. Territory: **Ecuador 🇪🇨**
  2. City: **Quito** or **Guayaquil**
  3. Search Query: `Empresas de seguridad privada y vigilancia física en Guayaquil`
  4. Desired Volume: **50**
  5. Currency: **USD**
* **Execution & Verification**:
  - [ ] Badges show *"✓ RUC Vigente en SRI"*.
  - [ ] Currency converts to USD correctly.
  - [ ] Extracted leads display verified RUC identifiers.

---

#### Scenario 9: Chile Corporate Directory (50 Leads • Santiago) 🇨🇱
* **Purpose**: Test SII RUT resolution and Mercado Público contractor indexing.
* **Flow Setup**:
  1. Territory: **Chile 🇨🇱**
  2. City: **Santiago**
  3. Search Query: `Empresas de servicios logísticos y transporte de carga en Santiago`
  4. Desired Volume: **50**
  5. Currency: **USD**
* **Execution & Verification**:
  - [ ] Badges show *"✓ RUT Vigente"*.
  - [ ] Correctly identifies Chilean corporate entities.

---

### PART D: Form Validation & Security Edge Cases

#### Scenario 10: Client Contact Validation Testing
* **Purpose**: Verify that incomplete or malformed contact data is blocked with inline alerts.
* **Test Cases**:
  1. **Name < 2 Characters**: Enter `"A"`, click submit.
     - [ ] Expected: Blocked with red border and message: *"Por favor ingresa tu nombre o el de tu empresa (mínimo 2 caracteres)."*
  2. **Invalid Email Syntax**: Enter `"not-an-email"`, click submit.
     - [ ] Expected: Blocked with red border and message: *"Por favor ingresa un correo electrónico corporativo válido."*
  3. **Invalid Phone Syntax**: Enter `"1234"`, click submit.
     - [ ] Expected: Blocked with message: *"El número de celular o WhatsApp debe contener al menos 7 dígitos."*
  4. **Native Autofill**: Click into Name, Email, Phone.
     - [ ] Expected: Browser offers 1-tap autofill (`name`, `email`, `tel`).
  5. **Empty Storage on First Load**: Open an Incognito window.
     - [ ] Expected: Name, email, and phone inputs start completely empty (`""`).

---

## 4. Human Testing Tracking Scorecard

Print or copy this scorecard to record test results during evaluation:

| # | Scenario Description | Target | Tier | Status (Pass/Fail) | Verified Yield | Notes & Observations |
|---|---|---|---|---|---|---|
| **01** | High-Volume Base Directory (Bogotá) 🇨🇴 | 1,000 | T1 | | | |
| **02** | Decision-Makers (Medellín) 🇨🇴 | 500 | T2 | | | |
| **03** | Deep Financial Audit (Cali / B/quilla) 🇨🇴 | 100 | T3 | | | |
| **04** | Biodegradable Packaging Suppliers 🇨🇴 | 50 | T2 | | | |
| **05** | Industrial CNC Contractors 🇨🇴 | 150 | T2 | | | |
| **06** | National Medical Suppliers 🇨🇴 | 500 | T1 | | | |
| **07** | Civil Contractors (Santo Domingo) 🇩🇴 | 50 | T2 | | | |
| **08** | Security Providers (Guayaquil) 🇪🇨 | 50 | T2 | | | |
| **09** | Logistics Operators (Santiago) 🇨🇱 | 50 | T2 | | | |
| **10** | Contact Form Validations & Security | N/A | N/A | | | |

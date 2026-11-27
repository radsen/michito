"""
Website Content Auditor & Quality Gate
Verifies that a candidate company website is an active, legitimate marketing portal,
detecting and rejecting domain parking pages, cPanel placeholders, webmail login portals,
and unrelated holding/vendor domains.
"""

import re
import ssl
import urllib.parse
import urllib.request
from typing import Tuple, Dict, Any, Optional

PARKING_SIGNATURES = [
    r"future home of something",
    r"under construction",
    r"p[aá]gina en construcci[oó]n",
    r"sitio en construcci[oó]n",
    r"este servidor no es el sitio",
    r"no es el sitio que buscas",
    r"cpanel",
    r"webmail login",
    r"default web site page",
    r"domain for sale",
    r"sedoparking",
    r"godaddy",
    r"suspended domain",
    r"account suspended",
    r"site under development",
    r"apache2 ubuntu default page",
    r"welcome to nginx",
]


class WebsiteAuditor:
    """
    Audits candidate URLs to ensure high data fidelity for B2B intelligence dossiers.
    """

    def __init__(self, timeout: float = 2.0):
        self.timeout = timeout
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        self._cache: dict = {}
        self._contacts_cache: dict = {}
        self.last_extracted_contacts: Dict[str, Any] = {}

    @staticmethod
    def extract_contacts_from_html(html: str, target_domain: str = "") -> Dict[str, Any]:
        """
        Extracts corporate emails, WhatsApp links, and direct telephone numbers from raw HTML.
        Filters out static asset files, third-party libraries, and boilerplate placeholders.
        """
        contacts: Dict[str, Any] = {
            "emails": [],
            "phones": [],
            "whatsapp": "",
            "primary_email": None,
            "primary_phone": None,
        }
        if not html:
            return contacts

        # 1. WhatsApp extraction (highest intent)
        wa_match = re.search(r"(?:wa\.me/|api\.whatsapp\.com/send\?phone=|\+?whatsapp[^\d]{0,5})([0-9]{10,14})", html, flags=re.IGNORECASE)
        if not wa_match:
            wa_href = re.search(r'href=["\'](?:https?://)?wa\.me/([0-9]+)', html, flags=re.IGNORECASE)
            if wa_href:
                wa_match = wa_href

        if wa_match:
            wa_num = wa_match.group(1).strip()
            if len(wa_num) >= 10:
                contacts["whatsapp"] = f"+{wa_num}" if not wa_num.startswith("+") else wa_num
                contacts["phones"].append(contacts["whatsapp"])
                contacts["primary_phone"] = contacts["whatsapp"]

        # 2. Email extraction
        raw_emails = re.findall(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b", html)
        invalid_email_tokens = (
            "example.com", "domain.com", "email.com", "yourname", "test.com",
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js",
            "wixpress", "sentry", "cloudflare", "bootstrap", "schema.org", "w3.org",
            "wordpress", "shopify", "elementor", "google", "apple", "facebook"
        )
        seen_emails = set()
        for em in raw_emails:
            em_clean = em.lower().strip().rstrip(".")
            if any(inv in em_clean for inv in invalid_email_tokens):
                continue
            if em_clean.startswith(("u00", "xxx", "user@", "name@", "info@domain")):
                continue
            if em_clean not in seen_emails:
                seen_emails.add(em_clean)
                contacts["emails"].append(em_clean)

        # Prioritize matching domain emails if available
        if target_domain:
            t_dom = target_domain.lower().replace("www.", "")
            domain_matched = [e for e in contacts["emails"] if t_dom in e]
            if domain_matched:
                contacts["primary_email"] = domain_matched[0]

        if not contacts["primary_email"] and contacts["emails"]:
            pref_prefixes = ("contacto@", "ventas@", "comercial@", "gerencia@", "info@", "atencionalcliente@")
            pref = [e for e in contacts["emails"] if any(e.startswith(p) for p in pref_prefixes)]
            contacts["primary_email"] = pref[0] if pref else contacts["emails"][0]

        # 3. Direct Phone Extraction
        tel_links = re.findall(r'href=["\']tel:([+0-9\s.-]+)["\']', html, flags=re.IGNORECASE)
        for t in tel_links:
            clean_t = re.sub(r"[^\d+]", "", t)
            if len(clean_t) >= 7 and clean_t not in contacts["phones"]:
                contacts["phones"].append(clean_t)

        # Regex for Colombia mobile numbers (+57 3XX XXX XXXX or 3XX XXX XXXX)
        co_mobiles = re.findall(r"(?:^|[^\d])(?:\+?57[\s.-]?)?(3[0-2]\d[\s.-]?\d{3}[\s.-]?\d{4})(?:[^\d]|$)", html)
        for m in co_mobiles:
            digits = re.sub(r"\D", "", m)
            if len(digits) == 10 and digits.startswith("3"):
                formatted = f"+57 {digits}"
                if formatted not in contacts["phones"]:
                    contacts["phones"].append(formatted)

        if not contacts["primary_phone"] and contacts["phones"]:
            contacts["primary_phone"] = contacts["phones"][0]

        return contacts

    def check_domain_alignment(self, domain: str, company_name: str) -> bool:
        """
        Heuristic check: ensures the domain name isn't an obviously unrelated third party
        (e.g., prevents Robotic International being assigned archivosdelestado.com).
        """
        clean_company = re.sub(r"[^a-zA-Z0-9]", "", company_name.lower())
        clean_domain = re.sub(r"[^a-zA-Z0-9]", "", domain.split(".")[0].lower())

        # Common company name abbreviations & words
        words = [w for w in re.split(r"\W+", company_name.lower()) if len(w) >= 3 and w not in ("sas", "ltda", "colombia", "internacional", "grupo")]
        
        # If any significant word from company name is in domain, or domain in company
        if any(w in clean_domain for w in words):
            return True
        if clean_domain in clean_company:
            return True
        # If domain acronym matches
        acronym = "".join(w[0] for w in words if w)
        if len(acronym) >= 3 and acronym in clean_domain:
            return True

        return False

    def audit(self, raw_url: str, company_name: str) -> Tuple[bool, str, str]:
        """
        Returns (is_active_marketing_site, display_url, status_notes)
        """
        if not raw_url or raw_url.strip() in ("No Provisto", "Por verificar", "0", ""):
            return False, "Presencia en LinkedIn Corporativo", "Sin portal web registrado"

        cache_key = f"{raw_url.strip().lower()}:{company_name.lower().strip()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        url = raw_url.strip()
        if not url.startswith("http"):
            url = f"https://{url}"

        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.replace("www.", "")

        # Check domain alignment with company name
        if not self.check_domain_alignment(domain, company_name):
            # Domain does not match company (e.g. outsourced accountant or holding email)
            res = (False, "Presencia en LinkedIn Corporativo", f"Dominio ({domain}) no alineado con la razón social")
            self._cache[cache_key] = res
            return res

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
        }

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=self.timeout) as resp:
                final_url = resp.geturl()
                final_parsed = urllib.parse.urlparse(final_url)
                final_domain = final_parsed.netloc.replace("www.", "")

                # If redirected to a third party or different company domain
                if not self.check_domain_alignment(final_domain, company_name):
                    res = (False, "Presencia en LinkedIn Corporativo", f"Redirige a dominio no alineado ({final_domain})")
                    self._cache[cache_key] = res
                    return res

                html_bytes = resp.read(35000)
                html = html_bytes.decode("utf-8", errors="ignore").lower()

                # Extract corporate contacts from HTML stream
                contacts = self.extract_contacts_from_html(html, target_domain=final_domain)
                self.last_extracted_contacts = contacts
                self._contacts_cache[cache_key] = contacts

                # Check redirect to login/webmail portal
                if any(p in final_url.lower() for p in ("/login", "/webmail", ":2096", ":2083", "/cpanel")):
                    res = (False, "Presencia en LinkedIn Corporativo", "Redirige a portal de login/intranet privada")
                    self._cache[cache_key] = res
                    return res

                # Check title and body for parking signatures
                for sig in PARKING_SIGNATURES:
                    if re.search(sig, html):
                        res = (False, "Presencia en LinkedIn Corporativo", f"Dominio en construcción o parqueado ({sig})")
                        self._cache[cache_key] = res
                        return res

                # Extract title for audit confirmation
                title_match = re.search(r"<title>(.*?)</title>", html)
                title = title_match.group(1).strip() if title_match else "Portal Web Activo"
                title_clean = re.sub(r"\s+", " ", title)[:45]

                res = (True, final_url, f"Portal Activo Verificado ({title_clean})")
                self._cache[cache_key] = res
                return res

        except Exception as e:
            # Strict policy: If connection fails or domain does not resolve, mark as inaccessible.
            # NEVER mark dead, fake, or unreachable domains as verified.
            res = (False, "Presencia en LinkedIn Corporativo", f"Portal inaccesible ({str(e)[:35]})")
            self._cache[cache_key] = res
            return res

    def audit_and_extract(self, raw_url: str, company_name: str) -> Tuple[bool, str, str, Dict[str, Any]]:
        """
        Audits candidate website and returns validation state along with extracted contacts (emails, WhatsApp, phones).
        """
        is_ok, url, note = self.audit(raw_url, company_name)
        cache_key = f"{(raw_url or '').strip().lower()}:{(company_name or '').lower().strip()}"
        contacts = self._contacts_cache.get(cache_key) or self.last_extracted_contacts or {
            "emails": [], "phones": [], "whatsapp": "", "primary_email": None, "primary_phone": None
        }
        return is_ok, url, note, contacts


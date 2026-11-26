"""
Michito AI Agent Suite — Semantic DANE/UN ISIC Rev. 4 Classification Engine.
Combines ultra-fast local deterministic regex and sub-millisecond BM25 token matching
with batch Gemini 2.5 Flash classification fallback for ambiguous corporate entities.
Zero external blockers, strict 2.5s client timeouts, and comprehensive financial observability.
"""

from collections import defaultdict
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from src.domain.taxonomy.isic_index import get_isic_index, IsicEntry
from src.domain.value_objects.ciiu_code import CiiuCode

logger = logging.getLogger(__name__)


class SemanticClassificationService:
    """
    Two-stage semantic classifier for Colombian and LatAm corporate entities.
    Stage 1: Deterministic regex and sub-millisecond BM25 local indexing (< 1ms, $0 cost).
    Stage 2: Batched Gemini 2.5 Flash inference for low-confidence corporate entities (< 2.5s timeout).
    """

    def __init__(self, api_key: Optional[str] = None):
        self.isic_index = get_isic_index()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")

    def classify_company(
        self,
        name: str,
        email: str = "",
        raw_desc: str = "",
    ) -> Tuple[CiiuCode, float, str]:
        """
        Classifies a single corporate entity using local regex and BM25 index.
        Returns:
            Tuple of (CiiuCode, confidence_score [0.0 - 1.0], source ['regex', 'bm25', 'fallback'])
        """
        text = f"{name} {email} {raw_desc}".strip()
        lower = text.lower()

        # 1. Deterministic high-precision regex matching
        regex_patterns = [
            (r"colegio|escuela|educa|ensenanza|liceo|gimnasio|academ|universidad|institucion educativa|bachillerato|preescolar|carnet", "8530"),
            (r"alimento|abarrote|viveres|granos|lacteo|carnic|horeca|frutas|conservas|gastronom|comida", "4631"),
            (r"combustible|gasolina|diesel|acpm|lubricante|hidrocarburo|petroleo|petroquimic", "4661"),
            (r"cemento|concreto|acero|ferreteria industrial|materiales de construccion|ladrillo|prefabricados", "4663"),
            (r"constructor|construccion|edificac|obras civiles", "4111"),
            (r"bodega industrial|cedi|almacenamiento y deposito", "5210"),
            (r"cobranza|gestion de cartera|factoring|recuperacion de cartera", "8291"),
            (r"facility|limpieza|aseo|mantenimiento locativo|seguridad fisica|seguridad privada|vigilancia|conserj", "8110"),
            (r"cowork|oficinas flexibles|espacios compartidos|espacios de trabajo", "6820"),
            (r"inmobiliari|bienes raices|propiedad horizontal|arrendamiento", "6810"),
            (r"logist|transport|carga|aduan|fletes|almacen", "4923"),
            (r"medical|salud|ips|clinic|farmaceut|biomed|odontol|dispositiv", "3250"),
            (r"software|analyt|data|tech|digital|sistemas|program|cloud|\bia\b|\bai\b|ciber", "6201"),
            (r"comput|hardware|redes|servidores|telecom", "4651"),
            (r"abogad|legal|jurid|derecho|leyes|litig", "6910"),
            (r"contab|auditor|financ|tributar|revisoria|impuesto", "6920"),
            (r"fintech|invers|fondos|credito|valores", "6499"),
            (r"arquitect|ingenier|civil|obras|interventor|diseno tecnico", "7110"),
            (r"publicid|marketing|btl|eventos|comunicacion|medios|agencia", "7310"),
            (r"maquinaria|equipos|repuestos|industrial", "4659"),
            (r"(comercio|distribuidora|mayorista|almacen).*(telas|textil|ropa|confeccion)", "4641"),
            (r"boutique|tienda de ropa|almacen de ropa|venta de prendas|venta de ropa", "4771"),
            (r"zapateria|tienda de calzado|almacen de calzado|venta de calzado", "4772"),
            (r"confeccion|confecciones|prendas de vestir|ropa|costura|maquila textil|uniformes|sastreria|camiseria|pantalones|vestidos|lenceria|moda", "1410"),
            (r"calzado|zapater|fabrica de zapatos|botas|suelas|marroquiner|curtiembre|cueros|bolsos de cuero|billeteras de cuero", "1521"),
            (r"textil|textiles|hilatura|hilados|hilanderia|hilaza|tejeduria|telas|tejidos|dril|denim|indigo|tintoreria textil|estampado textil", "1312"),
            (r"distribuid|distribuc|comercializad|comercializac|mayorist", "4690"),
            (r"\b(consultor|asesor|asesoria|consultoria|advisory|estrategi)\b", "7020"),
        ]

        for pat, code in regex_patterns:
            if re.search(pat, lower):
                return CiiuCode.from_code(code), 0.95, "regex"

        # 2. Local BM25 inverted index search
        entry, score = self.isic_index.resolve_match_with_confidence(text)
        if entry:
            confidence = min(1.0, round(score / 10.0, 2))
            if score >= 3.0:
                return CiiuCode.from_code(entry.code), confidence, "bm25"
            else:
                return CiiuCode.from_code(entry.code), max(0.15, confidence), "low_confidence_bm25"

        # 3. Default fallback
        return CiiuCode.from_code("7020"), 0.10, "fallback"

    def batch_classify_ambiguous_companies(
        self,
        companies: List[Dict[str, Any]],
        country_code: str = "CO",
        batch_size: int = 25,
    ) -> List[Dict[str, Any]]:
        """
        Processes a batch of candidate companies. Resolves high-confidence records
        locally, and routes ambiguous corporate entities (< 0.35 confidence or generic fallbacks)
        to Gemini 2.5 Flash in chunks of up to 25 records.
        """
        results: List[Dict[str, Any]] = []
        ambiguous_queue: List[Tuple[int, Dict[str, Any]]] = []

        # Step 1: Initial local classification
        for idx, comp in enumerate(companies):
            name = comp.get("company_name") or comp.get("razon_social") or comp.get("name") or ""
            email = comp.get("email") or comp.get("official_email") or ""
            desc = comp.get("declared_activity") or comp.get("sector") or comp.get("description") or ""

            ciiu_obj, confidence, source = self.classify_company(name, email, desc)
            enriched = dict(comp)
            enriched["ciiu_code"] = ciiu_obj.code
            enriched["ciiu_description"] = ciiu_obj.description
            enriched["ciiu_sector_macro"] = ciiu_obj.sector_macro
            enriched["ciiu_confidence"] = confidence
            enriched["ciiu_source"] = source

            results.append(enriched)

            # Check if entity is ambiguous and needs Gemini inference
            is_ambiguous = (
                confidence < 0.35
                or source in ("fallback", "low_confidence_bm25")
                or (ciiu_obj.code in ("7020", "4690") and source != "regex")
            )
            if is_ambiguous:
                ambiguous_queue.append((idx, enriched))

        # Step 2: Batched Gemini Flash classification if API key is present
        if ambiguous_queue and self.api_key:
            for i in range(0, len(ambiguous_queue), batch_size):
                chunk = ambiguous_queue[i : i + batch_size]
                chunk_items = [
                    {
                        "id": orig_idx,
                        "name": item.get("company_name") or item.get("razon_social") or item.get("name"),
                        "declared_activity": item.get("declared_activity") or item.get("sector") or "",
                        "email": item.get("email") or "",
                    }
                    for orig_idx, item in chunk
                ]
                classified_map, token_usage = self._call_gemini_batch_classification(chunk_items, country_code)
                for orig_idx, item in chunk:
                    if orig_idx in classified_map:
                        g_code, g_desc, g_conf = classified_map[orig_idx]
                        results[orig_idx]["ciiu_code"] = g_code
                        results[orig_idx]["ciiu_description"] = g_desc
                        results[orig_idx]["ciiu_confidence"] = g_conf
                        results[orig_idx]["ciiu_source"] = "gemini_flash"
                        if token_usage:
                            results[orig_idx]["ciiu_token_usage"] = token_usage

        return results

    def _call_gemini_batch_classification(
        self,
        items: List[Dict[str, Any]],
        country_code: str = "CO",
    ) -> Tuple[Dict[int, Tuple[str, str, float]], Dict[str, Any]]:
        """
        Executes a fast batched inference call against Gemini 2.5 Flash with strict 2.5s client timeout.
        Returns a mapping of id -> (4-digit code, description, confidence) and token usage metadata.
        """
        if not self.api_key:
            return {}, {}

        system_instruction = (
            f"You are an expert economic statistician specializing in DANE CIIU Rev. 4 A.C. and UN ISIC Rev. 4 "
            f"for corporate entities in {country_code}.\n"
            "Given a list of corporate entities with corporate name, declared activity, and email domain, "
            "determine the most likely 4-digit CIIU code (e.g. 1312, 1410, 1521, 4641, 4771, 6201, 7020) for each.\n"
            "Output a JSON object with key 'classifications' containing a list of objects:\n"
            '{"id": integer, "ciiu_code": "4-digit string", "title": "Activity name", "confidence": float between 0.0 and 1.0}'
        )

        prompt_body = {
            "contents": [{"parts": [{"text": json.dumps({"entities": items}, ensure_ascii=False)}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
            },
        }

        models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        usage_data: Dict[str, Any] = {}
        chosen_model: Optional[str] = None
        parsed_classifications: Dict[int, Tuple[str, str, float]] = {}

        for model_name in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            try:
                with httpx.Client(timeout=2.5) as client:
                    resp = client.post(url, json=prompt_body)
                    resp.raise_for_status()
                    data = resp.json()
                text_response = data["candidates"][0]["content"]["parts"][0]["text"]
                usage_data = data.get("usageMetadata", {})
                chosen_model = model_name
                payload = json.loads(text_response)
                for entry in payload.get("classifications", []):
                    c_id = entry.get("id")
                    code = str(entry.get("ciiu_code", "")).strip().zfill(4)
                    title = entry.get("title", "")
                    conf = float(entry.get("confidence", 0.85))
                    if c_id is not None and code:
                        parsed_classifications[c_id] = (code, title, conf)
                break
            except Exception as e:
                logger.warning(f"Batch Gemini classification failed on model {model_name}: {e}")
                continue

        # Financial Observability Metrics
        token_metrics = {}
        if usage_data:
            p_tokens = usage_data.get("promptTokenCount", 0)
            c_tokens = usage_data.get("candidatesTokenCount", 0)
            total = usage_data.get("totalTokenCount", p_tokens + c_tokens)
            cost_cop = round(((p_tokens * 0.075 / 1_000_000) + (c_tokens * 0.30 / 1_000_000)) * 4100, 4)
            token_metrics = {
                "model": chosen_model,
                "prompt_tokens": p_tokens,
                "candidates_tokens": c_tokens,
                "total_tokens": total,
                "cost_cop": cost_cop,
            }

        return parsed_classifications, token_metrics

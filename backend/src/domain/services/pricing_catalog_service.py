"""
Chiketto Universal Dynamic Pricing Catalog Service.
Decouples product definitions, regional currency price books, volume discount curves,
and affiliate marketing commissions (Tinkko) from application source code into the database.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger("michito.pricing_catalog")


class PricingCatalogService:
    _instance: Optional["PricingCatalogService"] = None

    # Resilient fallback catalog (Scenario B + Confirmed Flatter Curves)
    DEFAULT_RATES_COP = {1: 150000, 2: 620000, 3: 1500000}  # Cents: $1.500, $6.200, $15.000 COP
    DEFAULT_RATES_USD = {1: 38, 2: 155, 3: 375}              # Cents: $0.38, $1.55, $3.75 USD
    DEFAULT_RATES_DOP = {1: 2500, 2: 10000, 3: 25000}        # Cents: 25, 100, 250 DOP

    DEFAULT_DISCOUNT_CURVE = [
        {"min_quantity": 1000, "discount_percentage": 32.0},
        {"min_quantity": 500, "discount_percentage": 25.0},
        {"min_quantity": 250, "discount_percentage": 18.0},
        {"min_quantity": 100, "discount_percentage": 10.0},
        {"min_quantity": 50, "discount_percentage": 5.0},
        {"min_quantity": 25, "discount_percentage": 0.0},
    ]

    MIN_FLOOR_COP = 2500000  # $25.000 COP in cents
    MIN_FLOOR_USD = 625      # $6.25 USD in cents
    MIN_FLOOR_DOP = 40000    # 400 DOP in cents

    def __init__(self, session_factory=None):
        self._session_factory = session_factory
        self._cache_timestamp: Optional[datetime] = None
        self._cached_catalog: Optional[Dict[str, Any]] = None

    @classmethod
    def get_instance(cls, session_factory=None) -> "PricingCatalogService":
        if cls._instance is None:
            cls._instance = cls(session_factory=session_factory)
        elif session_factory is not None:
            cls._instance._session_factory = session_factory
        return cls._instance

    def _get_session(self):
        if self._session_factory:
            return self._session_factory()
        from src.adapters.db.sql_order_adapter import SqlOrderAdapter
        adapter = SqlOrderAdapter()
        return adapter._get_session()

    def seed_catalog_if_empty(self) -> bool:
        """Seeds the normalized catalog tables if they are unpopulated."""
        try:
            from src.adapters.db.models import (
                ProductCatalogModel,
                ProductRegionalPriceModel,
                ProductVolumeDiscountModel,
                AffiliateModel,
                AffiliateCommissionRuleModel,
            )
            with self._get_session() as session:
                existing = session.query(ProductCatalogModel).first()
                if existing:
                    return False  # Already seeded

                logger.info("[PricingCatalog] Seeding initial Michito products, regional prices, discounts & affiliate rules...")

                # 1. Master Products
                products = [
                    ProductCatalogModel(
                        id="michito_tier_1",
                        category="data_intelligence",
                        tier=1,
                        name="Tier 1: Directorio Base Corporativo",
                        description="Mailbox verificado corporativo, Representante Legal estatutario y datos auditados de contacto.",
                        fulfillment_type="data_harvest",
                    ),
                    ProductCatalogModel(
                        id="michito_tier_2",
                        category="data_intelligence",
                        tier=2,
                        name="Tier 2: Decisor C-Level & Celular Directo",
                        description="Tomador de decisión verificado con celular directo, correo corporativo 0-rebotes y perfil de LinkedIn.",
                        fulfillment_type="data_harvest",
                    ),
                    ProductCatalogModel(
                        id="michito_tier_3",
                        category="data_intelligence",
                        tier=3,
                        name="Tier 3: Auditoría Financiera & Debida Diligencia",
                        description="Dossier con estados contables auditados NIIF, cálculo de EBITDA, márgenes operativos y scoring de demandas judiciales.",
                        fulfillment_type="data_harvest",
                    ),
                ]
                for p in products:
                    session.add(p)
                session.flush()

                # 2. Regional Prices (COP, DOP, USD)
                prices = [
                    # Colombia (COP)
                    ProductRegionalPriceModel(id="michito_t1_cop", product_id="michito_tier_1", country_code="CO", currency="COP", base_unit_price_cents=150000, tax_rate_percent=19.0),
                    ProductRegionalPriceModel(id="michito_t2_cop", product_id="michito_tier_2", country_code="CO", currency="COP", base_unit_price_cents=620000, tax_rate_percent=19.0),
                    ProductRegionalPriceModel(id="michito_t3_cop", product_id="michito_tier_3", country_code="CO", currency="COP", base_unit_price_cents=1500000, tax_rate_percent=19.0),
                    # Dominican Republic (DOP)
                    ProductRegionalPriceModel(id="michito_t1_dop", product_id="michito_tier_1", country_code="DO", currency="DOP", base_unit_price_cents=2500, tax_rate_percent=18.0),
                    ProductRegionalPriceModel(id="michito_t2_dop", product_id="michito_tier_2", country_code="DO", currency="DOP", base_unit_price_cents=10000, tax_rate_percent=18.0),
                    ProductRegionalPriceModel(id="michito_t3_dop", product_id="michito_tier_3", country_code="DO", currency="DOP", base_unit_price_cents=25000, tax_rate_percent=18.0),
                    # International / Ecuador (USD)
                    ProductRegionalPriceModel(id="michito_t1_usd", product_id="michito_tier_1", country_code="MULTI", currency="USD", base_unit_price_cents=38, tax_rate_percent=0.0),
                    ProductRegionalPriceModel(id="michito_t2_usd", product_id="michito_tier_2", country_code="MULTI", currency="USD", base_unit_price_cents=155, tax_rate_percent=0.0),
                    ProductRegionalPriceModel(id="michito_t3_usd", product_id="michito_tier_3", country_code="MULTI", currency="USD", base_unit_price_cents=375, tax_rate_percent=0.0),
                ]
                for pr in prices:
                    session.add(pr)

                # 3. Progressive Volume Discount Curves
                discount_tiers = [
                    (50, 5.0),
                    (100, 10.0),
                    (250, 18.0),
                    (500, 25.0),
                    (1000, 32.0),
                ]
                for p in products:
                    for min_qty, pct in discount_tiers:
                        vd = ProductVolumeDiscountModel(
                            product_id=p.id,
                            min_quantity=min_qty,
                            discount_percentage=pct,
                        )
                        session.add(vd)

                # 4. Affiliates (Tinkko & Direct)
                affiliates = [
                    AffiliateModel(
                        partner_id="tinkko",
                        name="Tinkko Coworking S.A.S.",
                        tax_id="901000111-2",
                        contact_email="comunidad@tinkko.com",
                        is_active=True,
                    ),
                    AffiliateModel(
                        partner_id="direct",
                        name="Canal Directo Chiketto",
                        tax_id="901768811-1",
                        contact_email="info@chiketto.co",
                        is_active=True,
                    ),
                ]
                for aff in affiliates:
                    session.add(aff)
                session.flush()

                # 5. Commission Rules for Tinkko
                rules = [
                    AffiliateCommissionRuleModel(
                        partner_id="tinkko",
                        product_id="michito_tier_1",
                        commission_percentage=25.0,
                        customer_discount_percentage=10.0,
                    ),
                    AffiliateCommissionRuleModel(
                        partner_id="tinkko",
                        product_id="michito_tier_2",
                        commission_percentage=25.0,
                        customer_discount_percentage=10.0,
                    ),
                    AffiliateCommissionRuleModel(
                        partner_id="tinkko",
                        product_id="michito_tier_3",
                        commission_percentage=25.0,
                        customer_discount_percentage=10.0,
                    ),
                ]
                for r in rules:
                    session.add(r)

                session.commit()
                logger.info("[PricingCatalog] Dynamic pricing catalog seeded successfully.")
                self._cached_catalog = None
                return True
        except Exception as e:
            logger.warning(f"[PricingCatalog] Error seeding pricing catalog (using fallbacks): {e}")
            return False

    def get_active_catalog(self, currency: str = "COP") -> Dict[str, Any]:
        """
        Returns structured active pricing catalog for frontend consumers and API endpoints.
        """
        cur = currency.upper()
        try:
            from src.adapters.db.models import (
                ProductCatalogModel,
                ProductRegionalPriceModel,
                ProductVolumeDiscountModel,
            )
            with self._get_session() as session:
                products = (
                    session.query(ProductCatalogModel)
                    .filter(ProductCatalogModel.is_active == True)
                    .order_by(ProductCatalogModel.tier.asc())
                    .all()
                )

                if products:
                    tier_prices: Dict[int, float] = {}
                    tier_prices_cents: Dict[int, int] = {}
                    products_list: List[Dict[str, Any]] = []

                    # Query active regional prices for this currency in a single indexed query
                    prices_by_product: Dict[str, Any] = {}
                    all_prices = (
                        session.query(ProductRegionalPriceModel)
                        .filter(ProductRegionalPriceModel.currency == cur, ProductRegionalPriceModel.is_active == True)
                        .all()
                    )
                    for rp in all_prices:
                        prices_by_product[rp.product_id] = rp

                    # Query volume discounts
                    discounts_by_product: Dict[str, List[Any]] = {}
                    all_discounts = session.query(ProductVolumeDiscountModel).all()
                    for vd in all_discounts:
                        discounts_by_product.setdefault(vd.product_id, []).append(vd)

                    for p in products:
                        reg_price = prices_by_product.get(p.id)
                        base_cents = reg_price.base_unit_price_cents if reg_price else self._get_fallback_rate(p.tier or 2, cur)
                        tier_val = p.tier or 2
                        tier_prices[tier_val] = base_cents / 100.0
                        tier_prices_cents[tier_val] = base_cents

                        # Volume discounts
                        p_discounts = discounts_by_product.get(p.id, [])
                        discounts = [
                            {"min_quantity": vd.min_quantity, "discount_percentage": vd.discount_percentage}
                            for vd in sorted(p_discounts, key=lambda x: x.min_quantity, reverse=True)
                        ] if p_discounts else self.DEFAULT_DISCOUNT_CURVE

                        products_list.append({
                            "id": p.id,
                            "tier": p.tier,
                            "name": p.name,
                            "description": p.description,
                            "category": p.category,
                            "currency": cur,
                            "base_unit_price": base_cents / 100.0,
                            "base_unit_price_cents": base_cents,
                            "min_order_quantity": reg_price.min_order_quantity if reg_price else 25,
                            "volume_discounts": discounts,
                        })

                    return {
                        "status": "success",
                        "currency": cur,
                        "min_order_leads": 25,
                        "tier_prices": tier_prices,
                        "tier_prices_cents": tier_prices_cents,
                        "volume_discount_curve": self.DEFAULT_DISCOUNT_CURVE,
                        "products": products_list,
                    }
        except Exception as e:
            logger.debug(f"[PricingCatalog] Using in-memory fallback catalog: {e}")

        # In-memory fallback
        fb_rates = (
            self.DEFAULT_RATES_USD if cur == "USD"
            else (self.DEFAULT_RATES_DOP if cur == "DOP" else self.DEFAULT_RATES_COP)
        )
        return {
            "status": "success",
            "currency": cur,
            "min_order_leads": 25,
            "tier_prices": {k: v / 100.0 for k, v in fb_rates.items()},
            "tier_prices_cents": fb_rates,
            "volume_discount_curve": self.DEFAULT_DISCOUNT_CURVE,
            "products": [
                {
                    "id": f"michito_tier_{t}",
                    "tier": t,
                    "name": f"Tier {t}",
                    "currency": cur,
                    "base_unit_price": fb_rates[t] / 100.0,
                    "base_unit_price_cents": fb_rates[t],
                    "min_order_quantity": 25,
                    "volume_discounts": self.DEFAULT_DISCOUNT_CURVE,
                }
                for t in (1, 2, 3)
            ],
        }

    def _get_fallback_rate(self, tier: int, currency: str) -> int:
        cur = currency.upper()
        if cur == "USD":
            return self.DEFAULT_RATES_USD.get(tier, self.DEFAULT_RATES_USD[2])
        elif cur == "DOP":
            return self.DEFAULT_RATES_DOP.get(tier, self.DEFAULT_RATES_DOP[2])
        return self.DEFAULT_RATES_COP.get(tier, self.DEFAULT_RATES_COP[2])

    def calculate_quote(
        self,
        total_qualified: int,
        tier: int = 2,
        currency: str = "COP",
        partner_id: Optional[str] = None,
        allow_courtesy: bool = True,
    ) -> Dict[str, Any]:
        """
        Calculates quote in cents with volume discount brackets, affiliate customer discounts,
        minimum order floor enforcement, and the micro-batch courtesy sample policy.
        """
        if total_qualified <= 0:
            return {
                "total_cents": 0,
                "unit_base_cents": 0,
                "discounted_unit_cents": 0,
                "discount_percentage": 0.0,
                "is_courtesy_sample": False,
            }

        # Micro-batch courtesy rule: If fewer than 5 verified leads meet our quality gates,
        # release as complimentary courtesy sample ($0) to avoid gateway fee drag.
        if allow_courtesy and total_qualified < 5:
            return {
                "total_cents": 0,
                "unit_base_cents": 0,
                "discounted_unit_cents": 0,
                "discount_percentage": 100.0,
                "is_courtesy_sample": True,
            }

        cur = currency.upper()
        unit_base = self._get_fallback_rate(tier, cur)

        # Lookup DB rate if session is available
        try:
            from src.adapters.db.models import ProductCatalogModel, ProductRegionalPriceModel
            with self._get_session() as session:
                prod = session.query(ProductCatalogModel).filter_by(tier=tier, is_active=True).first()
                if prod:
                    rp = (
                        session.query(ProductRegionalPriceModel)
                        .filter_by(product_id=prod.id, currency=cur, is_active=True)
                        .first()
                    )
                    if rp:
                        unit_base = rp.base_unit_price_cents
        except Exception:
            pass

        # Volume discount bracket (Confirmed curve: 50: 5%, 100: 10%, 250: 18%, 500: 25%, 1000: 32%)
        volume_discount = 0.0
        if total_qualified >= 1000:
            volume_discount = 32.0
        elif total_qualified >= 500:
            volume_discount = 25.0
        elif total_qualified >= 250:
            volume_discount = 18.0
        elif total_qualified >= 100:
            volume_discount = 10.0
        elif total_qualified >= 50:
            volume_discount = 5.0
        else:
            volume_discount = 0.0

        # Partner customer discount (e.g. Tinkko 10%)
        partner_discount = 0.0
        partner_commission_pct = 0.0
        if partner_id and partner_id.lower() == "tinkko":
            partner_discount = 10.0
            partner_commission_pct = 25.0

        combined_discount_pct = min(40.0, volume_discount + partner_discount)
        discount_factor = 1.0 - (combined_discount_pct / 100.0)

        discounted_unit = int(unit_base * discount_factor)
        calculated_cents = total_qualified * discounted_unit

        # Enforce minimum order floor
        min_floor = (
            self.MIN_FLOOR_USD if cur == "USD"
            else (self.MIN_FLOOR_DOP if cur == "DOP" else self.MIN_FLOOR_COP)
        )
        total_cents = max(calculated_cents, min_floor)

        return {
            "total_cents": total_cents,
            "unit_base_cents": unit_base,
            "discounted_unit_cents": discounted_unit,
            "volume_discount_percentage": volume_discount,
            "partner_discount_percentage": partner_discount,
            "discount_percentage": combined_discount_pct,
            "is_courtesy_sample": False,
            "min_floor_applied": total_cents == min_floor and calculated_cents < min_floor,
            "partner_commission_percentage": partner_commission_pct,
            "partner_commission_cents": int(total_cents * (partner_commission_pct / 100.0)) if partner_commission_pct > 0 else 0,
        }

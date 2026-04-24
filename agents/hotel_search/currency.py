from __future__ import annotations

import json
import os
from urllib.error import URLError
from urllib.request import urlopen

from agents.hotel_search.models import HotelResult, PriceInfo, SearchRequest


class CurrencyConverter:
    _API_TEMPLATE = "https://open.er-api.com/v6/latest/{base}"

    def __init__(self) -> None:
        self._rates_by_base: dict[str, dict[str, float]] = {}
        self._env_rates = self._load_env_rates()

    def convert_results(self, request: SearchRequest, results: list[HotelResult]) -> list[HotelResult]:
        target_currency = request.price.currency
        for result in results:
            self.convert_price(result.price, target_currency)
        return results

    def convert_price(self, price: PriceInfo, target_currency: str) -> None:
        source_currency = price.currency.strip().upper()
        target_currency = target_currency.strip().upper()
        if not source_currency or source_currency == target_currency:
            price.currency = target_currency or source_currency
            return

        rate = self._get_rate(source_currency, target_currency)
        if rate is None:
            return

        price.original_total = price.total
        price.original_nightly = price.nightly
        price.original_currency = source_currency
        price.conversion_rate = rate
        price.currency = target_currency
        if price.total is not None:
            price.total = round(price.total * rate, 2)
        if price.nightly is not None:
            price.nightly = round(price.nightly * rate, 2)

    def _get_rate(self, source_currency: str, target_currency: str) -> float | None:
        env_key = f"{source_currency}:{target_currency}"
        if env_key in self._env_rates:
            return self._env_rates[env_key]

        rates = self._rates_for_base(source_currency)
        return rates.get(target_currency)

    def _rates_for_base(self, source_currency: str) -> dict[str, float]:
        if source_currency in self._rates_by_base:
            return self._rates_by_base[source_currency]

        rates: dict[str, float] = {}
        try:
            with urlopen(self._API_TEMPLATE.format(base=source_currency), timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError):
            payload = {}

        raw_rates = payload.get("rates", {}) if isinstance(payload, dict) else {}
        if isinstance(raw_rates, dict):
            for currency, value in raw_rates.items():
                try:
                    rates[str(currency).strip().upper()] = float(value)
                except (TypeError, ValueError):
                    continue

        self._rates_by_base[source_currency] = rates
        return rates

    def _load_env_rates(self) -> dict[str, float]:
        raw = os.getenv("HOTEL_SEARCH_EXCHANGE_RATES_JSON", "").strip()
        if not raw:
            return {}
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if not isinstance(value, dict):
            return {}

        rates: dict[str, float] = {}
        for key, rate in value.items():
            try:
                rates[str(key).strip().upper()] = float(rate)
            except (TypeError, ValueError):
                continue
        return rates

"""
Currency conversion using the European Central Bank (ECB) daily reference rates.
No API key required. Rates are updated each business day around 16:00 CET.
Source: https://www.ecb.europa.eu/stats/eurofx/eurofxref/eurofxref-daily.xml
"""

import aiohttp
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

ECB_URL = "https://www.ecb.europa.eu/stats/eurofx/eurofxref/eurofxref-daily.xml"

async def _fetch_ecb_rates() -> tuple[str, Dict[str, float]]:
    """Fetch ECB daily rates. Returns (date, {currency: rate_vs_EUR})."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ECB_URL, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    raise RuntimeError(f"ECB API returned status {response.status}")
                xml_text = await response.text()

        root = ET.fromstring(xml_text)
        ns = {
            "gesmes": "http://www.gesmes.org/xml/2002-08-01",
            "ecb": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
        }

        # Find the Cube[time] element
        time_cube = root.find("./ecb:Cube/ecb:Cube[@time]", ns)
        if time_cube is None:
            raise RuntimeError("Could not parse ECB XML – Cube[@time] not found")

        rate_date = time_cube.attrib["time"]

        # EUR is the base, always equals 1
        rates: Dict[str, float] = {"EUR": 1.0}
        for cube in time_cube.findall("ecb:Cube", ns):
            currency = cube.attrib.get("currency")
            rate = cube.attrib.get("rate")
            if currency and rate:
                rates[currency.upper()] = float(rate)

        return rate_date, rates

    except Exception as e:
        raise RuntimeError(f"Failed to fetch ECB rates: {e}") from e


def _convert(rates: Dict[str, float], from_currency: str, to_currency: str, amount: float) -> tuple[float, float]:
    """
    Convert amount using EUR-based ECB rates.
    Returns (converted_amount, effective_rate from→to).
    """
    if from_currency not in rates:
        raise ValueError(f"Currency not available in ECB data: {from_currency}")
    if to_currency not in rates:
        raise ValueError(f"Currency not available in ECB data: {to_currency}")

    # Convert: from_currency → EUR → to_currency
    amount_in_eur = amount / rates[from_currency]
    converted = amount_in_eur * rates[to_currency]
    effective_rate = rates[to_currency] / rates[from_currency]
    return round(converted, 4), round(effective_rate, 6)


async def currency_converter(**kwargs) -> Dict[str, Any]:
    """Convert an amount between currencies using ECB daily reference rates (no API key needed)."""
    from_currency = kwargs.get("from_currency", "")
    to_currency = kwargs.get("to_currency", "")
    amount_str = kwargs.get("amount")

    if not from_currency or not isinstance(from_currency, str):
        return {"error": "Invalid from_currency"}
    if not to_currency or not isinstance(to_currency, str):
        return {"error": "Invalid to_currency"}
    if amount_str is None:
        return {"error": "amount is required"}

    try:
        amount = float(amount_str)
        if amount <= 0:
            return {"error": "Amount must be positive"}
    except (ValueError, TypeError):
        return {"error": "Invalid amount – must be a number"}

    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    try:
        rate_date, rates = await _fetch_ecb_rates()

        converted_amount, effective_rate = _convert(rates, from_currency, to_currency, amount)

        return {
            "result": f"EXACT CONVERSION: {amount} {from_currency} = {converted_amount} {to_currency}",
            "from_currency": from_currency,
            "to_currency": to_currency,
            "amount": amount,
            "converted_amount": converted_amount,
            "exchange_rate": effective_rate,
            "rate_date": rate_date,
            "source": "European Central Bank (ECB) daily reference rates",
            "instruction": "Use the exact converted_amount value above. Do not approximate or round this value.",
            "calculation": f"{amount} {from_currency} × {effective_rate} = {converted_amount} {to_currency}",
        }

    except ValueError as e:
        logger.warning(f"Currency conversion – unknown currency: {e}")
        return {
            "error": str(e),
            "from_currency": from_currency,
            "to_currency": to_currency,
            "amount": amount,
            "hint": "ECB covers ~30 major currencies. USD, GBP, JPY, CHF, AUD, CAD, CNY, HKD, SEK, NOK etc.",
        }
    except Exception as e:
        logger.error(f"Currency conversion error: {e}")
        return {
            "error": f"Currency conversion failed: {str(e)}",
            "from_currency": from_currency,
            "to_currency": to_currency,
            "amount": amount,
        }

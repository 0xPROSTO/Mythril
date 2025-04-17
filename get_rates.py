import requests
import json
import logging
import os
from datetime import datetime, date, timezone
from pathlib import Path

CURRENCY_FILE = Path("data/currencies.json")

PRIMARY_URL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/rub.json"
FALLBACK_URL = "https://latest.currency-api.pages.dev/v1/currencies/rub.json"

CURRENCIES = ["RUB", "USD", "EUR"]

# UPDATE_INTERVAL = timedelta(hours=12)

log_dir = os.path.dirname("logs/currency.log")
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir)

rates_logger = logging.getLogger("currency")
rates_logger.setLevel(logging.INFO)
handler = logging.FileHandler('logs/currency.log', 'w', 'utf-8')
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
rates_logger.addHandler(handler)

def get_currencies():
    current_data = {
        "date": "1970-01-01",
        "rates": {"RUB": 1.0, "USD": 1.0, "EUR": 1.0}
    }
    if CURRENCY_FILE.exists():
        try:
            with open(CURRENCY_FILE, "r", encoding="utf-8") as f:
                current_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            rates_logger.error(f"Ошибка чтения {CURRENCY_FILE}: {e}")

    try:
        current_date = datetime.strptime(current_data["date"], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        current_date = date(1970, 1, 1)

    today = datetime.now(timezone.utc).date()
    if current_date >= today:
        rates_logger.info("Дата актуальна, возвращаем кэш")
        return current_data

    rates = current_data["rates"]
    date_str = current_date.strftime("%Y-%m-%d")
    try:
        response = requests.get(PRIMARY_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        api_date = datetime.strptime(data.get("date", date_str), "%Y-%m-%d").date()
        if api_date < today:
            rates_logger.warning("API вернул устаревшую дату, возвращаем кэш")
            return current_data
        rates = {currency: data["rub"].get(currency.lower(), 1.0) for currency in CURRENCIES}
        date_str = data["date"]
    except (requests.RequestException, KeyError, ValueError) as e:
        rates_logger.error(f"Ошибка PRIMARY_URL: {e}")
        try:
            response = requests.get(FALLBACK_URL, timeout=5)
            response.raise_for_status()
            data = response.json()
            api_date = datetime.strptime(data.get("date", date_str), "%Y-%m-%d").date()
            if api_date < today:
                rates_logger.warning("API вернул устаревшую дату, возвращаем кэш")
                return current_data
            rates = {currency: data["rub"].get(currency.lower(), 1.0) for currency in CURRENCIES}
            date_str = data["date"]
        except (requests.RequestException, KeyError, ValueError) as e:
            rates_logger.error(f"Ошибка FALLBACK_URL: {e}")
            rates_logger.info("Используем старые курсы")
            return current_data

    new_data = {
        "date": date_str,
        "rates": rates
    }
    try:
        with open(CURRENCY_FILE, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=4)
        rates_logger.info(f"Курсы обновлены: {date_str}")
    except OSError as e:
        rates_logger.error(f"Ошибка записи {CURRENCY_FILE}: {e}")
        return current_data

    return new_data


if __name__ == "__main__":
    # Тест
    result = get_currencies()
    print(json.dumps(result, indent=4, ensure_ascii=False))

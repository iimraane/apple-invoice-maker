#!/usr/bin/env python3

import calendar
import json
import random
import re
import string
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html import escape
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen


BASE_DIR = Path(__file__).resolve().parent
PROFILES_DIR = BASE_DIR / "profiles"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_HTML = OUTPUT_DIR / "invoice.html"
OUTPUT_PNG = OUTPUT_DIR / "invoice.png"

FIELDS = (
    "full_name",
    "street",
    "city",
    "apple_account_email",
    "device_label",
    "app_name",
    "subscription_name",
    "logo_url",
    "price_ttc_eur",
    "renew_date",
)

MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

FALLBACK_LOGO = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120' viewBox='0 0 120 120'>"
    "<rect width='120' height='120' rx='24' fill='%23f4f4f5'/>"
    "<text x='60' y='72' text-anchor='middle' font-size='44' font-family='Arial' fill='%23333'>D</text>"
    "</svg>"
)

FALLBACK_HEADER_LOGO = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' width='160' height='56' viewBox='0 0 160 56'>"
    "<rect width='160' height='56' rx='10' fill='%23b80000'/>"
    "<text x='80' y='36' text-anchor='middle' font-size='24' font-family='Arial' fill='white'>"
    "DEMO"
    "</text></svg>"
)


def ensure_dirs() -> None:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_profile_name(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip())
    return safe.strip("_") or "profile"


def ask_input(label: str, default: Optional[str] = None, required: bool = True) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        value = input(f"{label}{suffix}: ").strip()
        if not value and default is not None:
            return default
        if not value and required:
            print("Champ requis.")
            continue
        return value


def ask_yes_no(label: str, default: bool = False) -> bool:
    options = " [Y/n]" if default else " [y/N]"
    while True:
        answer = input(f"{label}{options}: ").strip().lower()
        if not answer:
            return default
        if answer in {"y", "yes", "o", "oui"}:
            return True
        if answer in {"n", "no", "non"}:
            return False
        print("Réponse attendue: y/n.")


def parse_amount(value: str) -> Decimal:
    cleaned = value.strip().replace("€", "").replace(" ", "").replace(",", ".")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError("Prix invalide.") from exc
    if amount < 0:
        raise ValueError("Le prix doit être positif.")
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def normalize_price(value: str) -> str:
    return f"{parse_amount(value):.2f}"


def parse_short_date(value: str) -> date:
    try:
        return datetime.strptime(value.strip(), "%d/%m/%y").date()
    except ValueError as exc:
        raise ValueError("Date invalide. Utilise le format jj/mm/aa.") from exc


def normalize_renew_date(value: str) -> str:
    return parse_short_date(value).strftime("%d/%m/%y")


def subtract_one_month(input_date: date) -> date:
    if input_date.month == 1:
        target_year = input_date.year - 1
        target_month = 12
    else:
        target_year = input_date.year
        target_month = input_date.month - 1
    max_day = calendar.monthrange(target_year, target_month)[1]
    return date(target_year, target_month, min(input_date.day, max_day))


def format_long_date(value: date) -> str:
    return f"{value.day} {MONTH_NAMES[value.month - 1]} {value.year}"


def format_eur(value: Decimal) -> str:
    rendered = f"{value:,.2f}".replace(",", " ").replace(".", ",")
    return f"{rendered} €"


def list_profiles() -> list:
    return sorted(PROFILES_DIR.glob("*.json"))


def select_profile_file() -> Optional[Path]:
    profiles = list_profiles()
    if not profiles:
        print("Aucun profil trouvé dans ./profiles.")
        return None
    print("\nProfils disponibles:")
    for idx, profile in enumerate(profiles, start=1):
        print(f"{idx}. {profile.stem}")
    while True:
        raw = input("Numéro du profil (ou Entrée pour annuler): ").strip()
        if not raw:
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(profiles):
            return profiles[int(raw) - 1]
        print("Sélection invalide.")


def load_profile(path: Path) -> Dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    profile: Dict[str, str] = {}
    for field in FIELDS:
        profile[field] = str(data.get(field, "")).strip()
    return profile


def save_profile(profile: Dict[str, str], profile_name: str) -> Path:
    safe_name = sanitize_profile_name(profile_name)
    path = PROFILES_DIR / f"{safe_name}.json"
    path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def ask_validated(
    label: str,
    validator,
    default: Optional[str] = None,
    required: bool = True,
) -> str:
    while True:
        raw = ask_input(label, default=default, required=required)
        if not raw and not required:
            return raw
        try:
            return validator(raw)
        except ValueError as exc:
            print(exc)


def collect_profile_inputs(base: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    source = base or {}
    profile: Dict[str, str] = {}
    print("\nSaisie des champs du profil:")
    profile["full_name"] = ask_input("Nom complet", source.get("full_name"))
    profile["street"] = ask_input("Rue", source.get("street"))
    profile["city"] = ask_input("Ville", source.get("city"))
    profile["apple_account_email"] = ask_input(
        "Apple Account (email)",
        source.get("apple_account_email"),
    )
    profile["device_label"] = ask_input(
        "Nom affiché après \"iPhone d’\"",
        source.get("device_label"),
    )
    profile["app_name"] = ask_input("Nom de l'app", source.get("app_name"))
    profile["subscription_name"] = ask_input(
        "Nom exact de l'abonnement",
        source.get("subscription_name"),
    )
    profile["logo_url"] = ask_input(
        "URL du logo (Entrée pour logo neutre)",
        source.get("logo_url"),
        required=False,
    )
    
    profile["price_ttc_eur"] = ask_validated(
        "Prix TTC en EUR (ex: 499.99)",
        normalize_price,
        source.get("price_ttc_eur"),
    )
    profile["renew_date"] = ask_validated(
        "Date de renouvellement (jj/mm/aa)",
        normalize_renew_date,
        source.get("renew_date"),
    )
    return profile


def generate_ids() -> Dict[str, str]:
    return {
        "sequence": "2-" + "".join(random.choices(string.digits, k=10)),
        "order_id": "".join(random.choices(string.ascii_uppercase + string.digits, k=10)),
        "document": "".join(random.choices(string.digits, k=12)),
    }


def city_to_department(city: str) -> Tuple[str, str]:
    query = quote(city.strip())
    url = (
        "https://geo.api.gouv.fr/communes"
        f"?nom={query}&fields=departement,codesPostaux&boost=population&limit=1"
    )
    try:
        with urlopen(url, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError):
        return "Département inconnu", "00000"

    if not payload:
        return "Département inconnu", "00000"

    first = payload[0]
    department = (first.get("departement") or {}).get("nom") or "Département inconnu"
    postal_codes = first.get("codesPostaux") or []
    postal_code = postal_codes[0] if postal_codes else "00000"
    return department, postal_code


def build_invoice_payload(profile: Dict[str, str]) -> Dict[str, str]:
    ttc = parse_amount(profile["price_ttc_eur"])
    subtotal = (ttc / Decimal("1.20")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    vat = (ttc - subtotal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    renew_date = parse_short_date(profile["renew_date"])
    purchase_date = subtract_one_month(renew_date)
    department, postal_code = city_to_department(profile["city"])
    ids = generate_ids()

    logo = profile["logo_url"].strip() or FALLBACK_LOGO
    device_label = profile["device_label"].strip()
    if device_label.lower().startswith("iphone"):
        device_line = device_label
    else:
        device_line = f"iPhone d’{device_label}"

    return {
        "full_name": profile["full_name"],
        "street": profile["street"],
        "city": profile["city"],
        "postal_code": postal_code,
        "department": department,
        "country": "France",
        "apple_account_email": profile["apple_account_email"],
        "device_line": device_line,
        "app_name": profile["app_name"],
        "subscription_name": profile["subscription_name"],
        "logo_url": logo,
        "purchase_date": format_long_date(purchase_date),
        "renew_date": format_long_date(renew_date),
        "subtotal": format_eur(subtotal),
        "vat": format_eur(vat),
        "ttc": format_eur(ttc),
        "sequence": ids["sequence"],
        "order_id": ids["order_id"],
        "document": ids["document"],
    }


def render_invoice_html(payload: Dict[str, str]) -> str:
    logo_url = escape(payload["logo_url"], quote=True)

    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Invoice Demo</title>
  <style>
    :root {{
      --bg: #ececed;
      --text: #333;
      --muted: #666;
      --line: #bdbdbd;
      --accent: #0a65d8;
      --danger: #b80000;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
      color: var(--text);
      background: var(--bg);
    }}
    .watermark {{
      position: fixed;
      inset: -25vh -20vw;
      z-index: 9999;
      pointer-events: none;
      transform: rotate(-28deg);
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      grid-auto-rows: 27vh;
      opacity: 0.2;
    }}
    .watermark span {{
      display: block;
      align-self: center;
      justify-self: center;
      color: var(--danger);
      font-size: 22vw;
      font-weight: 900;
      line-height: 0.8;
      letter-spacing: 0.02em;
      user-select: none;
      text-transform: uppercase;
    }}
    .page {{
      width: min(1280px, 96vw);
      margin: 0 auto;
      padding: 18px 18px 44px;
      position: relative;
      z-index: 1;
    }}
    .header-logo {{
      display: block;
      margin: 0 0 18px;
      line-height: 0;
    }}
    .header-logo img {{
      display: block;
      height: 56px;
      width: auto;
      max-width: min(360px, 70vw);
      object-fit: contain;
    }}
    h1 {{
      margin: 0 0 36px;
      font-size: 50px;
      line-height: 1;
      font-weight: 700;
      color: #222;
    }}
    .meta p {{
      margin: 0 0 8px;
      font-size: 29px;
    }}
    .meta .label {{
      font-weight: 700;
      margin-right: 8px;
    }}
    .meta a {{
      color: #0a5fc7;
      text-decoration: underline;
    }}
    .item {{
      margin-top: 54px;
      display: grid;
      grid-template-columns: 88px 1fr auto;
      gap: 18px;
      align-items: start;
    }}
    .logo-box {{
      width: 88px;
      height: 88px;
      border-radius: 18px;
      overflow: hidden;
      border: 1px solid #cfd2d7;
      background: #fff;
    }}
    .logo-box img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}
    .item h2 {{
      margin: 0 0 4px;
      font-size: 38px;
      line-height: 1.1;
    }}
    .item p {{
      margin: 0 0 6px;
      color: var(--muted);
      font-size: 30px;
      line-height: 1.2;
    }}
    .price {{
      text-align: right;
      min-width: 280px;
    }}
    .price .total {{
      margin: 0 0 8px;
      font-size: 42px;
      font-weight: 700;
      color: #333;
    }}
    .price .vat {{
      font-size: 30px;
      color: #5d5d5d;
    }}
    .billing {{
      margin-top: 68px;
    }}
    .billing h3 {{
      margin: 0 0 16px;
      font-size: 46px;
      line-height: 1.1;
    }}
    .billing-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 30px;
    }}
    .billing-grid p {{
      margin: 0 0 8px;
      font-size: 38px;
      line-height: 1.2;
    }}
    .billing-grid .right p {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
    }}
    .billing-grid .right .strong {{
      font-weight: 700;
    }}
    .divider {{
      margin: 14px 0 12px;
      border: none;
      border-top: 2px solid var(--line);
    }}
    .foot {{
      margin-top: 32px;
      border-top: 1px solid #cacaca;
      padding-top: 26px;
      font-size: 34px;
      color: #444;
      line-height: 1.35;
    }}
    .cta {{
      display: inline-block;
      margin-top: 26px;
      padding: 14px 24px;
      background: var(--accent);
      color: #fff;
      border-radius: 12px;
      font-size: 28px;
      text-decoration: none;
    }}
    .disclaimer {{
      margin-top: 22px;
      font-size: 24px;
      color: #7a7a7a;
    }}
    @media (max-width: 980px) {{
      .page {{
        width: 100%;
        padding: 18px;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <div class="header-logo">
      <img src="https://ci3.googleusercontent.com/meips/ADKq_NZNDsRDDITE7K1SrXZIG0zxA0iDYR5q5uk57VRAsrfBbidcm0_TgE49uZnvzc8SWQ437e_mAuZoqSBSGeHKnN8wE_6DLDOlxAgF_gsZVJXCSsM=s0-d-e1-ft#https://s.mzstatic.com/email/modern/logo/apple-134-70x84.png" alt="Header logo" />
    </div>
    <h1>Invoice</h1>

    <section class="meta">
      <p>{escape(payload["purchase_date"])}</p>
      <p><span class="label">Sequence:</span>{escape(payload["sequence"])}</p>
      <p><span class="label">Order ID:</span>{escape(payload["order_id"])}</p>
      <p><span class="label">Document:</span>{escape(payload["document"])}</p>
      <p><span class="label">Apple Account:</span><a href="mailto:{escape(payload["apple_account_email"], quote=True)}">{escape(payload["apple_account_email"])}</a></p>
    </section>

    <section class="item">
      <div class="logo-box">
        <img src="{logo_url}" alt="App logo" />
      </div>
      <div>
        <h2>{escape(payload["app_name"])}</h2>
        <p>{escape(payload["subscription_name"])}</p>
        <p>Renews {escape(payload["renew_date"])}</p>
        <p>{escape(payload["device_line"])}</p>
      </div>
      <div class="price">
        <p class="total">{escape(payload["ttc"])}</p>
        <p class="vat">Inclusive of VAT at %20&nbsp;&nbsp;{escape(payload["vat"])}</p>
      </div>
    </section>

    <section class="billing">
      <h3>Billing and Payment</h3>
      <div class="billing-grid">
        <div class="left">
          <p>{escape(payload["full_name"])}</p>
          <p>{escape(payload["street"])}</p>
          <p>{escape(payload["postal_code"])}</p>
          <p>{escape(payload["city"])} {escape(payload["department"])} {escape(payload["country"])}</p>
        </div>
        <div class="right">
          <p><span>Subtotal</span><span>{escape(payload["subtotal"])}</span></p>
          <p><span>VAT charged at %20</span><span>{escape(payload["vat"])}</span></p>
          <hr class="divider" />
          <p><span class="strong">Store Credit</span><span>{escape(payload["ttc"])}</span></p>
        </div>
      </div>
    </section>

    <section class="foot">
      <p>You can turn off renewal receipts to stop getting emails each time your subscriptions renew.</p>
      <a class="cta" href="#">Turn Off Renewal Receipt Emails</a>
      <p class="disclaimer">Document de démonstration uniquement. Sans valeur comptable ou légale.</p>
    </section>
  </main>
</body>
</html>
"""


def export_png_with_playwright(html_path: Path, png_path: Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("\nPNG non généré: Playwright n'est pas installé.")
        print("Installe-le avec:")
        print("  python3 -m pip install playwright")
        print("  python3 -m playwright install chromium")
        return False

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 2200})
            page.goto(html_path.resolve().as_uri(), wait_until="domcontentloaded", timeout=30000)
            page.screenshot(path=str(png_path), full_page=True)
            browser.close()
        return True
    except Exception as exc:
        print("\nPNG non généré: Playwright/Chromium indisponible ou erreur de capture.")
        print(f"Détail: {exc}")
        print("Commande de setup:")
        print("  python3 -m pip install playwright")
        print("  python3 -m playwright install chromium")
        return False


def show_menu() -> str:
    print("\n=== Invoice Tool ===")
    print("1. Créer un profil")
    print("2. Charger un profil")
    print("3. Générer la facture (HTML + PNG)")
    print("0. Quitter")
    return input("Choix: ").strip()


def main() -> None:
    ensure_dirs()
    current_profile: Optional[Dict[str, str]] = None
    current_profile_name: Optional[str] = None

    while True:
        choice = show_menu()

        if choice == "1":
            current_profile = collect_profile_inputs()
            profile_name = ask_input("Nom du profil à sauvegarder", default="demo a modifier")
            profile_path = save_profile(current_profile, profile_name)
            current_profile_name = profile_path.stem
            print(f"Profil sauvegardé: {profile_path}")

        elif choice == "2":
            selected = select_profile_file()
            if selected is None:
                continue
            current_profile = load_profile(selected)
            current_profile_name = selected.stem
            print(f"Profil chargé: {selected}")
            if ask_yes_no("Modifier des champs maintenant ?", default=False):
                current_profile = collect_profile_inputs(current_profile)
                if ask_yes_no("Sauvegarder les modifications ?", default=True):
                    save_path = save_profile(current_profile, current_profile_name)
                    print(f"Profil sauvegardé: {save_path}")

        elif choice == "3":
            if current_profile is None:
                print("Aucun profil en mémoire. Crée ou charge un profil d'abord.")
                continue
            if ask_yes_no("Modifier des champs avant génération ?", default=True):
                current_profile = collect_profile_inputs(current_profile)

            if ask_yes_no("Sauvegarder ce profil ?", default=True):
                default_name = current_profile_name or "modele_demo"
                name = ask_input("Nom du profil", default=default_name)
                save_path = save_profile(current_profile, name)
                current_profile_name = save_path.stem
                print(f"Profil sauvegardé: {save_path}")

            payload = build_invoice_payload(current_profile)
            html_output = render_invoice_html(payload)
            OUTPUT_HTML.write_text(html_output, encoding="utf-8")
            print(f"\nHTML généré: {OUTPUT_HTML}")

            if export_png_with_playwright(OUTPUT_HTML, OUTPUT_PNG):
                print(f"PNG généré: {OUTPUT_PNG}")
            else:
                print("PNG non disponible pour cette exécution, HTML prêt.")

        elif choice == "0":
            print("Fin.")
            break

        else:
            print("Choix invalide.")


if __name__ == "__main__":
    main()

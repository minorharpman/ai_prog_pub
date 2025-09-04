'''
A Selenium egy Python könyvtár , ami lehetővé teszi, hogy automatizáld a böngészőt.
A Selenium „böngészőt nyit”, valójában  egy WebDriver-t indít el, ami a kiválasztott böngészőhöz kapcsolódik.
A WebDriver a Selenium és a böngésző között közvetít, így tudsz Python kóddal navigálni, kattintani, űrlapot kitölteni.
Futtatás:


py laptophu_adatletoltes_public.py --url https://www.laptop.hu/kirakat
py laptophu_adatletoltes_public.py --url https://www.laptop.hu/laptop/lenovo/

'''


import argparse
from typing import List, Tuple

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from typing import List, Dict

import pandas as pd
from pathlib import Path


# ---- 1) Böngésző indítása ---------------------------------------------------
def build_driver(headless: bool = True) -> webdriver.Chrome:
    """
    Chrome WebDriver indítása. Headless módban is tud futni (látható UI nélkül).
    A webdriver_manager letölti/kezeli az illesztőprogramot.
    """
    chrome_opts = webdriver.ChromeOptions()
    if headless:
        chrome_opts.add_argument("--headless=new")   # stabilabb headless Chrome
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_opts)
    return driver


# ---- 2) Opcionális: sütibanner elfogadása -----------------------------------
def accept_cookies_if_present(driver: webdriver.Chrome) -> bool:
    """
    Több tipikus gomb/szöveg alapján megpróbálja elfogadni a cookie bannert.
    Ha nem talál semmit, csendben továbblép.
    """
    candidates: List[Tuple[By, str]] = [
        (By.CSS_SELECTOR, "button#onetrust-accept-btn-handler"),
        (By.CSS_SELECTOR, "button[aria-label*='Elfogad']"),
        (By.XPATH, "//button[contains(.,'Elfogad') or contains(.,'OK') or contains(.,'Rendben')]"),
        (By.XPATH, "//a[contains(.,'Elfogad') or contains(.,'Rendben')]"),
    ]
    for by, sel in candidates:
        try:
            btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((by, sel)))
            btn.click()
            return True
        except Exception:
            continue
    return False



# ---- 3) "item last" li elemek szövegkinyerése -------------------------------
def extract_li_item_last(driver: webdriver.Chrome, timeout: int = 8) -> list[str]:
    """
    Az összes <li> HTML elemet kigyűjti, amelynek CSS osztálya 'item last'.
    Ezeknek a .text értékét adja vissza listában.
    """
    try:
        # Megvárjuk, amíg legalább egy ilyen elem megjelenik
        els = WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.item.last"))
        )
        # Szövegek kigyűjtése, üresek kiszűrése
        #texts = [el.text.strip() for el in els if el.text.strip()]

        results: List[Dict[str, str]] = []
        for li in els:
                name = ""
                try:
                    # A li-n BELÜL keressük a h3.product-name -> a -> span láncot
                    span = li.find_element(
                        By.XPATH,
                        ".//h3[contains(concat(' ', normalize-space(@class), ' '), ' product-name ')]"
                        "//a//span[normalize-space()]"
                    )
                    name = span.text.strip()

                except Exception:
                    # Ha ebben a li-ben nincs ilyen szerkezet, lépünk a következőre
                    pass

                # --- Attribútum lista ---
                attributes = ""
                try:
                    ul = li.find_element(
                        By.XPATH,
                        ".//ul[contains(concat(' ', normalize-space(@class), ' '), ' product-attribute-list ')]"
                    )
                    li_items = ul.find_elements(By.TAG_NAME, "li")
                    texts = [x.text.strip() for x in li_items if x.text.strip()]
                    attributes = ", ".join(texts)
                except Exception:
                    pass

                        # --- Ár (price-box -> span.price-including-tax) ---
                price = ""
                try:
                    price_span = li.find_element(
                        By.XPATH,
                        ".//div[contains(concat(' ', normalize-space(@class), ' '), ' price-box ')]"
                        "//span[contains(concat(' ', normalize-space(@class), ' '), ' price-including-tax ')]"
                    )
                    price = price_span.text.strip()
                except Exception:
                    pass

                if name or attributes:
                    results.append({
                        "name": name,
                        "attributes": attributes,
                        "price": price
                    })

        return results
    
    except Exception:
        return []


# ---- 4) Fő folyamat ---------------------------------------------------------
def get_text_from_page(url: str, headless: bool = True) -> list[str]:
    """
    Betölti az oldalt, elfogadja a sütiket (ha vannak), majd kigyűjti a
    <li class="item last"> elemek szövegét.
    """
    driver = build_driver(headless=headless)
    try:
        driver.get(url)
        accept_cookies_if_present(driver)

        return extract_li_item_last(driver)
    finally:
        driver.quit()



# ---- 5) CLI -----------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="Egyszerű Selenium szövegkinyerés több szelektorral.")
    p.add_argument("--url", required=True, help="Az oldal URL-je, ahonnan szöveget szeretnél kinyerni.")
    p.add_argument("--headless", action="store_true", help="Headless futtatás (látható UI nélkül).")
    p.add_argument(
        "--selector",
        action="append",
        default=[],
        help="Szelektor (többször is megadható). Prefixeld 'css:' vagy 'xpath:'-szal. Példa: --selector \"css:h1\"",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    #text = get_text_from_page(args.url, args.selector, headless=args.headless)
    products = get_text_from_page(args.url, headless=args.headless)



    # Kimeneti mappa
    out_dir = Path("output_laptophu")
    out_dir.mkdir(parents=True, exist_ok=True)

    # DataFrame létrehozása
    df = pd.DataFrame(products)

    # Excel fájl mentése
    excel_path = out_dir / "products.xlsx"
    df.to_excel(excel_path, index=False)

    print(f"Mentve ide: {excel_path}")


    print("\n=== EREDMÉNY ===")
    if products:
        print(products)
    else:
        print("Nem találtam szöveget a megadott szelektorokkal.")

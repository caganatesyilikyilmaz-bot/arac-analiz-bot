import re
import json

def get_listing_data(url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        html = r.text
        soup = BeautifulSoup(html, "html.parser")

        # 1️⃣ Başlık
        title = "İlan"
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

        # 2️⃣ Fiyat – yöntem 1
        price = None
        price_tag = soup.find("span", class_=re.compile("classified-price"))
        if price_tag:
            price_text = price_tag.get_text()
            price = int(re.sub(r"[^\d]", "", price_text))

        # 3️⃣ Fiyat – yöntem 2 (data-price)
        if price is None:
            data_price = soup.find(attrs={"data-price": True})
            if data_price:
                price = int(data_price["data-price"])

        # 4️⃣ Fiyat – yöntem 3 (JSON içinden)
        if price is None:
            match = re.search(r'"price"\s*:\s*(\d+)', html)
            if match:
                price = int(match.group(1))

        if price is None:
            return None, None

        return title, price

    except Exception:
        return None, None

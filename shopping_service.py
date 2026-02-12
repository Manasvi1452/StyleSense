import requests
import os
import re
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")


def match_products(structured_queries, budget_limit, gender):

    categorized_products = {
        "CLOTHING": [],
        "FOOTWEAR": [],
        "JEWELLERY": [],
        "ACCESSORY": []
    }

    gender_term = "women" if gender.lower() == "female" else "men"

    fallback_terms = {
        "CLOTHING": ["outfit", "apparel"],
        "FOOTWEAR": ["shoes", "sandals", "sneakers", "heels", "loafers"],
        "JEWELLERY": ["jewellery", "accessories"],
        "ACCESSORY": ["fashion accessory", "handbag", "watch"]
    }

    def fetch_shopping_results(search_query):
        params = {
            "engine": "google_shopping",
            "q": search_query,
            "api_key": SERPAPI_KEY,
            "gl": "in",
            "hl": "en",
            "currency": "INR"
        }

        try:
            response = requests.get(
                "https://serpapi.com/search.json",
                params=params,
                timeout=10
            )
            data = response.json()
        except Exception:
            return []

        return data.get("shopping_results", [])

    for category, query in structured_queries.items():

        if category not in categorized_products:
            continue

        # 🔥 CLEAN AI PRICE TEXT
        query = re.sub(r"\(.*?\)", "", query).strip()

        queries_to_try = [f"{query} {gender_term} under {budget_limit} INR"]
        for term in fallback_terms.get(category, []):
            queries_to_try.append(f"{term} {gender_term} under {budget_limit} INR")

        seen_links = set()
        collected = 0

        for search_query in queries_to_try:
            if collected >= 4:
                break

            results = fetch_shopping_results(search_query)
            if not results:
                continue

            for item in results:
                if collected >= 4:
                    break

                link = item.get("product_link") or item.get("link")
                if not link or link in seen_links:
                    continue

                seen_links.add(link)
                product = {
                    "name": item.get("title"),
                    "brand": item.get("source"),
                    "price": item.get("price"),
                    "image": item.get("thumbnail"),
                    "link": link
                }

                categorized_products[category].append(product)
                collected += 1

    return categorized_products

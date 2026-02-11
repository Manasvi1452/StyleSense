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

    for category, query in structured_queries.items():

        if category not in categorized_products:
            continue

        # 🔥 CLEAN AI PRICE TEXT
        query = re.sub(r"\(.*?\)", "", query).strip()

        search_query = f"{query} {gender_term} under {budget_limit} INR"

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
        except:
            continue

        if "shopping_results" not in data:
            continue

        for item in data["shopping_results"][:4]:

            link = item.get("product_link") or item.get("link")
            if not link:
                continue

            product = {
                "name": item.get("title"),
                "brand": item.get("source"),
                "price": item.get("price"),
                "image": item.get("thumbnail"),
                "link": link
            }

            categorized_products[category].append(product)

    return categorized_products

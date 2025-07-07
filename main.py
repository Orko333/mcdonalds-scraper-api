import json
from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any, Union
app = FastAPI(
    title="API",
    description="API to access scraped data from the McDonald's.",
    version="1.0.0",
)
DATA_FILE = "mcdonalds_data.json"
products_db: Dict[str, Dict[str, Any]] = {}

def normalize_name(name: str) -> str:
    """Creates a URL-friendly, lowercase key from a product name."""
    return name.lower().replace(" ", "_").replace("®", "")

def load_data():
    """
    Loads product data from the JSON file into the in-memory `products_db`.
    This function is called once on application startup.
    """
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            products_list: List[Dict[str, Any]] = json.load(f)
            for product in products_list:
                if product.get("name"):
                    key = normalize_name(product["name"])
                    products_db[key] = product
        print(f"INFO:     Successfully loaded {len(products_db)} products from {DATA_FILE}")
    except FileNotFoundError:
        print(f"WARNING:  Data file '{DATA_FILE}' not found. API endpoints will not have data.")
    except json.JSONDecodeError:
        print(f"ERROR:    Could not parse '{DATA_FILE}'. The file may be corrupted.")

load_data()

@app.get(
    "/all_products/",
    summary="Get All Products",
    response_model=List[Dict[str, Any]]
)
async def get_all_products():
    """
    Returns a complete list of all products with their nutritional information.
    """
    if not products_db:
        raise HTTPException(
            status_code=404,
            detail="Product data is not available. Please ensure the data file is present and correct."
        )
    return list(products_db.values())


@app.get(
    "/products/{product_name}",
    summary="Get a Specific Product by Name",
    response_model=Dict[str, Any]
)
async def get_product_by_name(product_name: str):
    """
    Returns all available information for a single product.

    The `product_name` is case-insensitive and spaces can be replaced with underscores.
    Example: `big_mac` or `Big Mac`.
    """
    key = normalize_name(product_name)
    product = products_db.get(key)

    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Product '{product_name}' not found."
        )
    return product


@app.get(
    "/products/{product_name}/{product_field}",
    summary="Get a Specific Field for a Product",
    response_model=Dict[str, Union[str, int, float, None]]
)
async def get_product_field(product_name: str, product_field: str):
    """
    Returns the value of a specific field (e.g., `calories`, `proteins`) for a given product.
    """
    key = normalize_name(product_name)
    product = products_db.get(key)

    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Product '{product_name}' not found."
        )

    if product_field not in product:
        valid_fields = list(product.keys())
        raise HTTPException(
            status_code=404,
            detail=f"Field '{product_field}' not found for product '{product_name}'. Valid fields are: {valid_fields}"
        )

    return {
        "product": product.get("name"),
        "field": product_field,
        "value": product.get(product_field)
    }

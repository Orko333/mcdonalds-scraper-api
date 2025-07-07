# McDonald's Menu Scraper & API

## Setup & Installation

Follow these steps to set up the project locally.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Orko333/mcdonalds-scraper-api.git
    cd mcdonalds-scraper-api
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    venv\Scripts\activate
    ```

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Playwright's browser dependencies:**
    (This is a one-time setup for Playwright)
    ```bash
    playwright install
    ```

## Usage

The project has two main components: the scraper and the API.

### 1. Run the Scraper

To collect the data from the website, run the scraper script. This will create a `mcdonalds_data.json` file in the project directory.

```bash
python scraper.py
```

### 2. Run the API Server


```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`. You can access the interactive documentation (Swagger UI) at `http://127.0.0.1:8000/docs`.

## API Endpoints

The API provides the following endpoints:

#### `GET /all_products/`
Returns a list of all products with their complete information.

#### `GET /products/{product_name}`
Returns all available information for a single product.

#### `GET /products/{product_name}/{product_field}`
Returns a specific field for a given product.

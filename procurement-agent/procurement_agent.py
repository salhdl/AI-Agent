# procurement_agent.py
# -*- coding: utf-8 -*-

import os
import re
import ast
import csv
import tempfile
from textwrap import dedent
from typing import Iterator

from dotenv import load_dotenv
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import uvicorn

from agno.workflow import Workflow
from agno.agent import Agent, RunResponse
from agno.models.google import Gemini
from agno.tools.python import PythonTools
from agno.utils.pprint import pprint_run_response


# -----------------------------------------------------------------------------
# Environnement
# -----------------------------------------------------------------------------
load_dotenv()
EXA_API_KEY = os.environ.get("EXA_API_KEY")


# -----------------------------------------------------------------------------
# Fonction EXA (OpenAI-compatible) — plus d'appel à exa.research.create_task
# -----------------------------------------------------------------------------
def exa_search(product_list: str, location: str) -> str:
    """
    Utilise l'API Chat OpenAI-compatible d'Exa (model='exa-research') pour
    réaliser la recherche d'achats/approvisionnements et renvoyer un Markdown.
    """
    if not EXA_API_KEY:
        raise RuntimeError("Missing EXA_API_KEY in environment (.env)")

    # Import local pour éviter de forcer la dépendance quand non utilisé.
    from openai import OpenAI

    client = OpenAI(
        base_url="https://api.exa.ai",
        api_key=EXA_API_KEY,
    )

    user_prompt = f"""
You are an expert in business procurement research. Your task is to find the best vendors and prices for the following products:

- Product List: {product_list}
- Location: {location}

Return the results in clean, structured markdown. For each product, list the top 3 vendors with:
- Vendor Name
- Product Title
- Price (in local currency)
- Vendor Website or Purchase Link
- Short Description
- Minimum Order Quantity (if available)
- Shipping Time (if available)
- Known Bulk Discounts or Deals (if available)

Organize the output clearly for comparison.
""".strip()

    stream = client.chat.completions.create(
        model="exa-research",
        messages=[{"role": "user", "content": user_prompt}],
        stream=True,
    )

    chunks: list[str] = []
    for chunk in stream:
        # Défense : certains chunks peuvent ne pas contenir de delta.content
        choice = chunk.choices[0]
        delta = getattr(choice, "delta", None)
        if delta and getattr(delta, "content", None):
            chunks.append(delta.content)

    result = "".join(chunks)
    print("----------------------------- EXA SEARCH COMPLETION -----------------------------")
    print(result)
    print("--------------------------------------------------------------------------------")
    return result


# -----------------------------------------------------------------------------
# Workflow / Agent (Agno)
# -----------------------------------------------------------------------------
class ProcurementAgent(Workflow):
    procurement_agent: Agent = Agent(
        name="Procurement Agent",
        model=Gemini(id="gemini-2.0-flash"),
        instructions=dedent("""
        You are a procurement analysis agent.

        Your goal is to:
        1. Parse the markdown-formatted research output from Exa.
        2. For each product listed, extract the following fields for each vendor:
            - Product Name
            - Vendor Name
            - Product Title
            - Price (convert to numeric if possible)
            - Currency
            - Vendor Website or Purchase Link
            - Short Product Description
            - Minimum Order Quantity (if available)
            - Shipping Time (if available)
            - Bulk Discounts or Deals (if available)
            - Vendor Location (if mentioned)

        3. After extracting the data, write and execute a Python script that creates a file named `data.csv`
            - Use the standard `csv` module
            - After each product, leave a blank line
            - Make the columns in this order: Product Name, Vendor Name, Product Title, Price, Currency, Bulk Discounts or Deals, Vendor Website, Short Product Description, Minimum Order Quantity, Shipping Time
            - The script should write a header row followed by one row per vendor
            - IMPORTANT: When opening the file, always use encoding='utf-8' in open(), e.g. open('data.csv', 'w', newline='', encoding='utf-8')
            - Then use the PythonTools tool to run the script and save the data
            - Based on the data given, create rows for each data point

        Then:

        4. Analyze the data across all products and vendors.
            - Compare vendors based on pricing, shipping times, minimum quantities, and available deals.
            - Prioritize vendors who:
                - Deliver to the specified location
                - Offer the lowest price for comparable quality
                - Have favorable shipping times or bulk deals
                - Appear reliable (from marketplaces or verified sellers)

        5. Write an executive summary that includes:
            - Recommended vendor(s) per product
            - Reasons for the recommendation (price, location, delivery, etc.)
            - Any noteworthy observations (e.g. big pricing differences, best bundle offers)
            - Optional: Flag any vendors that should be avoided due to missing info or suspicious listings

        IMPORTANT: Use PythonTools to write the extracted data to `data.csv`.
        """),
        expected_output=dedent("""
        The output should include:

        1. 📊 Data Summary:
        - Number of products processed
        - Total vendors compared
        - Location considered for delivery: <city>, <country>
        - Any data quality issues or missing fields (if relevant)

        2. 🏆 Recommendations Per Product:
        For each product (e.g., "Office Chair", "Laptop"), provide:

        ### Product: <Product Name>

        **Recommended Vendor:** <Vendor Business Name>  
        **Price:** <Price and Currency>  
        **Why Chosen:**  
        - Reason 1 (e.g. best price for similar features)
        - Reason 2 (e.g. fastest shipping)
        - Reason 3 (e.g. known/verified vendor or bulk deal)

        **Runner-Up:** <Vendor Business Name>  
        - Mention if relevant (e.g. slightly higher price but faster delivery or better reviews)

        IMPORTANT: Confirm that the CSV file was written as part of this run.
        """),
        tools=[PythonTools()],
        show_tool_calls=True,
        markdown=True,
    )

    def run(self, product_list: str, location: str):
        # 1) Fait la recherche via EXA (markdown)
        research_response = exa_search(product_list, location)
        # 2) Envoie le markdown à l'agent d'analyse
        yield from self.procurement_agent.run(research_response, stream=True)


# -----------------------------------------------------------------------------
# FastAPI
# -----------------------------------------------------------------------------
app = FastAPI(title="Procurement Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ajuste si besoin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/procure")
async def procure(product_list: str = Form(...), location: str = Form(...)):
    """
    Lance le workflow d'approvisionnement et renvoie :
    - le markdown agrégé de l'agent
    - un indicateur de présence du CSV (data.csv)
    """
    workflow = ProcurementAgent()
    response: Iterator[RunResponse] = workflow.run(
        product_list=product_list, location=location
    )

    # Concaténer la sortie streamée en Markdown
    markdown_output = ""
    for chunk in response:
        # Agno peut streamer des objets RunResponse ou des str
        if hasattr(chunk, "content") and chunk.content:
            markdown_output += chunk.content
        elif isinstance(chunk, str):
            markdown_output += chunk

    # --- Post-traitement optionnel pour réécrire proprement le CSV ---
    # Cherche un bloc "data = [ ... ]" et réécrit data.csv avec un DictWriter.
    try:
        match = re.search(r"data\s*=\s*(\[.*?\])", markdown_output, re.DOTALL)
        if match:
            data_str = match.group(1)
            data_list = ast.literal_eval(data_str)  # safe parse de liste/dicts

            fieldnames = [
                "Product Name",
                "Vendor Name",
                "Product Title",
                "Price",
                "Currency",
                "Bulk Discounts or Deals",
                "Vendor Website",
                "Short Product Description",
                "Minimum Order Quantity",
                "Shipping Time",
            ]

            with open("data.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for row in data_list:
                    if isinstance(row, dict):
                        writer.writerow(row)

    except (ValueError, SyntaxError) as e:
        # Si l'agent n'a pas produit un bloc data exploitable, on garde le CSV tel quel (si l'agent l'a généré via PythonTools).
        print(f"Warning: Could not parse and rewrite CSV from agent output. {e}")
    # --- Fin post-traitement ---

    csv_exists = os.path.exists("data.csv")
    return JSONResponse({"markdown": markdown_output, "csv_available": csv_exists})


@app.get("/csv")
def get_csv():
    """
    Sert le fichier CSV généré par l'agent (data.csv)
    """
    csv_path = "data.csv"
    if os.path.exists(csv_path):
        return FileResponse(csv_path, media_type="text/csv", filename="data.csv")
    return JSONResponse({"error": "CSV not found"}, status_code=404)


# -----------------------------------------------------------------------------
# Entrée CLI
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Mode CLI (invite l'utilisateur), OU lance le serveur si variables présentes
    import sys
    from rich.prompt import Prompt

    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        # Lancer serveur FastAPI : python procurement_agent.py serve
        # Puis: uvicorn procurement_agent:app --reload   (ou ci-dessous)
        uvicorn.run("procurement_agent:app", host="0.0.0.0", port=8000, reload=True)
    else:
        # Mode interactif terminal
        try:
            products = Prompt.ask("Enter your products list separated by commas")
            loc = Prompt.ask("Enter your business location (city, country)")
            if products and loc:
                workflow = ProcurementAgent()
                resp: Iterator[RunResponse] = workflow.run(
                    product_list=products, location=loc
                )
                pprint_run_response(resp, markdown=True)
            else:
                print("Products and location are required.")
        except KeyboardInterrupt:
            print("\nCancelled by user.")

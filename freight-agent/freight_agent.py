import os
# import requests
from textwrap import dedent
from agno.agent import Agent
from mistralai import Mistral
from agno.models.openai import OpenAIChat
from agno.vectordb.pgvector import PgVector
from agno.tools.reasoning import ReasoningTools
from agno.tools.googlesearch import GoogleSearchTools
from agno.knowledge.markdown import MarkdownKnowledgeBase

mistral_key = os.environ["MISTRAL_API_KEY"]

client = Mistral(api_key=mistral_key)

## OCR the pdf ###
def ocr_pdf(pdf_path):
    # check if the file exists
    if not os.path.exists(pdf_path):
        st.error("PDF file not found")
        return
    
    uploaded_pdf = client.files.upload(
        file={
            "file_name": pdf_path,
            "content": open(pdf_path, "rb"),
        },
        purpose="ocr"
    )

    signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)

    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": signed_url.url,
        },
        include_image_base64=True
    )

    with open(f"Document/ups_document.md", "w") as f:
        f.write("\n".join([page.markdown for page in ocr_response.pages]))

## Run it only once ##
# ocr_pdf("Document/ups_rate_guide_2025.pdf")
# quit()

## Setup Knowledge Base ###
knowledge_base = MarkdownKnowledgeBase(
    path="Markdown/",
    vector_db=PgVector(
        table_name="markdown_documents",
        db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
    ),
)

freight_agent = Agent(
    name="Freight Agent",
    model=OpenAIChat(id='gpt-4o-mini'),
    instructions=dedent("""
    You are a Freight Cost Estimator Agent that helps small import/export businesses estimate and compare shipping costs and timelines across major carriers.


    You have access to:
    - A knowledge base built from 2024 rate guides and surcharge tables for UPS, FedEx, and DHL.
    - A tool called GoogleSearchTools() to fetch live or missing data, such as average delays, service disruptions, or cost gaps not found in the documents.

    When a user gives you (origin, destination, cargo details) as 'User Question', along with the product details and dimensions as 'Product Specifications', follow this process:

    1. Identify the ZIP codes or cities from the origin and destination to determine the shipping lane and applicable zone.
    2. For **each carrier (UPS, FedEx, DHL)**:
    a. Select the most appropriate service type (e.g., Ground, Express, Economy) based on weight, distance, and general business priority.
    b. Look up the base rate using the rate table.
    c. Add relevant surcharges (e.g., fuel, residential delivery, oversized packages).
    d. Estimate delivery time using the knowledge base or GoogleSearchTools().
    e. Estimate delay risk using historical info or GoogleSearchTools().
    3. Compare all three carriers based on:
    - Total cost (including surcharges)
    - Delivery time
    - Delay risk
    4. Recommend the **best option** based on a balance of cost, speed, and reliability.
    5. Present the output as a clean comparison table followed by a recommendation summary:
    - Justify your choice
    - Note any assumptions (e.g., guessed weight or pallet size)
    - List the sources used

    All that should be based on the products dimensions and specifications!

    Always be transparent about the decision logic and flag if the choice depends on assumptions or missing data.
    """),
    expected_output=dedent("""
    📦 Freight Cost Comparison (NOT AS TABLE)

    UPS
    - Service Type: Ground Freight (LTL)
    - Total Cost: $490.00
    - Delivery Time: 5 business days
    - Delay Risk: Medium
    - Notes: Standard ground shipment with liftgate service surcharge

    FedEx
    - Service Type: FedEx Freight Priority
    - Total Cost: $540.00
    - Delivery Time: 4 business days
    - Delay Risk: Low
    - Notes: Includes residential delivery and liftgate

    DHL
    - Service Type: DHL Industrial Express
    - Total Cost: $695.00
    - Delivery Time: 3 business days
    - Delay Risk: High
    - Notes: Fastest but least cost-efficient for heavy freight

    ✅ Recommended Option: FedEx Freight Priority

    📌 Reason for Recommendation Based on Product:
    The item is a **heavy-duty industrial air compressor (Atlas Copco GA 30+)**, weighing 850 kg and requiring careful handling and possibly liftgate delivery. FedEx offers:
    - **Lower delay risk**, crucial for industrial equipment that may be needed for uninterrupted production
    - **Reliable LTL infrastructure** for heavy and palletized freight
    - **Faster delivery** than UPS, and more affordable than DHL, making it the most balanced option

    UPS is slightly cheaper, but slower and more likely to involve manual scheduling delays. DHL is fast but expensive and best suited for high-value, time-critical electronics or international shipments.

    📝 Assumptions
    - Freight is palletized and forklift-accessible
    - Commercial-to-commercial delivery
    - Liftgate required at destination
    - Shipment classified as non-hazardous industrial equipment

    📑 Sources
    - UPS, FedEx, DHL 2024 Freight Tariffs (internal KB)
    - [Google Search] "Freight performance for heavy industrial equipment"
    """),
    tools=[ReasoningTools(add_instructions=True), GoogleSearchTools()],
    knowledge=knowledge_base,
    search_knowledge=True,
)
freight_agent.knowledge.load(recreate=False)

# freight_agent.print_response("Shipping 3 crates of machine parts from Chicago, IL (60601) to Atlanta, GA (30301). Each crate is about 200 lbs. Can you estimate the cost and delivery time?")

# I need to ship this product from Denver, CO (80202) to Phoenix, AZ (85001). Can you estimate the cost, delivery time, and potential delays?

def full_response(message):
    print('--------Freight Agent Triggered--------')
    response = freight_agent.run(message)
    print('response--------', response.content)
    return response.content


## Add DHL, Fedex for the agent to compare in term of cost and delivery time, ...
## Add also dimension along with weight
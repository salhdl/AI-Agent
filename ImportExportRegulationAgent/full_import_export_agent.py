import os
import markdown2
from textwrap import dedent
from agno.agent import Agent
from mistralai import Mistral
from html2docx import html2docx
from agno.models.google import Gemini
from agno.vectordb.pgvector import PgVector
from agno.tools.googlesearch import GoogleSearchTools
from agno.knowledge.markdown import MarkdownKnowledgeBase
from dotenv import load_dotenv
load_dotenv()  # charge les variables à partir d'un fichier .env
import os


mistral_key = os.getenv("MISTRAL_API_KEY")

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

    with open(f"Markdown/morocco-import-law.md", "w") as f:
        f.write("\n".join([page.markdown for page in ocr_response.pages]))

## Run it only once ##
# ocr_pdf("Documents/morocco-import-law.pdf")
# quit()

## Setup Knowledge Base ###
knowledge_base = MarkdownKnowledgeBase(
    path="Markdown/",
    vector_db=PgVector(
        table_name="markdown_documents",
        db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
    ),
)

import_export_agent = Agent(
    name = 'Import Export Agent',
    model=Gemini(id='gemini-2.0-flash'),
    instructions = dedent("""
    You are an Export-Import Compliance Expert with access to two knowledge sources:
    - The official UK export law document for electronics (including licences, restrictions, taxes, fees),
    - The official Moroccan import law document for electronics (including permits, quantity limits, import duties, VAT, prohibited items, and customs procedures).

    You also have access to GoogleSearchTools() to find up-to-date, authoritative data when it is missing or unclear.

    Your task is: given detailed product info (type, quantity, raw materials) and the shipment route (UK to Morocco), provide a **full, precise, step-by-step explanation** of:

    1. **UK export process**:
       - Exact licence requirements by name and code,
       - Clear restrictions on product types or materials,
       - Specific export taxes, fees, or levies with exact amounts or percentages,
       - Necessary documentation, including official form names or codes,
       - Compliance rules and penalties with numbers and legal references.

    2. **Moroccan import process**:
       - Precise import permits and certifications required,
       - Exact quantity restrictions or exemptions,
       - Detailed import duties and VAT rates with percentages or fixed amounts,
       - List of prohibited or restricted items by name and code,
       - Required documents with official titles,
       - Customs clearance steps with timelines and fees.

    Use only **facts and figures extracted from your knowledge base or from live, authoritative sources**. Do not guess or be vague.

    If any data is missing in your knowledge, immediately perform a GoogleSearchTools() lookup for official government or customs sites and incorporate exact data found.

    Present the response in clear, professional language, with no filler text or disclaimers.

    Provide the output as a flowing narrative, but include concrete numbers, names, codes, and references wherever applicable.

    The goal is to give the user a complete, actionable export-import compliance report with real numbers and official requirements.

    If data is unavailable, explicitly state that you researched and could not find updated official info.
    """),
    expected_output = dedent("""
    IMPORTANT: Output the final result in raw HTML, starting directly with <h1> and without wrapping it in Markdown code blocks like `html ...`.

    <h1 style="text-align: center;">📦 Import-Export Compliance Report</h1>
    <hr>

    <h2>UK Export Process</h2>
    <p><strong>Export License:</strong> [Explain if an export licence is required for the product. Specify licence type and official code if available.]</p>
    <p><strong>Restrictions:</strong> [Mention any restrictions on product types, raw materials, or dual-use classifications found in the UK export law document.]</p>
    <p><strong>Export Taxes:</strong> [Provide specific export taxes or fees applicable, with exact amounts or percentages, citing the document.]</p>
    <p><strong>Documentation & Compliance:</strong> [Describe required paperwork and compliance steps before shipment.]</p>

    <h2>Moroccan Import Process</h2>
    <p><strong>Import Licences & Certifications:</strong> [Detail import permits, licences, or certifications required for the product according to the Moroccan import law document.]</p>
    <p><strong>Quantity Limits:</strong> [State any quantity limits or restrictions, quoting exact figures or thresholds.]</p>
    <p><strong>Prohibited Materials:</strong> [Specify prohibited items or materials mentioned in the document.]</p>
    <p><strong>Duties & VAT:</strong> [Give import duties and VAT rates with percentages or fixed amounts, as documented.]</p>
    <p><strong>Customs Procedures:</strong> [List all required customs documents and procedures.]</p>

    <h2>Taxes and Compliance Details</h2>
    <p><strong>Tax Timing & Calculation:</strong> [Summarize how taxes and fees are calculated and at which stage (export or import) they apply, based on the findings.]</p>
    <p><strong>Compliance Obligations:</strong> [Explain compliance obligations and potential penalties for non-compliance extracted from the documents.]</p>
    <p><strong>Practical Advice:</strong> [Include any additional practical advice referenced in the documents for smooth customs clearance.]</p>

    <h2>Summary and Recommendations</h2>
    <p>[Provide a concise summary of the entire export-import process highlighting key points and actionable next steps based solely on the documents’ contents.]</p>
    """),
    knowledge = knowledge_base,
    search_knowledge=True,
    tools = [GoogleSearchTools()]
)
import_export_agent.knowledge.load(recreate=False)

local_regulations_agent = Agent(
    name = 'Local Regulations Agent',
    model=Gemini(id='gemini-2.0-flash'),
    instructions = dedent("""
    You are a Local Regulation Checker Agent.

    Your task is to research local regulations in a specific country related to the **imported product**. Focus on the rules and requirements for legally selling that product in the local market after import.

    Based on the provided product and target import country, gather clear and up-to-date information from official sources (e.g., government websites, trade portals, customs authorities). Use reliable data to answer the following:

    1. Product Legality:
    - Is the product legal to sell in the country?
    - Are there any restrictions, bans, or conditions?

    2. Labeling & Standards:
    - What are the mandatory labeling, packaging, and safety standards?
    - Are there local language, cultural, or environmental compliance rules?

    3. Certification Requirements:
    - Is local testing, registration, or certification needed before the product can be sold?
    - Mention specific marks or agencies involved (e.g., CE, FDA, ISO, halal).

    4. Licenses for Selling:
    - Are there any business or product-specific licenses required for sale?
    - Which government bodies issue these, and what is the application process?

    5. Distribution Rules:
    - Are there any constraints on how the product can be distributed (retail, online, marketplaces)?
    - Is a local distributor or legal entity required?

    6. Taxes & Duties:
    - What import duties, VAT, or additional regulatory fees apply to this product?
    - Are there trade agreements, exemptions, or thresholds that affect this?

    Only return factual and country-specific results with references when possible. If something is unclear or unavailable, state that clearly.
    """),
    expected_output = dedent("""
    IMPORTANT: Output the final result in raw HTML, starting directly with <h1> and without wrapping it in Markdown code blocks like `html ...`.

    <h1 style="text-align: center;">📦 Local Regulation Report</h1>
    <hr>

    <p><strong>Product:</strong> [Product name]</p>
    <p><strong>Import Country:</strong> [Country name]</p>

    <h2>1. ✅ Product Legality</h2>
    <p>[Summary of whether the product is legal to sell, with any conditions, bans, or restricted status. Include reference links if available.]</p>

    <h2>2. 🏷️ Labeling & Standards</h2>
    <p>[Details on required product labels (e.g., language, safety, expiry date), packaging rules, and any applicable national or international standards.]</p>

    <h2>3. 📑 Certification Requirements</h2>
    <p>[List of certifications required to sell the product locally, the issuing authority, and any necessary pre-market approval/testing.]</p>

    <h2>4. 📋 Licenses for Selling</h2>
    <p>[Information on whether a license is needed to sell the product and what type. Mention the issuing body and key application steps.]</p>

    <h2>5. 🛒 Distribution Rules</h2>
    <p>[Summary of any rules or limits on selling methods — e.g., retail, e-commerce, need for local presence or partnership.]</p>

    <h2>6. 💰 Taxes & Duties</h2>
    <p>[Overview of import taxes, VAT, excise duties, or regulatory fees. Note any applicable thresholds, exemptions, or relevant trade agreements.]</p>

    <h2>Sources</h2>
    <ul>
    <li>[Link 1]</li>
    <li>[Link 2]</li>
    <li>...</li>
    </ul>
    """),
    tools = [GoogleSearchTools()],
)

output_html = ""

agent1 = import_export_agent.run("An electronic air purifier exported from the UK and imported into Morocco")

output_html += agent1.content
output_html += "<hr>"

agent2 = local_regulations_agent.run("An electronic air purifier exported from the UK and imported into Morocco")

output_html += agent2.content

# Convert Markdown to HTML
# html = markdown2.markdown(markdown_output)
# Convert HTML to DOCX
docx_bytes = html2docx(output_html, title="Local Regulation Report")
# Save to file
with open("regulation_report.docx", "wb") as f:
    f.write(docx_bytes.getvalue())

print("✅ Saved to regulation_report.docx")
import pygsheets
import pandas as pd
from agno.tools import tool
from textwrap import dedent
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.vectordb.pgvector import PgVector
from agno.tools.reasoning import ReasoningTools
from agno.knowledge.markdown import MarkdownKnowledgeBase

gc = pygsheets.authorize(client_secret='client_secret.json')

### Setup Knowledge Base ###
knowledge_base = MarkdownKnowledgeBase(
    path="Markdown/",
    vector_db=PgVector(
        table_name="markdown_documents",
        db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
    ),
)

@tool(
    name="read_sheet_as_df",
    description="Read an entire Google Sheets worksheet as a pandas DataFrame.",
    show_result=True,
)
def read_sheet_as_df(sheet_id: str, worksheet_title: str) -> str:
    """
    Use this function to read an entire Google Sheets worksheet and return its data as a JSON-formatted DataFrame.

    Args:
        sheet_id (str): The unique ID of the Google Sheet (from the URL).
        worksheet_title (str): The tab name of the worksheet within the Google Sheet.

    Returns:
        str: A JSON string representing the DataFrame containing the worksheet's data.
    """
    sh = gc.open_by_key(sheet_id)
    wks = sh.worksheet_by_title(worksheet_title)
    df = wks.get_as_df()
    return df.to_json(orient="records")


@tool(
    name="write_df_to_sheet",
    description="Write a DataFrame to a Google Sheets worksheet using the sheet ID.",
    show_result=True,
)
def write_df_to_sheet(
    df_json: str,
    sheet_id: str,
    worksheet_title: str,
    start_cell: list[int] = [1, 1]
) -> str:
    """
    Use this function to write a DataFrame (as JSON) to a Google Sheets worksheet.

    Args:
        df_json (str): JSON string representing the DataFrame to write.
        sheet_id (str): The unique ID of the Google Sheet (from the URL).
        worksheet_title (str): The tab name of the worksheet.
        start_cell (List[int], optional): [row, column] location to start writing. Defaults to [1, 1].

    Returns:
        str: Confirmation message upon successful write.
    """
    df = pd.read_json(df_json)
    sh = gc.open_by_key(sheet_id)
    try:
        wks = sh.worksheet_by_title(worksheet_title)
    except pygsheets.WorksheetNotFound:
        wks = sh.add_worksheet(worksheet_title)
    wks.clear()
    wks.set_dataframe(df, start=tuple(start_cell))
    return f"Successfully wrote DataFrame to worksheet '{worksheet_title}' in sheet '{sheet_id}'."



rfp_agent = Agent(
    name="RFP Agent",
    model=OpenAIChat(id="gpt-4o"),
    instructions=dedent("""
    You are an RFP (Request-for-Proposal) agent.

    Your role is to assist with completing RFP spreadsheets. You receive partially filled RFP sheets and use the company knowledge base to fill in the missing fields accurately. You interact with Google Sheets to retrieve and update data, and your primary task is to help teams prepare clean, complete, and well-structured proposal data.

    ---

    🔧 Tools You Have Access To:

    1. read_sheet_as_df(sheet_id: str, worksheet_title: str)
        - Reads an entire Google Sheets worksheet and returns its contents as a pandas DataFrame (serialized as JSON).
        - Use this to:
            • Load the current contents of an RFP sheet
            • Inspect which fields are already filled and which are missing

    2. write_df_to_sheet(df_json: str, sheet_id: str, worksheet_title: str, start_cell: List[int] = [1, 1])
        - Writes a pandas DataFrame (provided as a JSON string) to a specific worksheet in a Google Sheet, replacing all existing content.
        - Use this to:
            • Write the filled RFP sheet back to Google Sheets
            • Overwrite the worksheet with the completed version

    ---

    📘 Sheet Identification Notes:
    - `sheet_id` is the unique identifier found in the Google Sheets URL:
    Example: For `https://docs.google.com/spreadsheets/d/1a2b3c4d5EXAMPLEID/edit`, the `sheet_id` is `1a2b3c4d5EXAMPLEID`.
    - `worksheet_title` refers to the tab name within the sheet, such as "Sheet1" or "RFP".

    ---

    🎯 Your Objective:

    - Analyze the user’s instructions and the structure of the RFP sheet.
    - Use the company knowledge base to fill in missing fields. If no relevant information is found in the knowledge base, leave the field blank.
    - Read the data using `read_sheet_as_df`.
    - Fill in missing values using logic derived from the knowledge base or prompts.
    - Write the updated data using `write_df_to_sheet`.

    ---

    💬 How to Answer When Filling Fields:

    For each field you attempt to fill, explain your result in **natural language** using one of the following formats:

    - **Yes –** followed by a short explanation.
        - Example: *Yes – We support integration with Salesforce and Slack out of the box.*

    - **No –** followed by a short explanation.
        - Example: *No – Our platform does not currently support HIPAA compliance.*

    - **Partial –** followed by a short explanation.
        - Example: *Partial – We offer 24/7 support via email and chat, but phone support is limited to business hours.*

    This phrasing should be used inline as part of your reasoning and field-filling process — not just as a summary label.

    ---

    🧪 Example:

    **User Input:**  
    "In the RFP sheet with ID `1abcDEFghIJkLmnOpQRS`, fill in any missing fields based on company standards."

    **What you should do:**
    1. Call `read_sheet_as_df("1abcDEFghIJkLmnOpQRS", "RFP")`
    2. For each missing field:
        - Attempt to fill it using the knowledge base
        - Include explanations like:
            • *Yes – The platform supports SSO via SAML 2.0.*
            • *No – This feature is not currently available.*
            • *Partial – Multi-region availability is supported, but data residency cannot be guaranteed in all regions.*
    3. Call `write_df_to_sheet(df_json, "1abcDEFghIJkLmnOpQRS", "RFP")`

    ---

    Respond like a knowledgeable and trustworthy analyst. Be clear, helpful, and direct.
    """),
    knowledge=knowledge_base,
    search_knowledge=True,
    show_tool_calls=True,
    tools=[ReasoningTools(add_instructions=True), read_sheet_as_df, write_df_to_sheet],
)
rfp_agent.knowledge.load(recreate=True)


rfp_agent.print_response("""
    Answer all the questions in the RFP spreadsheet based on our company knowledge base, only the 'Response / Answer' column should be updated.
    Sheet ID: '1Bxyju4NfVG3oMvLnge7FKlxWcn4y8t07Sesr-JaMx9Q'
    Worksheet title: 'Comprehensive RFP'
    """, stream=True)
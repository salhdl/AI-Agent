from agno.agent import Agent
from agno.team.team import Team
from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
from agno.tools.scrapegraph import ScrapeGraphTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.file import FileTools
from agno.tools.yfinance import YFinanceTools
from agno.tools.exa import ExaTools

from agno.tools.file import FileTools

from dotenv import load_dotenv
import os

load_dotenv()

id=os.getenv("id")
api_key=os.getenv("api_key")
id_openai=os.getenv("id_openai")
api_key_openai=os.getenv("api_key_openai")
exa_key = os.getenv("EXA_API_KEY")

# agent capable of searching internally for the client
internal_search = Agent(
    name="internal search agent",
    model=Gemini(id=id, api_key=api_key),
    #model=OpenAIChat(id=id_openai, api_key=api_key_openai),
    tools=[FileTools()],
    description="""
    A data analyst agent that retrieves and summarizes historical client meeting records 
    from the internal database ('Data/data.json').
    The agent provides concise, insight-driven summaries based on each meeting entry.
    """,
    instructions="""
    You are given access to a JSON file containing client information, including detailed meeting notes.

    Your task is to:
    1. Search for the specified client by full name in the 'Data/data.json' file.
    2. If the client is found, focus on the 'meeting_notes' field.
    3. For each note, write a **professional, well-structured summary, and actions** using markdown bullet format like this:
       # Internal Search:
       - <Date>: Summary
       - **Action Items**: 

    Notes:
    - Summarize clearly; do not just copy/paste raw content.
    - Group related ideas. Be concise but informative.
    - Ensure the tone is suitable for executive review.

    Final response must be:
    - Well-structured using Markdown
    - Professional in tone
    - Only include one of the two sections depending on the results.
    

    

    If the client is not found, respond exactly with: CLIENT NOT FOUND.
    """,

    stream=True
)

#internal_search.print_response("give me info about Manuel Dupant", markdown=True)



# agent capable of searching in the web for the client
web_search = Agent(
    name="web search agent",
    model=Gemini(id=id, api_key=api_key),
    #model=OpenAIChat(id=id_openai, api_key=api_key_openai),

    tools=[ScrapeGraphTools(markdownify=True), ExaTools(), ],
    description="""
    A web intelligence agent activated only when a client is not found in the internal records.
    It searches the web to uncover publicly available, up-to-date information about the client,
    focusing on professional activity and recent public appearances.
    """,
    instructions="""
    ⚠️ Only respond if the internal search agent confirms: "CLIENT NOT FOUND".

    Step 1: Use DuckDuckGoTools to search the web for the client's full name.
    Step 2: Identify relevant links such as:
    - Personal websites
    - LinkedIn, GitHub, or other professional profiles
    - News articles or blog posts
    - Conference appearances, guest speaking events, or publications

    Step 3: Use ScrapeGraphTools to scrape **only the most relevant and recent pages**.
    Step 4: Summarize any recent or notable findings into a **clear, executive-level markdown summary**.

    Formatting guidelines:
    - Use bullet points per finding.
    - Each point should include a concise description of the event, post, or appearance.
    - Keep it factual, neutral, and informative — suitable for a professional briefing.
    - If no relevant information is found, respond with: "No public information found."

    
    """,
    show_tool_calls=True,
    stream=True,
)

# web_search.print_response("search for Manuel Dupant", stream=True, markdown=True)



# Team manager that coordinates between the first two ones
client_research = Team(
    name="Client Research Agent",
    model=Gemini(id=id, api_key=api_key),
    #model=OpenAIChat(id=id_openai, api_key=api_key_openai),
    members=[internal_search, web_search],
    # mode="coordinate",
    tools=[],
    description="""
    A high-level research agent that coordinates two specialized sub-agents:
    - An internal search agent that queries local client records.
    - A web search agent that performs external research if internal data is missing.

    This agent orchestrates both and produces a professional, structured summary about the client.
    """,
    instructions="""
    Your goal is to gather insights about a client using two research sources:

    1. First, delegate the task to the **internal search agent** to locate any existing internal meeting records about the client.
    2. If the internal agent returns information, format it under the section titled:
       # Internal Search:
       - Date: Summary
       - **Action Items**: if any

    3. If the internal agent replies "CLIENT NOT FOUND", delegate the task to the **web search agent**.
    4. If the web search agent returns anything, format it under the section:
       # Web Search:
       - Summarized bullet points from recent or relevant online content

    Final response must be:
    - Well-structured using Markdown
    - Professional in tone
    - Only include one of the two sections depending on the results.
    

    """,
    stream=True,
    
    show_members_responses=True,
)



client_research.print_response("I'm Manuel Dupant, I'm a software engineer, do you have any info about me? ", stream=True, markdown=True)


# getting data on a specific stock
Financial_data_agent = Agent(
    name="Financial Intelligence Agent",
    model=Gemini(id=id, api_key=api_key),
    tools=[
        YFinanceTools(
            stock_price=True,
            company_info=True,
            stock_fundamentals=True,
            key_financial_ratios=True,
            analyst_recommendations=True,
        ),
        FileTools(),
        ExaTools(),
        ScrapeGraphTools(markdownify=True),
    ],

    description="""
    A financial analysis expert agent responsible for researching specific investment opportunities based on client context.
    This agent can extract financial data, summarize earnings calls, and provide balanced investment recommendations.

    It uses insights from the client's research and combines them with real-time financial data 
    and qualitative sources to support decision-making.

    By the end, save the final output in a ('financial_data.md') file.
    """,

    instructions="""
    You are a financial analyst agent tasked with evaluating a stock as an investment opportunity. Your output must strictly follow the structure outlined below.

    Start by understanding the client's investment preferences, goals, and risk tolerance. Tailor your recommendations to align with that profile.

    End by Saving the output in a file called 'financial_data.md'.

    ---
    Analyze [Stock Name] as an investment opportunity using this exact structure:

    ---
    **[Stock Name] Overview**  
    [1–2 sentences summarizing the company’s core business and differentiation.]

    **Pros of Investing in [Stock Name]**  
    - **Innovative Technology**: [Detail unique tech/advantages, if applicable.]  
    - **Strategic Partnerships**: [List key partnerships/alliances.]  
    - **Market Demand**: [Highlight growth sectors/tailwinds.]  
    - **Regulatory Support**: [Mention favorable policies/risks.]  
    - **Revenue Potential**: [Identify high-margin segments or opportunities.]

    **Cons of Investing in [Stock Name]**  
    - **Regulatory Challenges**: [Permitting delays/policy risks.]  
    - **Financial Health**: [Losses/debt/cash burn concerns.]  
    - **Market Risks**: [Supply chain/competition/volatility.]  
    - **Execution Risks**: [Management hurdles/operational uncertainties.]

    **Overall**, [Stock Name] presents [summary of opportunity], but investors should weigh [key risks].

    ---

    Use the following data sources to inform your analysis (in priority order):
    1. Latest earnings calls (Q2–Q3 2024).
    2. SEC filings (10-K/10-Q).
    3. Analyst reports (e.g., Bloomberg, Reuters).
    4. Industry trends related to the company (e.g., AI, energy transition, EV, etc.).
    5. Financial metrics using YFinance (stock fundamentals, key ratios, analyst recommendations).

    📌 Important:
    Before saving your output to `financial_data.md`, perform this final step:
    - Replace all smart punctuation (like `’`, `“`, `”`, `–`) with standard ASCII characters (e.g., `'`, `"`, `-`).
    - Save the output in UTF-8 encoding using FileTools.

    Your output must be:
    - Clean, well-formatted Markdown
    - Free of encoding issues
    - Saved in a file called `financial_data.md`
    """,

    success_criteria="Your task is only complete when the output is saved to 'financial_data.md'.",

    
    stream=True,
)

Financial_data_agent.print_response("Summarize what Oklo does and provide the pros and cons of investing into it based on the earnings call Q2–Q3 2024", stream=True, markdown=True)


file_tools = FileTools()

response = Financial_data_agent.run(
    "Summarize what Oklo does and provide the pros and cons of investing into it based on the earnings call Q2–Q3 2024"
)

# Sauvegarde du résultat dans financial_data.md
file_tools.save_file("financial_data.md", response)

# Financial Adviser Agent
recommendation_agent = Agent(
    name="Financial Adviser Agent",
    model=Gemini(id=id, api_key=api_key),
    tools=[FileTools(), YFinanceTools(
        stock_price=True,
        company_info=True,
        stock_fundamentals=True,
        key_financial_ratios=True,
        analyst_recommendations=True,
    ), ExaTools(),],
    description="""
    A financial advisory agent responsible for issuing structured investment recommendations based on prior financial analysis.
    It reads data from 'financial_data.md' and produces a detailed recommendation report using a fixed template, 
    including both qualitative insights and quantitative metrics.


    """,
    
    instructions="""
    You are tasked with generating a professional stock recommendation report and save it as a 'recommendation.md' file.

    Step 1: Load and read the file `financial_data.md`. It contains a prior detailed analysis of the stock's performance, risks, and potential.

    Step 2: Based on the data in that file and YFinance tools, complete the following structured markdown template with realistic and accurate values:

    ---
    [Company Name] Stock Recommendation

    **Rating**: [Buy / Hold / Sell]  
    **Target Price**: [$XX.XX]  

    **Rationale**:

    - **Financial Health**: [Brief summary of financials — EPS, revenue trends, profitability]  
    - **Regulatory Environment**: [Summary of policy or compliance issues]  
    - **Growth Initiatives**: [Acquisitions, partnerships, product pipelines]  
    - **Market Position**: [Competitive strengths or threats]  
    - **Risk Factors**: [Short/long-term risks or volatility factors]  

    **Overall**: [1–2 sentence summary — should reflect the company’s outlook and your advised action]

    **Key Metrics**:

    | Metric               | Value       |
    |----------------------|-------------|
    | Open Price           | $XX.XX      |
    | Market Cap           | $X.XXB      |
    | 52-Week High         | $XX.XX      |
    | 52-Week Low          | $XX.XX      |
    | P/E Ratio            | XX.XX       |
    | Volume               | X,XXX,XXX   |
    | Volatility (30D)     | XX%         |

    **Company Details**:

    | Name       | Rating | Target | ISIN      | Last Price | Currency | Sector   | Sector Rating |
    |------------|--------|--------|-----------|------------|----------|----------|----------------|
    | [Company]  | [Rating] | [Price] | [ISIN] | $XX.XX     | [Ccy]    | [Sector] | [Sector Rating] |

    Notes:
    - Make sure all values are consistent with the financial insights in the input file.
    - Maintain a professional tone suitable for investment committees or client reports.
    - Use markdown formatting to ensure the output is clean and readable.

    Step 3: Save the final output as a 'recommendation.md' file.
    """,


    stream=True,
    markdown=True

)

recommendation_agent.print_response("Manuel is interested in Oklo Inc. stock. What is our recommendation for this stock?", stream=True, markdown=True)

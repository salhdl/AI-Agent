from agno.agent import Agent
from agno.models.google import Gemini
from dotenv import load_dotenv
import os
from agno.tools.file import FileTools
from agno.tools.calculator import CalculatorTools
from agno.tools.gmail import GmailTools
from agno.team import Team
from agno.storage.postgres import PostgresStorage
from pyairtable import Table
from flask import Flask, request, render_template_string, jsonify
from pyngrok import ngrok
import uuid
import threading
import time
import logging
from flask_cors import CORS
import requests

# Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()


# Load environment variables
id= os.getenv("id")
api_key = os.getenv("api_key")
AIRTABLE_TOKEN = os.getenv("AIRTABLE_API")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")
NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")
HR_EMAIL = os.getenv("HR_EMAIL")

# Airtable table configurations
holiday_table = Table(AIRTABLE_TOKEN, BASE_ID, "employee_holidays")
project_table = Table(AIRTABLE_TOKEN, BASE_ID, "employee_projects")
request_table = Table(AIRTABLE_TOKEN, BASE_ID, "holiday_requests")

# Flask app for approval/disapproval
app = Flask(__name__)

CORS(app, resources={r"/chat": {"origins": "http://localhost:8080"}})
CORS(app, resources={r"/text": {"origins": "http://localhost:8080"}})

APPROVAL_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Holiday Request Approval</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 600px; margin: auto; }
        .button { padding: 10px 20px; margin: 10px; font-size: 16px; cursor: pointer; }
        .approve { background-color: #4CAF50; color: white; border: none; }
        .disapprove { background-color: #f44336; color: white; border: none; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Holiday Request Approval</h2>
        <p><strong>Employee ID:</strong> {{ employee_id }}</p>
        <p><strong>Name:</strong> {{ name }}</p>
        <p><strong>Requested Days:</strong> {{ requested_days }}</p>
        <p><strong>Remaining Holiday Days:</strong> {{ remaining_days }}</p>
        <p><strong>Request Date:</strong> {{ request_date }}</p>
        <form method="POST" action="/process/{{ request_id }}">
            <button type="submit" name="action" value="approved" class="button approve">Approve</button>
            <button type="submit" name="action" value="disapproved" class="button disapprove">Disapprove</button>
        </form>
    </div>
</body>
</html>
"""

@app.route('/request/<request_id>')
def show_request(request_id):
    try:
        # logger.info(f"Attempting to retrieve request with request_id: {request_id}")
        records = request_table.all(formula=f"{{request_id}}='{request_id}'")
        if not records:
            # logger.error(f"No record found for request_id: {request_id}")
            return "Request not found", 404
        record = records[0]
        fields = record['fields']
        # logger.info(f"Retrieved record: {record}")
        return render_template_string(
            APPROVAL_PAGE,
            employee_id=fields.get('employee_id'),
            name=fields.get('full_name'),
            requested_days=fields.get('requested_days'),
            remaining_days=fields.get('remaining_days'),
            request_date=fields.get('request_date'),
            request_id=request_id
        )
    except Exception as e:
        # logger.error(f"Error retrieving request {request_id}: {str(e)}")
        return f"Error retrieving request: {str(e)}", 500

@app.route('/process/<request_id>', methods=['POST'])
def process_request(request_id):
    try:
        # logger.info(f"Processing request with request_id: {request_id}")
        action = request.form.get('action')
        records = request_table.all(formula=f"{{request_id}}='{request_id}'")
        if not records:
            # logger.error(f"No record found for request_id: {request_id}")
            return "Request not found", 404
        record = records[0]
        request_table.update(record['id'], {'status': action})
        # logger.info(f"Updated request {request_id} with status: {action}")
        # Trigger approval agent to notify employee
        response = approval_agent.run(f"Process holiday request {request_id} with action {action}", markdown=True)
        print(response.content)
        logger.info(f"Approval agent response: {response.content}")
        return f"Request {action}d successfully. The employee will be notified."
    except Exception as e:
        # logger.error(f"Error processing request {request_id}: {str(e)}")
        return f"Error processing request: {str(e)}", 500

@app.route('/chat', methods=['POST'])
def chat_handler():
    try:
        data = request.get_json()
        message = data.get("message")

        if not message:
            return jsonify({"error": "Missing message"}), 400

        # Call the team agent
        response = ChatBot_Team.run(message, markdown=True)

        return jsonify({"response": response.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/text', methods=['POST'])
def voice_handler():
    try:
        data = request.get_json()
        print(data)
        print(data.get("transcript"))

        transcript = data.get("transcript") 
        print(transcript)
        if not transcript:
            return jsonify({"error": "Missing transcript"}), 400
        # Optional: customer_name = data.get("customer_name", "User")

        # Step 1: Create Chat Session
        create_chat_response = requests.post(
            "https://api.retellai.com/create-chat",
            headers={
                "Authorization": f"Bearer key_1501adb94f79644ed8f3f9c0fc51",
                "Content-Type": "application/json"
            },
            json={
                "agent_id": "agent_46b88cf66474b91d090194619b",
                "metadata": {}
            }
        )
        print(create_chat_response) #prints response 402, means payment required!!!!!
        if create_chat_response.status_code != 200:
            return jsonify({"error": f"Failed to create chat: {create_chat_response.text}"}), 500

        chat_id = create_chat_response.json().get("chat_id")
        if not chat_id:
            return jsonify({"error": "No chat_id returned"}), 500

        # Step 2: Send Message
        RETELL_API_KEY = "key_1501adb94f79644ed8f3f9c0fc51" 
        completion_response = requests.post(
            "https://api.retellai.com/create-chat-completion",
            headers={
                "Authorization": f"Bearer {RETELL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "chat_id": chat_id,
                "content": transcript
            }
        )

        if completion_response.status_code != 200:
            return jsonify({"error": f"Failed to get completion: {completion_response.text}"}), 500

        messages = completion_response.json().get("messages", [])
        agent_reply = messages[-1]["content"] if messages else "No reply from agent."

        return jsonify({
            "response": agent_reply,
            "chat_id": chat_id
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    
def start_flask():
    # logger.info("Starting Flask app on port 5001")
    app.run(port=5000)

# Start ngrok and Flask in a separate thread
ngrok.set_auth_token(NGROK_AUTH_TOKEN)
public_url = ngrok.connect(5000, bind_tls=True).public_url
# logger.info(f"ngrok public URL: {public_url}")
threading.Thread(target=start_flask, daemon=True).start()
time.sleep(2)  # Wait for Flask to start

# Airtable tool functions
def get_employee_holiday(employee_id: int):
    """Retrieve employee holiday information from Airtable by employee_id."""
    records = holiday_table.all()
    for record in records:
        fields = record["fields"]
        if fields.get("employee_id") == employee_id:
            # logger.info(f"Retrieved holiday data for employee_id: {employee_id}")
            return {
                "name": fields.get("full_name"),
                "email": fields.get("email"),
                "total": int(fields.get("total_holiday_days", 0)),
                "taken": int(fields.get("holidays_taken", 0)),
                "last_date": fields.get("last_holiday_taken"),
            }
    # logger.warning(f"No holiday data found for employee_id: {employee_id}")
    return None

def get_employee_project(employee_id: int):
    """Retrieve employee project information from Airtable by employee_id."""
    records = project_table.all()
    for record in records:
        fields = record["fields"]
        if fields.get("employee_id") == employee_id:
            # logger.info(f"Retrieved project data for employee_id: {employee_id}")
            return {
                "name": fields.get("employee_name"),
                "project": fields.get("project_name"),
                "role": fields.get("role"),
                "start_date": fields.get("start_date"),
                "end_date": fields.get("end_date"),
                "next_project": {
                    "project_name": fields.get("next_project_name", ""),
                    "start_date": fields.get("next_project_start_date", ""),
                    "role": fields.get("next_project_role", "")
                }
            }
    # logger.warning(f"No project data found for employee_id: {employee_id}")
    return None

def update_next_project(employee_id: int, project_name: str, start_date: str, role: str):
    """Update the next project information for an employee in Airtable."""
    records = project_table.all()
    for record in records:
        fields = record["fields"]
        if fields.get("employee_id") == employee_id:
            project_table.update(record["id"], {
                "next_project_name": project_name,
                "next_project_start_date": start_date,
                "next_project_role": role
            })
            # logger.info(f"Updated next project for employee_id: {employee_id}")
            return True
    # logger.warning(f"No project record found for employee_id: {employee_id}")
    return False

def create_holiday_request(employee_id: int, requested_days: int):
    """Create a new holiday request in Airtable."""
    employee = get_employee_holiday(employee_id)
    if not employee:
        # logger.error(f"No employee found for employee_id: {employee_id}")
        return None
    request_id = str(uuid.uuid4())
    remaining_days = employee['total'] - employee['taken']
    try:
        request_table.create({
            'request_id': request_id,
            'employee_id': employee_id,
            'full_name': employee['name'],
            'requested_days': requested_days,
            'remaining_days': remaining_days,
            'status': 'pending',
            'request_date': time.strftime('%Y-%m-%d')
        })
        # logger.info(f"Created holiday request {request_id} for employee_id: {employee_id}")
        return request_id
    except Exception as e:
        # logger.error(f"Failed to create holiday request for employee_id {employee_id}: {str(e)}")
        return None

def update_holiday_taken(employee_id: int, additional_days: int):
    """Update holidays_taken for an employee in Airtable."""
    records = holiday_table.all()
    for record in records:
        fields = record["fields"]
        if fields.get("employee_id") == employee_id:
            current_taken = int(fields.get("holidays_taken", 0))
            holiday_table.update(record["id"], {
                "holidays_taken": current_taken + additional_days,
                "last_holiday_taken": time.strftime('%Y-%m-%d')
            })
            # logger.info(f"Updated holidays_taken for employee_id: {employee_id}")
            return True
    # logger.warning(f"No holiday record found for employee_id: {employee_id}")
    return False

# Holiday Agent
holiday_agent = Agent(
    name="Holiday Days Calculator Agent",
    model=Gemini(id=id, api_key=api_key),
    markdown=True,
    show_tool_calls=True,
    tools=[
        FileTools(),
        CalculatorTools(),
        GmailTools(credentials_path=r"C:\Users\hp\Downloads\AiAgents-yns\HR-Assistant\client_secret.json"),
        get_employee_holiday,
        create_holiday_request
    ],
    description="""
    An internal company assistant that helps employees check their holiday status and submit holiday requests.
    This agent queries holiday data from Airtable using employee IDs and creates holiday request entries for HR approval.
    It sends an email to HR with a link to approve or disapprove the request.
    """,
    instructions="""
    - Your job is to retrieve holiday information or process holiday requests using the employee’s unique ID.
    - Use `get_employee_holiday` to fetch:
        - Full name
        - Email
        - Total allocated holiday days
        - Number of holidays taken
        - Last holiday date
    - For balance queries:
        - Calculate: remaining_days = total_holiday_days - holidays_taken
        - Return the information clearly and professionally.
    - For holiday requests:
        - Extract the number of requested days and employee ID from the query.
        - Use `create_holiday_request` to store the request in Airtable.
        - Generate a unique request ID and include it in an email to HR ({HR_EMAIL}) with a link to the approval page: {public_url}/request/<request_id>
        - The email should include the employee’s name, requested days, and remaining balance.
    - Do not send holiday balance or request confirmation directly to the employee unless explicitly requested.
    - Only use data from Airtable. Do not guess or hallucinate employee info.
    - If no matching employee_id is found, respond with: "No holiday data found for the provided employee ID."
    """.format(HR_EMAIL=HR_EMAIL, public_url=public_url),
)

# Approval Agent
approval_agent = Agent(
    name="Holiday Approval Agent",
    model=Gemini(id=id, api_key=api_key),
    markdown=True,
    tools=[
        GmailTools(credentials_path=r"C:\Users\hp\Downloads\AiAgents-yns\HR-Assistant\client_secret.json"),
        get_employee_holiday,
        update_holiday_taken
    ],
    description="""
    An internal agent that processes HR holiday request approvals or disapprovals.
    It updates the employee's holiday data and notifies the employee of the decision via email.
    """,
    instructions="""
    - Your job is to process holiday request outcomes (approve or disapprove) from the Airtable `holiday_requests` table.
    - For each request:
        - Retrieve the request by `request_id` using a filter formula `{{request_id}}='{request_id}'` to get `employee_id`, `full_name`, `requested_days`, and `status`.
        - Use `get_employee_holiday` to get the employee’s email for notifications using the `employee_id`.
        - If `status` is 'approved':
            - Use `update_holiday_taken` to increment `holidays_taken` by `requested_days` and update `last_holiday_taken`.
            - Send an email to the employee’s email confirming approval.
        - If `status` is 'disapproved':
            - Send an email to the employee confirming disapproval.
        - Include the employee’s name, requested days, and decision in the email.
    - Do not modify Airtable data unless explicitly required (e.g., for approved requests).
    - If no matching request_id is found, log: "No request found for the provided ID."
    """
)

# Project Agent
project_agent = Agent(
    name="Project Management Agent",
    model=Gemini(id=id, api_key=api_key),
    markdown=True,
    tools=[
        GmailTools(credentials_path=r"C:\Users\hp\Downloads\AiAgents-yns\HR-Assistant\client_secret.json"),
        FileTools(),
        get_employee_project,
        update_next_project
    ],
    description="""
    An internal company assistant that helps employees view and manage their current and future project assignments.
    This agent reads employee project data from an Airtable table using the employee’s unique ID.
    It can also update planned future projects when new information is provided.
    """,
    instructions="""
    - Use the Airtable project table to manage employee project data by `employee_id`.
    - For each employee, retrieve:
        - Current project name
        - Role
        - Start date
        - End date
        - Optional future assignment details under "next project"
    - Respond to user questions like:
        - "What is my current project?"
        - "When does my project end?"
        - "What’s my role in the project?"
    - If the user shares new project info, update the employee’s "next_project" fields:
        - next_project_name
        - next_project_start_date
        - next_project_role
    - Always match using `employee_id` only — do not use names for lookups.
    - Respond clearly, briefly, and professionally.
    - If no matching employee_id is found, reply: "No project record found for the provided employee ID."
    """
)

# Chatbot Team Manager
db_url = "postgresql+psycopg://postgres:ai@localhost:5432/ai"

ChatBot_Team = Team(
    name="HR Assistant Team Manager",
    members=[holiday_agent, project_agent, approval_agent],
    storage=PostgresStorage(
        table_name="agent_sessions",
        db_url=db_url,
        auto_upgrade_schema=True
    ),
    add_history_to_messages=True,
    model=Gemini(id=id, api_key=api_key),
    description="""
    An intelligent HR Assistant Team Manager responsible for handling employee queries related to holidays, project assignments, and holiday request approvals.
    This team manager delegates tasks to the most relevant specialist agent:
    - The **Holiday Agent** manages vacation day tracking and holiday request submissions.
    - The **Project Agent** manages project assignments, updates, and status inquiries.
    - The **Approval Agent** processes HR approvals or disapprovals and notifies employees.
    The manager ensures that every incoming query is handled by the appropriate agent based on the user's intent.
    """,
    instructions="""
    You are an intelligent routing agent that serves as the HR Assistant Team Manager.
    Your role is to:
    - Receive user questions related to employee holidays, project assignments, or holiday request approvals.
    - Analyze the intent of the query.
    - Forward the query to the correct agent:
        - If the query relates to holidays, time off, vacation, leave balance, or holiday requests, assign it to the **Holiday Days Calculator Agent**.
        - If the query relates to project names, roles, start/end dates, or updates, assign it to the **Project Management Agent**.
        - If the query relates to processing a holiday request approval or disapproval (e.g., from a web hook or internal trigger), assign it to the **Holiday Approval Agent**.
    - Never try to answer the user directly — your job is to decide which agent is most suited to respond.
    - If a query could match multiple areas, use your best judgment based on phrasing and specificity.
    - If no clear match exists, return a polite message suggesting the user clarify their request.
    Always strive to delegate clearly and efficiently, ensuring accurate responses from the appropriate domain expert.
    """
)

# Main interaction loop
# while True:
#     user_input = input("You: ")
#     if user_input.lower() in ["exit", "quit"]:
#         print("Bot: Goodbye!")
#         break
#     response = ChatBot_Team.run(user_input, markdown=True)
#     print("Bot:", response.content)





try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down.")
from typing import TypedDict, List, Dict
from langchain_community.agent_toolkits import GmailToolkit
from langchain_community.tools.gmail.search import GmailSearch
from langchain_community.llms import Ollama  # Import Ollama for local LLM
from langgraph.graph import StateGraph
import os
import time
import pickle
import threading  # For running the exit listener in a separate thread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build  # For sending emails
from langsmith import Client


# Define the state
class EmailsState(TypedDict):
    checked_emails_ids: List[str]
    emails: List[Dict]
    action_required_emails: Dict


# Global flag to control the program's execution
exit_flag = False


# Gmail Authentication Handler
class GmailAuthHandler:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
        self.TOKEN_PATH = 'token.pkl'
        self.CREDENTIALS_PATH = 'credentials.json'

    def get_gmail_service(self):
        creds = None
        if os.path.exists(self.TOKEN_PATH):
            try:
                with open(self.TOKEN_PATH, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                print(f"Error loading token: {e}")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    creds = self._handle_new_authentication()
            else:
                creds = self._handle_new_authentication()

            try:
                with open(self.TOKEN_PATH, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                print(f"Error saving token: {e}")

        return build('gmail', 'v1', credentials=creds)  # Return the Gmail API service

    def _handle_new_authentication(self):
        if not os.path.exists(self.CREDENTIALS_PATH):
            raise FileNotFoundError(f"Client secrets file not found at {self.CREDENTIALS_PATH}.")
        flow = InstalledAppFlow.from_client_secrets_file(self.CREDENTIALS_PATH, self.SCOPES)
        return flow.run_local_server(port=0)


# Custom Agents
class EmailFilterAgent:
    def __init__(self):
        self.role = "Senior Email Analyst"
        self.goal = "Filter out non-essential emails like newsletters and promotional content."
        self.backstory = (
            "You are a Senior Email Analyst with extensive experience in email content analysis. "
            "Your expertise lies in identifying key patterns and markers that signify the importance of an email. "
            "You are responsible for filtering out non-essential emails and ensuring only important emails are processed."
        )

    def filter_emails(self, emails: List[Dict]) -> List[Dict]:
        """Filter out non-essential emails like newsletters and promotions."""
        print(f"{self.role} is filtering emails...")
        filtered_emails = []
        for email in emails:
            sender = email.get('sender', '')
            snippet = email.get('snippet', '')
            # Example: Skip emails from known promotional senders
            if "newsletter" not in sender.lower() and "promo" not in sender.lower():
                filtered_emails.append(email)
        return filtered_emails


class EmailActionAgent:
    def __init__(self):
        self.role = "Email Action Specialist"
        self.goal = "Identify action-required emails and compile a list of important email IDs."
        self.backstory = (
            "You are an Email Action Specialist with a knack for identifying action-required emails. "
            "Your role is to compile a list of important email IDs based on their urgency and context. "
            "You use tools like GmailGetThread and internet search to better understand the emails."
        )

    def identify_action_required(self, emails: List[Dict]) -> List[Dict]:
        """Identify emails that require action."""
        print(f"{self.role} is identifying action-required emails...")
        action_emails = []
        for email in emails:
            sender = email.get('sender', '').lower()
            snippet = email.get('snippet', '').lower()

            # Example: Flag emails from specific senders or with specific phrases
            if (
                "linkedin" in sender or
                "kaggle" in sender or
                "course" in snippet or
                "new openings" in snippet
            ):
                action_emails.append(email)
        return action_emails


class EmailResponseAgent:
    def __init__(self, llm):
        self.role = "Email Response Writer"
        self.goal = "Draft tailored and effective responses for action-required emails. You need to specify the Sender's Name and you need to specify the Name of The Email User"
        self.backstory = (
            "You are a skilled Email Response Writer specializing in drafting tailored and effective responses. "
            "Your role is to ensure clear, concise communication for action-required emails. "
            "You use tools to reread threads, search the internet, and create drafts."
        )
        self.llm = llm

    def draft_response(self, email: Dict) -> str:
        """Draft a response for the given email using the LLM."""
        print(f"{self.role} is drafting a response...")
        # Include the agent's role, goal, and backstory in the prompt
        prompt = (
            f"Role: {self.role}\n"
            f"Goal: {self.goal}\n"
            f"Backstory: {self.backstory}\n\n"
            f"You received an email from {email['sender']} with the following content: {email['snippet']}. "
            "Draft a polite and concise response that aligns with your role and goal. "
        )
        response = self.llm(prompt)
        return response


# Nodes for the graph
class Nodes:
    def __init__(self, user_email: str):
        self.user_email = user_email  # Store the user's email
        try:
            auth_handler = GmailAuthHandler()
            self.gmail = auth_handler.get_gmail_service()
            print("Successfully authenticated with Gmail")
            # Load Ollama Llama3.2 model with base_url pointing to the host machine
            self.llm = Ollama(model="llama3.2", base_url="http://host.docker.internal:11434")
            print("Successfully loaded Llama3.2 model")
            # Initialize agents
            self.filter_agent = EmailFilterAgent()
            self.action_agent = EmailActionAgent()
            self.response_agent = EmailResponseAgent(self.llm)
        except Exception as e:
            print(f"Failed to initialize Gmail service or LLM: {str(e)}")
            raise

    def check_email(self, state: EmailsState) -> EmailsState:
        try:
            print("# checking for new emails")
            search = GmailSearch(api_resource=self.gmail)
            emails = search('is:unread')

            checked_emails = state.get('checked_emails_ids', [])
            thread = []
            new_emails = []

            for email in emails:
                if not isinstance(email, dict):
                    print(f"Skipping invalid email: {email}")
                    continue

                email_id = email.get('id')
                thread_id = email.get('threadId')
                sender = email.get('from', '')
                snippet = email.get('snippet', '')

                if (email_id not in checked_emails) and (thread_id not in thread) and (self.user_email not in sender):
                    thread.append(thread_id)
                    new_emails.append({
                        "id": email_id,
                        "threadId": thread_id,
                        "sender": sender,
                        "snippet": snippet
                    })

            checked_emails.extend([email.get('id') for email in emails if isinstance(email, dict)])

            return {
                **state,
                "emails": new_emails,
                "checked_emails_ids": checked_emails
            }
        except Exception as e:
            print(f"Error checking emails: {str(e)}")
            return state

    def wait_next_run(self, state: EmailsState) -> EmailsState:
        print("## Waiting for 30 seconds")
        time.sleep(30)
        return state

    def new_emails(self, state: EmailsState) -> str:
        if len(state.get("emails", [])) == 0:
            print('## No new emails')
            return "end"
        else:
            print("## New emails")
            return "continue"

    def draft_responses(self, state: EmailsState) -> EmailsState:
        print("### Drafting responses")
        # Filter emails using the EmailFilterAgent
        filtered_emails = self.filter_agent.filter_emails(state.get("emails", []))
        print(f"Filtered emails: {filtered_emails}")  # Debug: Print filtered emails

        # Identify action-required emails using the EmailActionAgent
        action_emails = self.action_agent.identify_action_required(filtered_emails)
        print(f"Action-required emails: {action_emails}")  # Debug: Print action-required emails

        for email in action_emails:
            print(f"Drafting response for email from {email['sender']} with snippet: {email['snippet']}")
            # Generate a response using the EmailResponseAgent
            response = self.response_agent.draft_response(email)
            print(f"Generated response: {response}")  # Debug: Print generated response

            # Send the response using the Gmail API
            try:
                message = {
                    "raw": self._create_message(email['sender'], "Re: Your email", response)
                }
                self.gmail.users().messages().send(userId="me", body=message).execute()
                print(f"Response sent to {email['sender']}")
            except Exception as e:
                print(f"Error sending response: {e}")  # Debug: Print sending error

        return state

    def _create_message(self, to: str, subject: str, message_text: str) -> str:
        """Create a message for sending via the Gmail API."""
        import base64
        from email.mime.text import MIMEText

        message = MIMEText(message_text)
        message['to'] = to
        message['subject'] = subject
        return base64.urlsafe_b64encode(message.as_bytes()).decode()


# Define the workflow
class WorkFlow:
    def __init__(self, user_email: str):
        nodes = Nodes(user_email)  # Pass the user's email to Nodes
        workflow = StateGraph(EmailsState)

        workflow.add_node("check_new_emails", nodes.check_email)
        workflow.add_node("wait_next_run", nodes.wait_next_run)
        workflow.add_node("draft_responses", nodes.draft_responses)

        workflow.set_entry_point("check_new_emails")
        workflow.add_conditional_edges(
            "check_new_emails",
            nodes.new_emails,
            {
                "continue": 'draft_responses',
                "end": 'wait_next_run'
            }
        )
        workflow.add_edge('draft_responses', 'wait_next_run')
        workflow.add_edge('wait_next_run', 'check_new_emails')
        self.app = workflow.compile()


# Function to listen for the "exit" command
def exit_listener():
    global exit_flag
    while True:
        user_input = input("Type 'exit' to stop the program: ").strip().lower()
        if user_input == "exit":
            exit_flag = True
            print("Exiting program...")
            break


# Main function
def main():
    try:
        print("Starting the program...")

        # Read the Gmail address from the .env file
        user_email = os.getenv("GMAIL_ADDRESS")
        if not user_email:
            raise ValueError("GMAIL_ADDRESS environment variable is not set.")

        print(f"Using Gmail address: {user_email}")

        #********************************************************************************************************** # LangSmith Code begins

        # Map LANGSMITH_API_KEY to LANGCHAIN_API_KEY if it exists
        if 'LANGSMITH_API_KEY' in os.environ and 'LANGCHAIN_API_KEY' not in os.environ:
            os.environ['LANGCHAIN_API_KEY'] = os.environ['LANGSMITH_API_KEY']
        
        # Environment variable checks
        if 'LANGCHAIN_API_KEY' not in os.environ:
            raise EnvironmentError("LANGCHAIN_API_KEY or LANGSMITH_API_KEY environment variable is not set. Visit https://smith.langchain.com to get your API key.")
        
        # Configure LangSmith tracing
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ.setdefault("LANGCHAIN_PROJECT", "Gmail Assistant Workflow")  # set the project in langsmith 
        
        # Initialize LangSmith client
        try:
            client = Client()
            print(f"LangSmith tracing enabled | Project: {os.environ['LANGCHAIN_PROJECT']}")
        except Exception as e:
            print(f"LangSmith initialization warning: {str(e)}")
        
        #********************************************************************************************************** # LangSmith Code ends

        # Initialize Gmail workflow with the user's email
        print("Initializing Gmail workflow...")
        app = WorkFlow(user_email).app

        # Initial state for the workflow
        initial_state = {
            "checked_emails_ids": [],
            "emails": [],
            "action_required_emails": {}
        }

        # Start the exit listener in a separate thread
        exit_thread = threading.Thread(target=exit_listener)
        exit_thread.daemon = True  # Daemonize thread to exit when the main program exits
        exit_thread.start()

        print("Starting email monitoring...")
        while not exit_flag:
            # Invoke the workflow with the initial state
            app.invoke(initial_state)

    except FileNotFoundError as e:
        print(f"Authentication Error: {str(e)}")
        print("Please ensure you have client_secrets.json file in your project directory")

    except EnvironmentError as e:
        print(f"Environment Error: {str(e)}")
        print("Please set up your environment variables properly")

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        
if __name__ == "__main__":
    main()
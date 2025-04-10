# Email_Multi_Agent_Automation_System

Gmail Assistant Workflow 🌟
Welcome to the Gmail Assistant Workflow project! 🚀 This Python-based assistant is designed to make your email management effortless and efficient. Whether you're drowning in newsletters, promotional emails, or action-required messages, this tool has got your back. Let’s automate your inbox and save you time! ⏰

✨ Features
Email Filtering: Automatically filters out non-essential emails like newsletters and promotional content. No more clutter! 🗑️

Action Identification: Identifies emails that require action based on specific criteria (e.g., emails from LinkedIn, Kaggle, or containing keywords like "course" or "new openings"). 📥

Response Drafting: Drafts tailored and effective responses for action-required emails using a local LLM (Llama3.2 powered by Ollama). ✍️

Gmail Integration: Uses the Gmail API to fetch, send, and manage emails seamlessly. 📧

LangSmith Integration: Enables tracing and monitoring of the workflow using LangSmith for better insights. 📊

🛠️ Prerequisites
Before diving in, ensure you have the following:

Python 3.7+: The project is written in Python and requires Python 3.7 or higher. 🐍

Gmail API Credentials: You need to set up Gmail API credentials. Follow these steps:

Go to the Google Cloud Console.

Create a new project or select an existing one.

Enable the Gmail API for your project.

Create OAuth 2.0 credentials and download the credentials.json file.

Place the credentials.json file in the root directory of the project.

Ollama: The project uses Ollama to run a local LLM. Ensure you have Ollama installed and the llama3.2 model downloaded. 🤖

Environment Variables:

MY_EMAIL: Set this to your Gmail address.

LANGCHAIN_API_KEY or LANGSMITH_API_KEY: Set this to your LangSmith API key for tracing and monitoring.

🚀 Installation
Clone the Repository:

bash
Copy
git clone https://github.com/your-username/gmail-assistant.git
cd gmail-assistant
Install Dependencies:

bash
Copy
pip install -r requirements.txt
Set Up Environment Variables:

Create a .env file in the root directory and add the following:

plaintext
Copy
MY_EMAIL=your-email@gmail.com
LANGCHAIN_API_KEY=your-langsmith-api-key
Run the Program:

bash
Copy
python main.py
🔄 Workflow Overview
Authentication: The program authenticates with Gmail using OAuth 2.0 and loads the local LLM. 🔐

Email Checking: The program checks for new unread emails. 📨

Filtering: Non-essential emails (e.g., newsletters, promotions) are filtered out. 🧹

Action Identification: Emails that require action are identified based on specific criteria. 🎯

Response Drafting: Responses are drafted for action-required emails using the local LLM. ✨

Sending Responses: Drafted responses are sent via the Gmail API. 📤

Loop: The program waits for 30 seconds before checking for new emails again. 🔁

🛑 Exiting the Program
To stop the program, type exit in the terminal and press Enter. The program will gracefully stop after completing the current iteration. ⏹️

📊 LangSmith Integration
The project integrates with LangSmith for tracing and monitoring. Ensure you have set the LANGCHAIN_API_KEY environment variable. You can view the traces and logs in your LangSmith dashboard. 📈

🚨 Troubleshooting
Authentication Errors: Ensure that the credentials.json file is correctly placed in the root directory and that you have granted the necessary permissions. 🔑

Environment Errors: Ensure that all required environment variables are set correctly. 🌐

LLM Errors: Ensure that Ollama is running and the llama3.2 model is downloaded. 🤖

🤝 Contributing
Contributions are welcome! Whether it's a bug fix, feature request, or improvement, feel free to open an issue or submit a pull request. Let’s make this project even better together! 🌈

This README provides an overview of the Gmail Assistant Workflow project. For more details, refer to the code and comments in the main.py file. Happy coding! 💻🎉

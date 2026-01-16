# Draftly - AI Email Drafting Assistant

An AI-powered email assistant that helps users compose professional email replies quickly and efficiently using Gmail and Groq LLM.

## Key Features

- **AI-Powered Drafts**: Generate contextual email replies using Groq's LLM
- **Gmail Integration**: Seamlessly works with your Gmail account via OAuth
- **Thread Context**: Understands full email conversations for better responses
- **Multiple Styles**: Choose from different writing styles (Professional, Casual, Formal, etc.)
- **Draft Management**: Save drafts or send emails directly
- **Session Management**: Secure user sessions with database storage

##  Project Structure

```
draftly-v1/
├── src/draftly_v1/           # Main application code
│   ├── app.py                # FastAPI application entry point
│   ├── config.py             # Configuration settings
│   ├── model/                # SQLAlchemy database models
│   │   ├── User.py           # User model
│   │   ├── UserSession.py    # Session model
│   │   └── DraftLog.py       # Draft/email log model
│   ├── routes/               # API route handlers
│   │   ├── auth_routes.py    # Google OAuth authentication
│   │   ├── email_routes.py   # Email operations (fetch, draft, send)
│   │   └── static_routes.py  # Frontend static files
│   └── services/             # Business logic
│       ├── database.py       # Database operations
│       ├── gmail_services.py # Gmail API integration
│       ├── email_services.py # Email drafting/sending
│       ├── llm_services.py   # Groq LLM integration
│       └── utils/            # Utility functions
├── frontend/                 # Frontend HTML/JS files
│   ├── index.html           # Main dashboard
│   ├── login.html           # Login page
│   └── js/                  # JavaScript modules
├── resources/               # OAuth client secrets (not in Git)
├── tests/                   # Test files
├── docker-compose.yml       # Docker orchestration
├── Dockerfile              # Container definition
└── .env                    # Environment variables (not in Git)
```

## Key Technologies

- **Backend**: FastAPI, Python 3.11
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI/LLM**: Groq API (llama-3.3-70b-versatile)
- **Email**: Gmail API with OAuth 2.0
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Deployment**: Docker & Docker Compose


## Draftly: High-Level System Architecture

![alt text](image.png)

#### This diagram represents how components communicate, specifically highlighting the "Human-in-the-Loop" flow and the database caching layer we implemented.

##### Key Components Explained
1. ###### Client Layer (Bootstrap + Vanilla JS)
State Management: Local storage handles the 2-hour session token.

Polling Engine: Triggers the /sync endpoint every 2 minutes to check for new messages.

User Interface: Three-column layout for Inbox, Thread History, and AI Interaction.

2. ###### API Gateway & Logic (FastAPI)
Auth Middle-ware: Validates the custom X-Session-Token against PostgreSQL before allowing any Gmail operations.

Background Tasks: Handles the "Mark as Read" operations so the user doesn't have to wait for the UI to update.

3. ###### Data Persistence (PostgreSQL)
Email Metadata: Stores thread_id and message_id to prevent redundant Gmail fetches.

Draft Store: Acts as the "Source of Truth" for AI drafts, allowing the user to edit and save progress before sending.

Session Table: Manages the life-cycle of user logins with hard expires_at timestamps.

4. ###### External Integration
Gmail API (OAuth2): Handles the actual retrieval and sending of emails.

LLM/AI Service (GROQ): Processes the thread history to generate context-aware replies.


###### Security: added a custom session layer on top of GMAIL OAuth.

###### Asynchronous: Asynchronous background tasks to keep the UI snappy.



## Draftly flow:

1) #### User login:
	* User needs to authorize the GMAIL oauth, which will be handled by the backend redirects. 
	* The necessary Long lived token will be extracted from the GMAIL api and persisted in User Table in PostgreSQL DB.
2) #### Email Draft generation:
	* When a new email arrives in Gmail Inbox, the front end Sync service (runs periodically frequency of 2 mins)or Manual sync when user clicks from UI calls backend with HTTP REST request.
	* Gets the "UNREAD" emails from only inbox which persists necessary data to "Draftlog" Table in PostgreSQL DB.
	* The front end populates the UI column with unread messages and metadata.
	* When user selects the desired Email to respond, it then calls the backend to retrieve whole email thread using GMAIL batch request by passing the selected threadId.
	* The email thread data will be parsed as per LLM suitable payload.
	* Using the langchain_core.prompts PromptTemplate chain composition is formed with LLM and output parser
	* The parsed data will be passed as arguments while invoking the chain, upon invoking the chain it makes an call to LLM.
	* the LLm will generate the email draft based on the Prompt template, email context and the tone preference.
	* the generated draft will be persisted to draftLog and same will be responded to UI.
	
3) #### Approve and send :
	* Upon user validation or email draft content edit via UI. The User can Send email directly or save draft in gmail.
	* If user wants to change the tone/style, user can regenerate the email Draft by passing the tone selection.
	* Using the Gmail threadID meta data all Emails body, headers will be formed and sent via Gmail API.
	

## Running Tests

```bash
# Install test dependencies
pip install -e ".[testing]"

# Run all tests
pytest

```

# Draftly Setup Guide

## Prerequisites

1. Docker and Docker Compose installed
2. Google Cloud account
3. GROQ API key
4. create .env file with required environment variables


## Step 1: Get Google OAuth Credentials

   1. Go to [Google Cloud Console](https://console.cloud.google.com/)
   2. Create a new project or select existing one
   3. Enable **Gmail API**:
      * Go to "APIs & Services" > "Library"
      * Search for "Gmail API"
      * Click "Enable"
   4. provide consent by creating the app.
	
	   1. Create OAuth 2.0 Credentials:
	   * Go to "APIs & Services" > "Credentials"
	   * Choose "Web application"
	   * Click "Create Credentials" > "OAuth client ID"
	   * Add Authorized redirect URIs:
      ```
       http://localhost:8000/auth/callback
      ```
	   * Click "Create"

   2. add test user
	   * Go to "audience" > "Test users" 
	   * add upto 100 gmail id to test
	   * now oauth can be provided to only test user list

   5. Download the JSON file:
      * Click the download button next to your credential
      * Rename it to `client_secret.json`

## Step 2: Project Structure to run with docker

Create this folder structure to run the app via docker compose:

your-project-folder/
├── docker-compose.yml
├── .env
└── resources/
	└── client_secret.json ← Place your downloaded file here with exact name

2. **Configure environment variables**
   
   Create a `.env` file in the project root:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_MODEL_NAME=llama-3.3-70b-versatile
   
   GAPI=https://www.googleapis.com/
   GMAIL_SCOPES=auth/gmail.modify,auth/gmail.readonly,auth/userinfo.email,auth/userinfo.profile,openid
   
   DATABASE_URL=postgresql://postgres:password@draftly-db:5432/draftly
   POSTGRES_USER=<your_username>
   POSTGRES_PASSWORD=<your_password>
   POSTGRES_DB=draftly 
    # note: db should be created manually
   ```



3. **Build and run with Docker Compose**
   ```bash

   # pull docker image
   docker pull jayathirthawa/draftly-app:latest

   # Build and start all services
   docker-compose up -d

   ```

5. **Access the application**
   - Frontend: http://localhost:8000/ui
   - Login: http://localhost:8000/ui/login



### Troubleshooting

**Database connection issues:**
```bash
# Ensure DATABASE_URL uses 'draftly-db' not 'localhost'
DATABASE_URL=postgresql://postgres:password@draftly-db:5432/draftly

# Reset database
docker-compose down -v
docker-compose up -d
```

## API Endpoints

### Authentication
- `GET /auth/login` - Initiate Google OAuth flow
- `GET /auth/callback` - redirect url by the backend to complete OAuth callback, handler 

### Email Operations
- `POST /email/fetch_latest` - Fetch unread emails
- `POST /email/draft` - Generate AI draft for email thread
- `POST /email/regenerate_draft` - Regenerate draft with different style
- `POST /email/send` - Send email draft

## Security Notes

- Google OAuth credentials are **NOT** included in the Docker image
- They are mounted as a read-only volume at runtime

## License

MIT License - See [LICENSE.txt](LICENSE.txt)

##  Author

Jayathirtha - [GitHub Profile](https://github.com/Jayathirtha)

---
For Docker deployment details, see [DOCKER.md](DOCKER.md)

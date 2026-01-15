import html
import logging
import os
import re
from dotenv import load_dotenv
from draftly_v1.services.database import get_db_session
from draftly_v1.services.utils.logger_config import setup_logging
from langchain_groq import ChatGroq  
from langchain_core.prompts import PromptTemplate 
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

setup_logging(logging.INFO)
_logger = logging.getLogger(__name__)

api_key = os.getenv("GROQ_API_KEY")
llm_model = os.getenv("GROQ_MODEL_NAME", "insta")

llm = ChatGroq(model=llm_model,
            temperature=0.7,
            max_tokens=512,
            api_key=api_key) 

def generate_draft(email_context, user_style: str, sender_name: str = None) -> str:
    _logger.debug(f"Generating draft with context: {email_context} and style: {user_style}")
    llm = ChatGroq(model="llama-3.3-70b-versatile")
    
    prompt = PromptTemplate.from_template("""
    You are an AI assistant helping a user draft an email reply.
    
    User's preferred style: {user_style}
    User's name: {sender_name}
    
    {email_context}
    
    INSTRUCTIONS:
    - Read the entire email thread for context
    - Generate a reply to the LATEST EMAIL only
    - Use the user's preferred style: {user_style}
    - Reference previous emails in the thread if relevant to the response
                                          
    Communication style:
	- Use clear, concise language with bullet points where appropriate
    - Match the tone and formality of the {user_style}

    Response formatting:
	- Provide answers in HTML format
	- Use bullet points when listing multiple items
    - Add appropriate greetings and sign-offs with the user's name
    - Do NOT make up information; use placeholders like [INSERT INFO HERE] where necessary
    - Focus your response on addressing the latest email's content and questions

    Generate the email draft now:
    """)
    
    chain = prompt | llm | StrOutputParser() # chain composition using pipe operator
    response = chain.invoke({
        "user_style": user_style, 
        "email_context": formatted_context(email_context), 
        "sender_name": sender_name or "User"
    })
    return response


def clean_html_for_llm(html_content: str) -> str:
    """Convert HTML content to clean text for LLM processing"""
    if not html_content or not isinstance(html_content, str):
        return html_content
    
    # Remove HTML tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # Unescape HTML entities
    text = html.unescape(text)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text

 # Format email thread context for better LLM understanding
def formatted_context(email_context) -> str:
    """Format email thread context for better LLM understanding"""
    _logger.debug(f"Formatting context: {type(email_context)}")
    formatted_text = ""
    
    # Handle different input types
    if isinstance(email_context, str):
        return formatted_context(clean_html_for_llm(email_context))
    elif isinstance(email_context, list) and len(email_context) > 0:
        # Check if list contains dictionaries or strings
        if isinstance(email_context[0], dict):
            # Process previous emails in the thread (if any)
            if len(email_context) > 1:
                formatted_text += "=== PREVIOUS EMAIL THREAD (for context only) ===\n\n"
                for idx, msg in enumerate(email_context[1:]):
                    formatted_text += f"Email #{idx + 1}:\n"
                    formatted_text += f"From: {msg.get('from', 'Unknown')}\n"
                    formatted_text += f"To: {msg.get('to', 'Unknown')}\n"
                    formatted_text += f"Date: {msg.get('date', 'Unknown')}\n"
                    formatted_text += f"Subject: {msg.get('subject', 'No Subject')}\n"
                    formatted_text += f"Content: {clean_html_for_llm(msg.get('body', ''))}\n\n"
            
            # Process the latest email that needs a response
            latest_msg = email_context[0]
            formatted_text += "=== LATEST EMAIL (Reply to this) ===\n\n"
            formatted_text += f"From: {latest_msg.get('from', 'Unknown')}\n"
            formatted_text += f"To: {latest_msg.get('to', 'Unknown')}\n"
            formatted_text += f"Date: {latest_msg.get('date', 'Unknown')}\n"
            formatted_text += f"Subject: {latest_msg.get('subject', 'No Subject')}\n"
            formatted_text += f"Content: {clean_html_for_llm(latest_msg.get('body', ''))}\n"
        else:
            # List contains strings or other types
            formatted_text = str(email_context)
    else:
        formatted_text = str(email_context)
    
    return formatted_text
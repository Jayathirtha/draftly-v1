from langchain_groq import ChatGroq  
from langchain.prompts import PromptTemplate  # type: ignore[import-untyped]

def generate_draft(context, user_style):
    llm = ChatGroq(model="llama-3.3-70b-versatile")
    
    prompt = PromptTemplate.from_template("""
    You are an AI assistant helping a professional draft an email.
    User's style: {style}
    Email thread context: {context}
    
    Generate a concise and helpful draft reply.
    """)
    
    chain = prompt | llm
    response = chain.invoke({"style": user_style, "context": context})
    return response.content


def build_style_profile(service):
    # 1. Fetch the last 10 sent messages 
    results = service.users().messages().list(userId='me', q="label:SENT", maxResults=10).execute()
    messages = results.get('messages', [])
    
    sample_texts = []
    for msg in messages:
        m = service.users().messages().get(userId='me', id=msg['id']).execute()
        sample_texts.append(m['snippet']) # Use snippet for a quick overview [cite: 10]

    # 2. Use LLM to analyze the style
    style_analyzer_prompt = f"""
    Analyze the following email snippets and summarize the writer's:
    1. Tone (e.g., formal, casual, authoritative)
    2. Common greetings and sign-offs
    3. Sentence structure (e.g., brief, descriptive)
    
    Emails: {" ".join(sample_texts)}
    """
    
    # Send this to OpenAI/LangChain to get a 'Style Profile' string
    # Then save that string to the User.style_profile column in the DB.


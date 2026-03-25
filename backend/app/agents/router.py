import os
import litellm
from .state import DocIntelState

# Point to LiteLLM Proxy if available, otherwise use direct
LITELLM_PROXY_URL = os.getenv("LITELLM_PROXY_URL", "http://litellm:4000")

async def router_node(state: DocIntelState) -> DocIntelState:
    """
    Classifies the user's query into one of the following intents:
    summarise, summarise_each, compare, contradict, extract, qa, action_items, timeline.
    """
    query = state.get("query", "")
    
    # Define the system prompt for intent classification
    system_prompt = """
    You are an AI router for a document intelligence system. Your task is to classify the user's query into one of the following intents:
    
    1. 'summarise': The user wants a summary of the provided document(s) as a whole.
    2. 'summarise_each': The user wants separate summaries for each of the provided documents.
    3. 'compare': The user wants to compare two or more documents or entities within documents.
    4. 'contradict': The user wants to find contradictions between documents or within a single document.
    5. 'extract': The user wants to extract specific structured data (e.g., tables, specific fields) from the documents.
    6. 'qa': The user has a specific question about the content of the documents.
    7. 'action_items': The user wants to identify tasks, deadlines, or responsibilities mentioned in the documents.
    8. 'timeline': The user wants a chronological sequence of events mentioned in the documents.
    
    Return only the intent name as a single word from the list above. If the query is ambiguous, default to 'qa'.
    """
    
    try:
        # Use LiteLLM with Gemini 1.5 Flash
        # We pass api_base if LITELLM_PROXY_URL is set, but for Gemini it might be direct
        # However, the project seems to prefer the proxy for other models.
        # If LITELLM_PROXY_URL is used, it should be configured to handle gemini/gemini-1.5-flash
        
        # For now, we'll try to use the proxy if it looks like it's configured for it,
        # but LiteLLM usually handles Gemini directly if API key is in ENV.
        
        response = await litellm.acompletion(
            model="gemini/gemini-1.5-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Query: {query}"}
            ],
            temperature=0,
            api_base=LITELLM_PROXY_URL
        )
        
        intent = response.choices[0].message.content.strip().lower()
        
        # Clean up common LLM "noise" like markdown or full stops
        intent = intent.replace(".", "").replace("'", "").replace("\"", "").strip()
        
        # Validate the intent against allowed list
        allowed_intents = ["summarise", "summarise_each", "compare", "contradict", "extract", "qa", "action_items", "timeline"]
        if intent not in allowed_intents:
            # Fallback check for partial matches or common variants
            for allowed in allowed_intents:
                if allowed in intent:
                    intent = allowed
                    break
            else:
                intent = "qa"
            
    except Exception as e:
        # Log error or print (consider using a logger)
        print(f"Error in router_node: {e}")
        intent = "qa"
        
    # Return the updated state as a partial dictionary (LangGraph will merge)
    return {"intent": intent}

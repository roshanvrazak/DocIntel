import os
import litellm
import logging
from .state import DocIntelState

# Point to LiteLLM Proxy if available, otherwise use direct
LITELLM_PROXY_URL = os.getenv("LITELLM_PROXY_URL", "http://litellm:4000")

logger = logging.getLogger(__name__)

async def router_node(state: DocIntelState) -> DocIntelState:
    """
    Classifies the user's query into one of the following intents:
    summarise, summarise_each, compare, contradict, extract, qa, action_items, timeline.
    """
    query = state.get("query", "")
    
    system_prompt = "Classify the query into exactly one intent: summarise, summarise_each, compare, contradict, extract, qa, action_items, timeline. Return only the intent name. Default: qa."

    try:
        response = await litellm.acompletion(
            model="gemini/gemini-1.5-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0,
            max_tokens=10,
            api_base=LITELLM_PROXY_URL,
            api_key="sk-dummy"
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
        logger.error(f"Error in router_node: {e}")
        intent = "qa"
        
    # Return the updated state as a partial dictionary (LangGraph will merge)
    return {"intent": intent}

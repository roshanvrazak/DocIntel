import litellm
import logging
from .state import DocIntelState
from backend.app.config import LITELLM_PROXY_URL, LITELLM_API_KEY

logger = logging.getLogger(__name__)

_ALLOWED_INTENTS = frozenset([
    "summarise", "summarise_each", "compare", "contradict",
    "extract", "qa", "action_items", "timeline",
])


async def router_node(state: DocIntelState) -> DocIntelState:
    """
    Classifies the user's query into one of the supported intents.
    Falls back to 'qa' on any error or unrecognised output.
    """
    query = state.get("query", "")

    # If the caller already supplied an explicit intent (e.g. from the UI action
    # selector), skip the LLM classification step.
    existing_intent = state.get("intent")
    if existing_intent and existing_intent in _ALLOWED_INTENTS:
        return {"intent": existing_intent}

    system_prompt = (
        "Classify the query into exactly one intent: "
        "summarise, summarise_each, compare, contradict, extract, qa, action_items, timeline. "
        "Return ONLY the intent name. Default: qa."
    )

    try:
        response = await litellm.acompletion(
            model="gemini/gemini-1.5-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            temperature=0,
            max_tokens=10,
            api_base=LITELLM_PROXY_URL,
            api_key=LITELLM_API_KEY,
        )

        raw = response.choices[0].message.content.strip().lower()
        intent = raw.replace(".", "").replace("'", "").replace('"', "").strip()

        if intent not in _ALLOWED_INTENTS:
            # Try partial match for robustness
            for allowed in _ALLOWED_INTENTS:
                if allowed in intent:
                    intent = allowed
                    break
            else:
                intent = "qa"

    except Exception as e:
        logger.error("Error in router_node: %s", e, exc_info=True)
        intent = "qa"

    return {"intent": intent}

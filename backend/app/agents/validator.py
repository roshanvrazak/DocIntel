import os
import litellm
import logging
import re
from .state import DocIntelState

# Point to LiteLLM Proxy if available
LITELLM_PROXY_URL = os.getenv("LITELLM_PROXY_URL", "http://litellm:4000")

logger = logging.getLogger(__name__)

async def validator_node(state: DocIntelState) -> DocIntelState:
    """
    Validates the generated response for faithfulness and grounding.
    Uses Gemini 1.5 Flash for scoring.
    """
    draft_response = state.get("draft_response", "")
    retrieved_chunks = state.get("retrieved_chunks", [])
    retry_count = state.get("retry_count", 0)
    
    logger.info(f"Validator node checking faithfulness. Retry count: {retry_count}")
    
    if not draft_response:
        return {"faithfulness_score": 0.0, "retry_count": retry_count}
    
    context_text = "\n\n".join([f"Chunk {i+1}:\n{chunk.get('content')}" for i, chunk in enumerate(retrieved_chunks)])
    
    system_prompt = "Score faithfulness of the response vs context. Return ONLY a number 0.0-1.0."

    try:
        response = await litellm.acompletion(
            model="gemini/gemini-1.5-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context_text}\n\nResponse:\n{draft_response}"}
            ],
            api_base=LITELLM_PROXY_URL,
            api_key="sk-dummy",
            temperature=0.0,
            max_tokens=10
        )
        
        score_text = response.choices[0].message.content.strip()
        
        # Robust parsing using regex to find the first numeric value
        match = re.search(r"(\d+(\.\d+)?)", score_text)
        if match:
            try:
                faithfulness_score = float(match.group(1))
            except ValueError:
                logger.error(f"Regex matched but float conversion failed for: {match.group(1)}")
                faithfulness_score = 0.5
        else:
            logger.error(f"Failed to find numeric faithfulness score in response: {score_text}")
            faithfulness_score = 0.5 # Default to mid-point on parse error
            
    except Exception as e:
        logger.error(f"Error in validator_node: {str(e)}")
        faithfulness_score = 0.0
        
    # Increment retry count for the NEXT potential run
    new_retry_count = retry_count + 1
    
    # Consistent threshold: pass if score is 0.8 or higher
    final_response = draft_response if faithfulness_score >= 0.8 else None
    
    return {
        "faithfulness_score": faithfulness_score,
        "final_response": final_response,
        "retry_count": new_retry_count
    }

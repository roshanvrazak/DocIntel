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
    
    system_prompt = f"""
    You are an objective auditor of AI-generated responses. Your task is to score the faithfulness of a response based on provided document chunks.
    
    Grounding Context:
    {context_text}
    
    Evaluate the following response:
    {draft_response}
    
    Provide a faithfulness score between 0.0 and 1.0, where 1.0 means every claim in the response is fully supported by the context, and 0.0 means the response is entirely hallucinated or unsupported.
    Return ONLY the numeric score (e.g., 0.85). No other text.
    """
    
    try:
        response = await litellm.acompletion(
            model="gemini/gemini-1.5-flash",
            messages=[
                {"role": "system", "content": system_prompt},
            ],
            api_base=LITELLM_PROXY_URL,
            temperature=0.0
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

import re
import logging
import litellm
from .state import DocIntelState
from backend.app.config import LITELLM_PROXY_URL, LITELLM_API_KEY, FAITHFULNESS_THRESHOLD

logger = logging.getLogger(__name__)


async def _score_with_llm(system_prompt: str, user_content: str) -> float:
    """Call Gemini Flash and parse a 0.0-1.0 numeric score."""
    response = await litellm.acompletion(
        model="gemini/gemini-1.5-flash",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        api_base=LITELLM_PROXY_URL,
        api_key=LITELLM_API_KEY,
        temperature=0.0,
        max_tokens=10,
    )
    score_text = response.choices[0].message.content.strip()
    match = re.search(r"(\d+(\.\d+)?)", score_text)
    if match:
        try:
            return min(1.0, float(match.group(1)))
        except ValueError:
            pass
    logger.warning("Could not parse score from LLM output: %s", score_text)
    return 0.5


async def validator_node(state: DocIntelState) -> DocIntelState:
    """
    Validates the generated response for faithfulness and answer relevancy.
    Uses Gemini 1.5 Flash for both scores.
    """
    draft_response = state.get("draft_response", "")
    retrieved_chunks = state.get("retrieved_chunks", [])
    retry_count = state.get("retry_count", 0)
    query = state.get("query", "")

    logger.info("Validator checking response. Retry count: %d", retry_count)

    if not draft_response:
        return {"faithfulness_score": 0.0, "answer_relevancy_score": 0.0, "retry_count": retry_count}

    context_text = "\n\n".join(
        [f"Chunk {i+1}:\n{chunk.get('content', '')}" for i, chunk in enumerate(retrieved_chunks)]
    )

    faithfulness_score = 0.0
    answer_relevancy_score = 0.0

    try:
        faithfulness_score = await _score_with_llm(
            system_prompt="Score the faithfulness of the response vs the context (0.0-1.0). Return ONLY a number.",
            user_content=f"Context:\n{context_text}\n\nResponse:\n{draft_response}",
        )
    except Exception as e:
        logger.error("Error scoring faithfulness: %s", str(e), exc_info=True)
        faithfulness_score = 0.0

    try:
        answer_relevancy_score = await _score_with_llm(
            system_prompt="Score how well the response answers the question (0.0-1.0). Return ONLY a number.",
            user_content=f"Question: {query}\n\nResponse:\n{draft_response}",
        )
    except Exception as e:
        logger.error("Error scoring answer relevancy: %s", str(e), exc_info=True)
        answer_relevancy_score = 0.5

    new_retry_count = retry_count + 1
    final_response = draft_response if faithfulness_score >= FAITHFULNESS_THRESHOLD else None

    logger.info(
        "Validator scores — faithfulness: %.2f, relevancy: %.2f, passed: %s",
        faithfulness_score,
        answer_relevancy_score,
        final_response is not None,
    )

    return {
        "faithfulness_score": faithfulness_score,
        "answer_relevancy_score": answer_relevancy_score,
        "final_response": final_response,
        "retry_count": new_retry_count,
    }

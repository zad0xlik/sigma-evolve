import logging
import os
from typing import List, Optional

from app.utils.prompts import MEMORY_CATEGORIZATION_PROMPT
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

# Lazy initialization - don't create client at module load time
_openai_client: Optional[OpenAI] = None


def get_openai_client() -> OpenAI:
    """Get or create OpenAI client with provider-based configuration."""
    global _openai_client
    
    if _openai_client is not None:
        return _openai_client
    
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    if provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is required when LLM_PROVIDER=openrouter")
        _openai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
    elif provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        _openai_client = OpenAI(
            base_url=base_url,
            api_key="ollama"  # Ollama doesn't require API key
        )
    else:
        # Default: direct OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        _openai_client = OpenAI(api_key=api_key)
    
    return _openai_client


def get_model_name() -> str:
    """Get model name based on provider configuration."""
    model = os.getenv("MODEL")
    if model:
        return model
    
    # Provider-specific defaults
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "openrouter":
        return "openai/gpt-4o-mini"
    elif provider == "ollama":
        return "llama3.2"
    else:
        return "gpt-4o-mini"


class MemoryCategories(BaseModel):
    categories: List[str]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=15))
def get_categories_for_memory(memory: str) -> List[str]:
    try:
        client = get_openai_client()
        model = get_model_name()
        
        messages = [
            {"role": "system", "content": MEMORY_CATEGORIZATION_PROMPT},
            {"role": "user", "content": memory}
        ]

        # Try structured output parsing first (works with OpenAI and some models)
        try:
            completion = client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=MemoryCategories,
                temperature=0
            )
            parsed: MemoryCategories = completion.choices[0].message.parsed
            return [cat.strip().lower() for cat in parsed.categories]
        except Exception as parse_error:
            # Fallback to regular completion for providers that don't support structured output
            logging.debug(f"Structured output failed, falling back to regular completion: {parse_error}")
            
            # Add JSON instruction to prompt
            json_prompt = f"{MEMORY_CATEGORIZATION_PROMPT}\n\nRespond with a JSON object containing a 'categories' array of strings."
            messages[0]["content"] = json_prompt
            
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0
            )
            
            import json
            response_text = completion.choices[0].message.content
            # Try to parse JSON from response
            try:
                data = json.loads(response_text)
                categories = data.get("categories", [])
            except json.JSONDecodeError:
                # Try to extract categories from text
                logging.warning(f"Could not parse JSON response, returning empty categories")
                categories = []
            
            return [cat.strip().lower() for cat in categories if isinstance(cat, str)]

    except Exception as e:
        logging.error(f"[ERROR] Failed to get categories: {e}")
        raise

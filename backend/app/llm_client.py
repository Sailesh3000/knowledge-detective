import logging
import requests
from app.config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Dedicated LLM client wrapper for Fireworks AI cloud inference.
    """
    def __init__(self):
        self.api_key = settings.FIREWORKS_API_KEY
        self.base_url = settings.FIREWORKS_BASE_URL
        self.model = settings.FIREWORKS_MODEL

    def generate(
        self, 
        prompt: str, 
        system_instruction: str = None, 
        json_format: bool = False, 
        temperature: float = 0.0
    ) -> str:
        """
        Queries Fireworks AI chat completions API.
        """
        if not self.api_key:
            # Let's read from settings again in case env was loaded/updated dynamically
            self.api_key = settings.FIREWORKS_API_KEY
            if not self.api_key:
                logger.error("FIREWORKS_API_KEY is not configured! Cloud inference will fail.")
                raise ValueError(
                    "FIREWORKS_API_KEY is missing. Please configure it in your .env file."
                )

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096,
        }

        if json_format:
            payload["response_format"] = {"type": "json_object"}

        logger.info(f"Querying Fireworks AI model '{self.model}'...")
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=90.0)
            response.raise_for_status()
            
            result = response.json()
            choices = result.get("choices", [])
            if not choices:
                logger.warning("Fireworks AI returned an empty completions list.")
                return ""
            
            content = choices[0].get("message", {}).get("content", "").strip()
            return content
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying Fireworks AI: {e}")
            raise e

# Singleton instance
llm_client = LLMClient()

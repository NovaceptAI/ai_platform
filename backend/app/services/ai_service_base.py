# app/services/ai_service_base.py
import os
import json
import logging
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
import openai
import time

log = logging.getLogger(__name__)

class AIServiceBase(ABC):
    """
    Base class for AI-powered services that use OpenAI for analysis.
    Provides common functionality for API calls, prompt management, and response parsing.
    Compatible with openai==0.28 API.
    """
    
    def __init__(self):
        self.service_name = "ai_service"  # Override in subclasses
        self._current_endpoint = None
        self._setup_openai_client()
        
    def _setup_openai_client(self):
        """Initialize Azure OpenAI client using the key manager."""
        try:
            # Use the existing key manager for endpoint rotation
            from app.services.openai_key_manager import key_manager
            
            # Get the next available API key and endpoint
            api_key, api_base, index = key_manager.get_next()
            
            if not api_key or not api_base:
                raise ValueError("No valid Azure OpenAI endpoints configured in key manager")
            
            self._current_endpoint = api_base
            
            # Configure openai library (v0.28 style)
            openai.api_type = "azure"
            openai.api_base = api_base
            openai.api_key = api_key
            openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
            
            log.info(f"[{self.service_name}] Initialized Azure OpenAI client with endpoint #{index}: {api_base}")
            
        except Exception as e:
            log.error(f"[{self.service_name}] Failed to initialize OpenAI client: {e}")
            raise
    
    def _make_openai_call(self, messages: List[Dict[str, str]], model: str = None, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        """
        Make a call to OpenAI API with retry logic and error handling.
        Compatible with openai==0.28 API.
        
        Args:
            messages: List of message dictionaries for the conversation
            model: Model name to use (defaults to gpt-4)
            temperature: Randomness in response (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            
        Returns:
            Response content as string
        """
        if not model:
            model = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
        
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                log.debug(f"[{self.service_name}] Making OpenAI call (attempt {attempt + 1}/{max_retries})")
                
                response = openai.ChatCompletion.create(
                    engine=model,  # Use engine for Azure OpenAI v0.28
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                content = response.choices[0].message.content
                log.debug(f"[{self.service_name}] OpenAI call successful")
                return content
                
            except openai.error.RateLimitError as e:
                delay = base_delay * (2 ** attempt) + (attempt * 0.5)  # Simple jitter without random
                log.warning(f"[{self.service_name}] Rate limit hit, retrying in {delay:.2f}s: {e}")
                time.sleep(delay)
                
            except openai.error.APIError as e:
                if attempt == max_retries - 1:
                    log.error(f"[{self.service_name}] OpenAI API error after {max_retries} attempts: {e}")
                    raise
                delay = base_delay * (2 ** attempt)
                log.warning(f"[{self.service_name}] API error, retrying in {delay}s: {e}")
                time.sleep(delay)
                
            except Exception as e:
                log.error(f"[{self.service_name}] Unexpected error in OpenAI call: {e}")
                raise
        
        raise Exception(f"Failed to get response from OpenAI after {max_retries} attempts")
    
    def _expects_json_response(self, messages: List[Dict[str, str]]) -> bool:
        """
        Check if the prompt expects a JSON response.
        Override in subclasses for more sophisticated logic.
        """
        prompt_text = " ".join([msg.get("content", "") for msg in messages]).lower()
        json_indicators = ["json", "format:", "structure:", "{", "return a", "respond with"]
        return any(indicator in prompt_text for indicator in json_indicators)
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON response from OpenAI with error handling.
        
        Args:
            response: Raw response string from OpenAI
            
        Returns:
            Parsed JSON as dictionary
        """
        try:
            # Try direct JSON parsing
            return json.loads(response)
        except json.JSONDecodeError:
            try:
                # Try to extract JSON from markdown code blocks
                if "```json" in response:
                    start = response.find("```json") + 7
                    end = response.find("```", start)
                    json_str = response[start:end].strip()
                    return json.loads(json_str)
                elif "```" in response:
                    start = response.find("```") + 3
                    end = response.find("```", start)
                    json_str = response[start:end].strip()
                    return json.loads(json_str)
                else:
                    # Try to find JSON-like content
                    start = response.find("{")
                    end = response.rfind("}") + 1
                    if start != -1 and end > start:
                        json_str = response[start:end]
                        return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        log.error(f"[{self.service_name}] Failed to parse JSON response: {response[:200]}...")
        return {"error": "Failed to parse JSON response", "raw_response": response}
    
    def _build_system_prompt(self, task_description: str, output_format: str = None) -> str:
        """
        Build a system prompt for the AI service.
        
        Args:
            task_description: Description of the task to perform
            output_format: Optional format specification for the output
            
        Returns:
            Formatted system prompt
        """
        prompt = f"""You are an expert AI assistant specialized in {task_description}.

Your task is to analyze the provided content and generate high-quality, actionable results.

Key guidelines:
- Be thorough and analytical in your approach
- Provide specific, actionable insights
- Maintain consistency in your analysis
- Focus on practical value for users
- Handle edge cases gracefully
"""
        
        if output_format:
            prompt += f"\n\nOutput format: {output_format}"
        
        return prompt
    
    def _build_analysis_prompt(self, content: str, specific_instructions: str) -> str:
        """
        Build an analysis prompt for content processing.
        
        Args:
            content: Content to analyze
            specific_instructions: Specific instructions for this analysis
            
        Returns:
            Formatted analysis prompt
        """
        return f"""Please analyze the following content:

{content}

Specific instructions:
{specific_instructions}

Please provide a comprehensive analysis following the specified format."""
    
    def _validate_response(self, response: Dict[str, Any], required_keys: List[str]) -> bool:
        """
        Validate that response contains required keys.
        
        Args:
            response: Response dictionary to validate
            required_keys: List of required keys
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(response, dict):
            return False
        
        return all(key in response for key in required_keys)
    
    def _safe_get(self, data: Dict[str, Any], key: str, default: Any = None) -> Any:
        """
        Safely get a value from a dictionary with fallback.
        
        Args:
            data: Dictionary to get value from
            key: Key to look for
            default: Default value if key not found
            
        Returns:
            Value or default
        """
        return data.get(key, default) if isinstance(data, dict) else default
    
    def _chunk_content(self, content: str, max_chunk_size: int = 8000) -> List[str]:
        """
        Split content into manageable chunks for processing.
        
        Args:
            content: Content to chunk
            max_chunk_size: Maximum size per chunk
            
        Returns:
            List of content chunks
        """
        if len(content) <= max_chunk_size:
            return [content]
        
        chunks = []
        words = content.split()
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word) + 1  # +1 for space
            if current_size + word_size > max_chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_size = word_size
            else:
                current_chunk.append(word)
                current_size += word_size
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def _merge_analysis_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge results from multiple chunks into a single result.
        Override in subclasses for specific merging logic.
        
        Args:
            results: List of analysis results to merge
            
        Returns:
            Merged result dictionary
        """
        if not results:
            return {}
        
        if len(results) == 1:
            return results[0]
        
        # Default merging strategy - combine lists and average numbers
        merged = {}
        
        for result in results:
            for key, value in result.items():
                if key not in merged:
                    merged[key] = value
                elif isinstance(value, list) and isinstance(merged[key], list):
                    merged[key].extend(value)
                elif isinstance(value, (int, float)) and isinstance(merged[key], (int, float)):
                    merged[key] = (merged[key] + value) / 2
                elif isinstance(value, dict) and isinstance(merged[key], dict):
                    merged[key].update(value)
        
        return merged
    
    def _log_analysis_start(self, operation: str, data_info: str):
        """Log the start of an analysis operation."""
        log.info(f"[{self.service_name}] Starting {operation} for {data_info}")
    
    def _log_analysis_complete(self, operation: str, result_summary: str):
        """Log the completion of an analysis operation."""
        log.info(f"[{self.service_name}] Completed {operation}: {result_summary}")
    
    def _log_analysis_error(self, operation: str, error: Exception):
        """Log an analysis error."""
        log.error(f"[{self.service_name}] Error in {operation}: {error}")
    
    # Abstract methods to be implemented by subclasses
    @abstractmethod
    def get_service_info(self) -> Dict[str, Any]:
        """
        Return information about this service.
        
        Returns:
            Dictionary with service information
        """
        pass

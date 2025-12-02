"""
Google Gemini Client for LLM and Embeddings
"""
import os
from typing import List, Optional, Dict, Any
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings


class GoogleGeminiClient:
    """Client for Google Gemini API"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash",
        temperature: float = 0.7
    ):
        """
        Initialize Google Gemini client
        
        Args:
            api_key: Google Gemini API key (from config file)
            model: Model name (default: gemini-2.0-flash)
            temperature: Temperature for generation (default: 0.7)
        """
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("Google Gemini API key required. Set api_key in agent_config.json.")
        
        self.model_name = model
        self.temperature = temperature
        
        # Initialize Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model)
        
        # Initialize embeddings
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=self.api_key
        )
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text using Gemini with retry logic for quota handling
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text
        """
        import time
        import re
        
        generation_config = {
            "temperature": kwargs.get("temperature", self.temperature),
            "max_output_tokens": kwargs.get("max_tokens", 8192),
        }
        
        max_retries = 3
        retry_delay = 2  # Start with 2 seconds
        
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
                return response.text
                
            except Exception as e:
                error_str = str(e)
                
                # Check if it's a quota error
                if 'quota' in error_str.lower() or '429' in error_str:
                    if attempt < max_retries - 1:
                        # Try to extract retry delay from error
                        retry_match = re.search(r'retry.*?(\d+)', error_str, re.IGNORECASE)
                        if retry_match:
                            retry_delay = int(retry_match.group(1)) + 1
                        else:
                            retry_delay = retry_delay * 2  # Exponential backoff
                        
                        print(f"  ⚠ Quota limit hit, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    else:
                        raise Exception(f"API quota exceeded after {max_retries} attempts. Please wait and try again later.")
                else:
                    # Not a quota error, raise immediately
                    raise
    
    def generate_structured(self, prompt: str, response_format: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate structured response
        
        Args:
            prompt: Input prompt
            response_format: Expected response format (JSON schema)
            
        Returns:
            Structured response as dictionary
        """
        if response_format:
            # Add format instruction to prompt
            format_instruction = f"\n\nRespond in the following JSON format: {response_format}"
            prompt = prompt + format_instruction
        
        response_text = self.generate(prompt)
        
        # Try to parse as JSON
        try:
            import json
            return json.loads(response_text)
        except:
            return {"raw_response": response_text}
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for text
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector
        """
        return self.embeddings.embed_query(text)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with error handling
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
            
        Raises:
            Exception: If embedding fails (e.g., quota exceeded)
        """
        try:
            return self.embeddings.embed_documents(texts)
        except Exception as e:
            error_msg = str(e)
            if 'quota' in error_msg.lower() or '429' in error_msg:
                raise Exception(f"Embedding quota exceeded: {error_msg}")
            raise
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Chat completion interface
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters
            
        Returns:
            Response text
        """
        # Convert messages to Gemini format
        chat = self.model.start_chat()
        
        for message in messages[:-1]:  # All but last message
            if message["role"] == "user":
                chat.send_message(message["content"])
            elif message["role"] == "assistant":
                # Gemini doesn't support assistant messages in history directly
                # We'll include them in the prompt
                pass
        
        # Send last message
        response = chat.send_message(messages[-1]["content"])
        return response.text


import os
import json
import logging
from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types
import numpy as np
import backend.constant as constant
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class GeminiClient:
    """
    Unified Gemini client supporting both:
    1. Text generation (e.g., classification, reasoning)
    2. Function calling (structured, using Gemini Tools API)
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key not provided and GEMINI_API_KEY not set.")

        os.environ["GOOGLE_API_KEY"] = self.api_key
        self.client = genai.Client()
        self.model = model

    # -----------------------------
    # 🧠 1. TEXT GENERATION
    # -----------------------------
    def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        parse_json: bool = False
    ) -> Any:
        """
        Calls Gemini for text generation.
        Useful for Query Classification, Reasoning, Explanations, etc.
        """
        selected_model = model or self.model
        try:
            response = self.client.models.generate_content(
                model=selected_model,
                contents=prompt
            )

            text = response.text.strip() if response.text else ""
            if parse_json:
                cleaned = text.strip("`").replace("json", "").strip()
                return json.loads(cleaned)
            return text

        except Exception as e:
            logger.error(f"❌ Text generation failed: {e}", exc_info=True)
            return None

    # -----------------------------
    # ⚡ 2. FUNCTION CALLING
    # -----------------------------
    def function_call(
        self,
        user_query: str,
        function_schema: List[Dict[str, Any]],
        system_instruction: str,
        entities: List[str],
        chat_history: dict[Any],
        classification_metadata:dict[Any],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calls Gemini with function declarations to map natural language
        to structured function calls.
        """
        selected_model = model or self.model

        try:
            function_calls = []
            # Define tools from function schema
            tools = types.Tool(function_declarations=function_schema)

            config = types.GenerateContentConfig(tools=[tools])
            config = types.GenerateContentConfig(
            tools=[tools],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
                # Force the model to call 'any' function, instead of chatting.
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(mode='ANY')
                ),
            )

            # formatted_prompt = f"{system_instruction}\n UserQuery \n \n {user_query}"
            formatted_prompt = system_instruction \
            .replace("{{ENTITIES}}", str(entities)) \
            .replace("{{CLASSIFICATION_METADATA}}", str(classification_metadata)) \
            .replace("{{CURRENT_QUERY}}", user_query)
            
            if formatted_prompt is None:
                return {"status": "error", "message": "Prompt is None"}
            # Call Gemini with tools
            response = self.client.models.generate_content(
                model=selected_model,
                contents=formatted_prompt,
                config=config
            )
            # Parse function call if present
            candidate = response.candidates[0]
            parts = candidate.content.parts
            
            if parts:
                for part in parts:
                    if part.function_call:
                        fn_call = part.function_call
                        fn_name = fn_call.name
                        fn_args = dict(fn_call.args)
                        function_calls.append({"name": fn_name, "arguments": fn_args})
                    
            # if parts and parts[0].function_call:
            #     fn_call = parts[0].function_call
            #     fn_name = fn_call.name
            #     fn_args = dict(fn_call.args)
                
                logger.info(f"Function call detected: {fn_name} with args {fn_args}")
                return {
                    "status": "success",
                    "function_calls": function_calls
                }

            # If no function call, fallback to normal text
            logger.warning("No function call detected in Gemini response.")
            return {"status": "no_function_call", "text": response.text}

        except Exception as e:
            logger.error(f"Function calling failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
        
    

    def get_gemini_embedding(self, text: str, task: str = "retrieval_document", model = "models/embedding-001"):
        """
        Generate Gemini embeddings for a given text with proper error handling.
        
        Args:
            text (str): The input text to embed.
            task (str): One of ["retrieval_document", "retrieval_query", "semantic_similarity"].
        
        Returns:
            list[float]: Embedding vector if successful, empty list otherwise.
        """
        if not text or not isinstance(text, str):
            logger.warning("Invalid input text for embedding.")
            return []

        # Map task to Gemini config
        task_map = {
            "retrieval_document": "RETRIEVAL_DOCUMENT",
            "retrieval_query": "RETRIEVAL_QUERY",
            "semantic_similarity": "SEMANTIC_SIMILARITY"
        }
        task_type = task_map.get(task.lower(), "SEMANTIC_SIMILARITY")

        try:
            time.sleep(60)
            response = self.client.models.embed_content(
                model=model,
                contents=text,
                config=types.EmbedContentConfig(task_type=task_type)
            ).embeddings

            if not response or not isinstance(response[0].values, list):
                logger.error(f"Invalid embedding response for text: {text[:80]}...")
                return []

            return response[0].values

        except Exception as e:
            logger.error(f"Unexpected error during embedding: {e}", exc_info=True)
            return []


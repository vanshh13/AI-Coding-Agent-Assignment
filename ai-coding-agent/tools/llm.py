import json
from pathlib import Path
from typing import Any, Dict, Optional
from openai import OpenAI
from jinja2 import Environment, FileSystemLoader
from config import Config

class LLMHelper:
    def __init__(self, config: Config = Config()) -> None:
        self.config = config
        self.client = OpenAI(
            api_key=self.config.LLM_API_KEY,
            base_url=self.config.LLM_BASE_URL
        )
        # Setup Jinja2 environment pointing to prompts folder
        prompts_dir = Path(__file__).parent.parent / "prompts"
        self.jinja_env = Environment(loader=FileSystemLoader(str(prompts_dir)))

    def render_prompt(self, template_name: str, context: Dict[str, Any]) -> str:
        """Renders prompt templates using Jinja2."""
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)

    def call_text(self, prompt: str, system_message: str = "You are a helpful software engineering assistant.") -> str:
        """Invokes chat completion returning plain text response."""
        response = self.client.chat.completions.create(
            model=self.config.MODEL_NAME,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=self.config.TEMPERATURE
        )
        return response.choices[0].message.content or ""

    def call_json(self, prompt: str, system_message: str = "You are a helpful assistant that outputs JSON.") -> Dict[str, Any]:
        """Invokes chat completion with JSON mode, returning a parsed Python dictionary.
        Falls back to text parsing if JSON mode is unsupported by the model.
        """
        raw_content = "{}"
        try:
            # Attempt native JSON mode
            response = self.client.chat.completions.create(
                model=self.config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=self.config.TEMPERATURE
            )
            raw_content = response.choices[0].message.content or "{}"
        except Exception as e:
            # Fallback for models/endpoints that don't support JSON mode (e.g. some older/smaller models)
            fallback_system = system_message + " Respond ONLY with a valid, parsable JSON object. Do not include markdown wraps unless needed."
            try:
                response = self.client.chat.completions.create(
                    model=self.config.MODEL_NAME,
                    messages=[
                        {"role": "system", "content": fallback_system},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.config.TEMPERATURE
                )
                raw_content = response.choices[0].message.content or "{}"
            except Exception as inner_e:
                raise RuntimeError(f"LLM API Call failed: {str(inner_e)}") from inner_e

        # Normalize and clean up response content
        clean_content = raw_content.strip()
        if clean_content.startswith("```"):
            # Strip markdown fences if present
            lines = clean_content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            clean_content = "\n".join(lines).strip()
            if clean_content.startswith("json"):
                clean_content = clean_content[4:].strip()

        # Extract only the first valid JSON object to ignore trailing braces/garbage
        extracted_content = extract_json_object(clean_content)

        try:
            return json.loads(extracted_content)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response", "raw": raw_content}

def extract_json_object(text: str) -> str:
    """Finds the first valid JSON object by finding the first '{' and matching '}'."""
    text = text.strip()
    start_idx = text.find('{')
    if start_idx == -1:
        return text

    brace_count = 0
    in_string = False
    escape = False
    
    for i in range(start_idx, len(text)):
        char = text[i]
        
        if char == '"' and not escape:
            in_string = not in_string
            
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return text[start_idx:i+1]
                    
        if char == '\\':
            escape = not escape
        else:
            escape = False
            
    return text[start_idx:]



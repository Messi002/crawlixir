"""Ollama integration for extraction and text generation."""

import json
import requests


class AI:
    """Talks to a local Ollama instance for extraction, summarization, and email drafting."""

    # Max characters to send to the model. Keeps prompts from overwhelming a CPU-bound LLM.
    MAX_CONTENT_CHARS = 4000

    def __init__(self, model="llama3.2", base_url="http://127.0.0.1:11434"):
        self.model = model
        self.base_url = base_url

    def _truncate(self, text, max_chars=None):
        """Trim text to a reasonable size so the model doesn't choke."""
        limit = max_chars or self.MAX_CONTENT_CHARS
        if len(text) <= limit:
            return text
        return text[:limit] + "\n\n[...truncated]"

    def _generate(self, prompt, system=None):
        """Send a prompt to Ollama using streaming so we never hit a read timeout."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
        }
        if system:
            payload["system"] = system

        resp = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            stream=True,
            timeout=(10, 600),  # 10s to connect, 10min for first token (model loading)
        )
        resp.raise_for_status()

        result = []
        for line in resp.iter_lines():
            if line:
                chunk = json.loads(line)
                token = chunk.get("response", "")
                result.append(token)
                if chunk.get("done"):
                    break
        return "".join(result)

    def extract(self, content, prompt):
        """
        Pull specific info out of scraped content using the LLM.

        content: the scraped text/markdown.
        prompt: what to look for (e.g. "job title, company, and requirements").
        """
        system = (
            "You are a data extraction assistant. Extract the requested information "
            "from the provided content. Be precise and structured in your output."
        )
        full_prompt = f"Content:\n{self._truncate(content)}\n\n---\n\nTask: {prompt}"
        return self._generate(full_prompt, system=system)

    def extract_json(self, content, prompt, fields):
        """
        Same as extract(), but tries to return structured JSON.

        fields: list of field names you want in the output.
        Returns a dict if parsing works, raw string if it doesn't.
        """
        system = (
            "You are a data extraction assistant. Extract information and return ONLY "
            "valid JSON with the specified fields. No extra text, just JSON."
        )
        fields_str = ", ".join(fields)
        full_prompt = (
            f"Content:\n{self._truncate(content)}\n\n---\n\n"
            f"Extract the following fields as JSON: {fields_str}\n"
            f"Additional instructions: {prompt}\n"
            f"Return ONLY valid JSON."
        )
        raw = self._generate(full_prompt, system=system)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(raw[start:end])
                except json.JSONDecodeError:
                    pass
            return raw

    def summarize(self, content, style="concise"):
        """Summarize scraped content."""
        system = f"You are a summarization assistant. Provide a {style} summary."
        return self._generate(f"Summarize this:\n\n{self._truncate(content, 6000)}", system=system)

    def draft_email(self, job_content, cv_content, recipient_email=None, extra_instructions=""):
        """
        Write a job application email from a posting and a CV.

        Returns a dict with 'subject' and 'body'.
        """
        system = (
            "You are a professional email writer. Write a compelling job application "
            "email that highlights relevant experience from the CV that matches the "
            "job requirements. Be professional but personable. Keep it concise."
        )
        prompt = (
            f"Job Posting:\n{self._truncate(job_content)}\n\n---\n\n"
            f"My CV/Resume:\n{self._truncate(cv_content)}\n\n---\n\n"
            f"Write a job application email with a subject line and body.\n"
            f"Format your response as:\nSUBJECT: <subject>\n\nBODY:\n<email body>\n"
        )
        if extra_instructions:
            prompt += f"\nAdditional instructions: {extra_instructions}"

        raw = self._generate(prompt, system=system)

        # Parse subject and body
        subject = ""
        body = raw
        if "SUBJECT:" in raw:
            parts = raw.split("BODY:", 1)
            subject = parts[0].replace("SUBJECT:", "").strip()
            body = parts[1].strip() if len(parts) > 1 else raw

        return {"subject": subject, "body": body}

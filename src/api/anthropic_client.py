import json
import os
import anthropic
from typing import Dict
import httpx

class AnthropicClient:
    """Client for interacting with the Anthropic API."""
    
    def __init__(self, credentials_path: str = "config/credentials.json"):
        """Initialize the Anthropic API client."""
        self.credentials = self._load_credentials(credentials_path)
        self.api_key = self.credentials["anthropic"]["api_key"]
        self.model = self.credentials["anthropic"]["model"]
        
        # Create a custom HTTP client without proxy settings
        http_client = httpx.Client(
            timeout=600.0,
            follow_redirects=True
        )
        
        # Initialize the Anthropic client with our custom HTTP client
        # This avoids the proxies parameter issue
        self.client = anthropic.Anthropic(
            api_key=self.api_key,
            http_client=http_client
        )
    
    def _load_credentials(self, credentials_path: str) -> Dict:
        """Load API credentials from the specified JSON file."""
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"Credentials file not found at {credentials_path}")
        
        with open(credentials_path, 'r') as f:
            return json.load(f)
    
    def send_message(self, prompt: str, max_tokens: int = 1000):
        """Send a message to Claude and get a response."""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message
        except Exception as e:
            print(f"Error sending message to Claude: {e}")
            raise
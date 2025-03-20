from src.api.anthropic_client import AnthropicClient

def test_api_connection():
    try:
        # Initialize the client
        client = AnthropicClient()
        print("AnthropicClient initialized successfully!")
        
        # Test sending a simple message
        prompt = "Hello, Claude. Please respond with a simple greeting."
        print(f"Sending test message to Claude: '{prompt}'")
        
        message = client.send_message(prompt, max_tokens=100)
        print("Message sent and response received successfully!")
        print(f"Message ID: {message.id}")
        print(f"Model used: {message.model}")
        
        # Print the response text
        print("\n--- Claude's Response ---")
        for block in message.content:
            if block.type == "text":
                print(block.text)
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_api_connection()
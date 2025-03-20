# Claude API Interaction - Enhanced.ipynb

# Cell 1: Import dependencies and set up the environment
import sys
import os
import json
import glob
from datetime import datetime
import re

# Add the project root to the Python path to import your modules
# Adjust the path if needed to match your project structure
sys.path.append(os.path.abspath(".."))
print("Project path added to system path.")

from src.api.anthropic_client import AnthropicClient

# Cell 2: Initialize the client and conversation state
client = AnthropicClient()
print(f"AnthropicClient initialized with model: {client.model}")

# Initialize conversation state
conversation_state = {
    "messages": [],  # Will store the conversation history
    "summary": "",   # Will store the latest conversation summary
    "shared_files": [],  # Will track which files have been shared
    "last_updated": datetime.now().isoformat(),
}

# Cell 3: Function to send a message to Claude with conversation history
def ask_claude(prompt, include_history=True, include_summary=True, max_tokens=1000):
    """
    Send a message to Claude with optional conversation history and summary.
    
    Args:
        prompt (str): The new prompt to send to Claude
        include_history (bool): Whether to include message history
        include_summary (bool): Whether to include the conversation summary
        max_tokens (int): Maximum tokens in the response
        
    Returns:
        dict: Formatted response from Claude
    """
    full_prompt = ""
    
    # Add summary if requested and available
    if include_summary and conversation_state["summary"]:
        full_prompt += "# Previous Conversation Summary\n"
        full_prompt += conversation_state["summary"]
        full_prompt += "\n\n"
    
    # Add conversation history if requested
    if include_history and conversation_state["messages"]:
        full_prompt += "# Previous Messages\n"
        # Include up to last 3 message pairs to avoid token limits
        for i in range(max(0, len(conversation_state["messages"])-6), len(conversation_state["messages"])):
            msg = conversation_state["messages"][i]
            full_prompt += f"{'Human' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}\n\n"
        
        full_prompt += "# New Question\n"
    
    # Add the new prompt
    full_prompt += prompt
    
    print(f"Sending to Claude (with{'out' if not include_history else ''} history, with{'out' if not include_summary else ''} summary)")
    
    # Get response from Claude
    response = client.send_message(full_prompt, max_tokens=max_tokens)
    
    # Extract text content
    text_content = ""
    for block in response.content:
        if block.type == "text":
            text_content += block.text
    
    # Update conversation history
    conversation_state["messages"].append({"role": "user", "content": prompt})
    conversation_state["messages"].append({"role": "assistant", "content": text_content})
    conversation_state["last_updated"] = datetime.now().isoformat()
    
    return {
        "message_id": response.id,
        "model": response.model,
        "content": text_content,
        "tokens_used": len(full_prompt.split()) // 3  # Rough estimate of tokens
    }

# Cell 4: Function to extract and save markdown content from Claude's response
def extract_markdown(response_text):
    """Extract markdown sections from Claude's response text"""
    # Look for markdown blocks between triple backticks
    code_blocks = re.findall(r'```(?:markdown)?\s*([\s\S]*?)```', response_text)
    
    # Also look for potential markdown sections that start with headings
    heading_blocks = re.findall(r'(?:^|\n)# (.*?)(?:\n|$)([\s\S]*?)(?=(?:\n# |$))', response_text)
    
    artifacts = []
    
    # Process code blocks
    for i, block in enumerate(code_blocks):
        artifacts.append({
            "type": "markdown_code_block",
            "content": block.strip(),
            "index": i
        })
    
    # Process heading sections
    for i, (heading, content) in enumerate(heading_blocks):
        # Skip if this content is already included in a code block
        if not any(content.strip() in block for block in code_blocks):
            artifacts.append({
                "type": "markdown_section",
                "heading": heading.strip(),
                "content": f"# {heading.strip()}\n\n{content.strip()}",
                "index": i
            })
    
    return artifacts

def save_artifact(artifact, folder="extracted_artifacts"):
    """Save an artifact to a file"""
    # Create the folder if it doesn't exist
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    # Generate filename based on heading or index
    if artifact['type'] == 'markdown_section' and 'heading' in artifact:
        # Clean up the heading to make it a valid filename
        filename = "".join(c if c.isalnum() or c in " -_" else "_" for c in artifact['heading'])
        filename = filename.replace(" ", "_").lower()
    else:
        filename = f"artifact_{artifact['index']}"
    
    # Add extension and ensure uniqueness
    base_filename = os.path.join(folder, f"{filename}.md")
    final_filename = base_filename
    counter = 1
    
    while os.path.exists(final_filename):
        final_filename = os.path.join(folder, f"{filename}_{counter}.md")
        counter += 1
    
    # Write the content to the file
    with open(final_filename, 'w') as f:
        f.write(artifact['content'])
    
    return final_filename

# Cell 5: File and project management functions
def get_project_structure(root_dir='..', ignore_patterns=None):
    """
    Generate a summary of the project's file structure
    """
    if ignore_patterns is None:
        ignore_patterns = [
            '__pycache__', 
            '*.pyc', 
            '.git', 
            '.ipynb_checkpoints', 
            'venv',
            '*.egg-info'
        ]
    
    result = []
    
    for root, dirs, files in os.walk(root_dir):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if not any(re.match(pattern, d) for pattern in ignore_patterns)]
        
        level = root.replace(root_dir, '').count(os.sep)
        indent = ' ' * 4 * level
        result.append(f"{indent}{os.path.basename(root)}/")
        
        sub_indent = ' ' * 4 * (level + 1)
        for file in files:
            if not any(re.match(pattern, file) for pattern in ignore_patterns):
                result.append(f"{sub_indent}{file}")
    
    return '\n'.join(result)

def read_file_content(file_path):
    """Read and return the content of a file"""
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def include_file_in_prompt(file_path, max_length=None):
    """Format a file for inclusion in a prompt to Claude"""
    content = read_file_content(file_path)
    
    # Truncate if specified
    if max_length and len(content) > max_length:
        content = content[:max_length] + "\n...(truncated)..."
    
    # Format the file content for inclusion in prompt
    formatted = f"""
<file path="{file_path}">
```
{content}
```
</file>
"""
    return formatted

def share_files_with_claude(file_paths, prompt_prefix="Please review these files:", prompt_suffix=""):
    """Share multiple files with Claude and ask for analysis"""
    prompt = prompt_prefix + "\n\n"
    
    for file_path in file_paths:
        prompt += include_file_in_prompt(file_path)
        # Track that we've shared this file
        if file_path not in conversation_state["shared_files"]:
            conversation_state["shared_files"].append(file_path)
    
    prompt += "\n" + prompt_suffix
    
    return ask_claude(prompt)

# Cell 6: Summarization functions
def generate_conversation_summary():
    """Ask Claude to summarize the conversation so far"""
    if len(conversation_state["messages"]) < 2:
        print("Not enough conversation to summarize.")
        return
    
    # Gather recent conversation
    recent_convo = ""
    for i, msg in enumerate(conversation_state["messages"]):
        role = "Human" if msg["role"] == "user" else "Assistant"
        recent_convo += f"{role}: {msg['content']}\n\n"
    
    summary_prompt = f"""
Please provide a concise summary of our conversation so far. Focus on:
1. The main project goal (Claude Artifacts Automation)
2. Current progress and implementation details
3. Key decisions made
4. Current issues or questions being addressed

Here's the conversation to summarize:

{recent_convo}
"""
    
    # We don't include history/summary to avoid recursion
    response = ask_claude(summary_prompt, include_history=False, include_summary=False)
    
    # Save the summary
    conversation_state["summary"] = response["content"]
    print("Conversation summary updated.")
    
    return response["content"]

def save_conversation_state(filename="claude_conversation_state.json"):
    """Save the current conversation state to a file"""
    with open(filename, 'w') as f:
        json.dump(conversation_state, f, indent=2)
    print(f"Conversation state saved to {filename}")

def load_conversation_state(filename="claude_conversation_state.json"):
    """Load conversation state from a file"""
    global conversation_state
    try:
        with open(filename, 'r') as f:
            conversation_state = json.load(f)
        print(f"Conversation state loaded from {filename}")
    except FileNotFoundError:
        print(f"File {filename} not found. Using empty conversation state.")

# Cell 7: Test with a simple prompt
# Uncomment to run a test
# response = ask_claude("Hello Claude, what capabilities does this notebook provide for working with the Claude API?")
# print(f"\nMessage ID: {response['message_id']}")
# print(f"Model: {response['model']}")
# print("\n--- Claude's Response ---")
# print(response['content'])

# Cell 8: Example usage - sharing project files
# project_structure = get_project_structure()
# print(project_structure)

# Cell 9: Example of sharing multiple files and asking for analysis
# key_files = [
#    "../src/api/anthropic_client.py",
#    "../config/credentials.json"
# ]
# response = share_files_with_claude(
#    key_files, 
#    prompt_prefix="Please review these files from my Claude Artifacts Automation project:", 
#    prompt_suffix="What improvements would you suggest for the AnthropicClient class?"
# )
# print(response["content"])

# Cell 10: Generating and saving a summary
# summary = generate_conversation_summary()
# print("--- Conversation Summary ---")
# print(summary)
# save_conversation_state()

#!/usr/bin/env python3
"""Test OpenAI API connectivity"""

import os
import os
from openai import OpenAI

# Set API key from environment
api_key = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")

client = OpenAI(api_key=api_key)

try:
    print("Testing OpenAI connection...")
    
    # Test embedding
    response = client.embeddings.create(
        input="test",
        model="text-embedding-3-small"
    )
    
    print(f"✅ Embedding test successful! Length: {len(response.data[0].embedding)}")
    
    # Test chat
    chat_response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Say hello"}],
        max_tokens=10
    )
    
    print(f"✅ Chat test successful! Response: {chat_response.choices[0].message.content}")
    
except Exception as e:
    print(f"❌ Error: {e}")

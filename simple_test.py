#!/usr/bin/env python
"""
Simple test script for the multiagent_assistant chat_step function
"""
import json
from services.chatbot.multiagent_assistant import chat_step

# Test with candidate context for job applications
test_candidate_id = "test123"
test_message = "Show me this candidate's job applications"

print(f"Sending message: '{test_message}' with candidate_id: '{test_candidate_id}'")
response = chat_step(test_message, candidate_id=test_candidate_id)
print("\nResponse:")
print(response)

# Parse the JSON response
response_obj = json.loads(response)
print("\nParsed response:")
print(json.dumps(response_obj, indent=2))

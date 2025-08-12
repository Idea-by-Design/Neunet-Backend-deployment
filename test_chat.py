#!/usr/bin/env python
"""
Test script for the multiagent_assistant chat_step function
"""
import json
from services.chatbot.multiagent_assistant import chat_step

def test_candidate_context():
    """Test the candidate context handling in chat_step"""
    print("Testing candidate context handling...")
    
    # Test with candidate context for job applications
    test_candidate_id = "test123"
    test_message = "Show me this candidate's job applications"
    
    print(f"Sending message: '{test_message}' with candidate_id: '{test_candidate_id}'")
    response = chat_step(test_message, candidate_id=test_candidate_id)
    print("\nResponse:")
    print(response)
    
    # Parse the JSON response
    try:
        response_obj = json.loads(response)
        print("\nParsed response:")
        print(json.dumps(response_obj, indent=2))
        
        # Check if candidate context is included
        if "candidateId" in response_obj and response_obj["candidateId"] == test_candidate_id:
            print("\n✅ Candidate ID is correctly included in the response")
        else:
            print("\n❌ Candidate ID is missing or incorrect in the response")
            
        if "candidateResume" in response_obj:
            print("✅ Candidate resume is included in the response")
            
            # Check for LinkedIn and GitHub links
            if "contact" in response_obj["candidateResume"]:
                contact = response_obj["candidateResume"]["contact"]
                if "linkedin" in contact:
                    print(f"✅ LinkedIn link is included: {contact['linkedin']}")
                else:
                    print("❌ LinkedIn link is missing")
                    
                if "github" in contact:
                    print(f"✅ GitHub link is included: {contact['github']}")
                else:
                    print("❌ GitHub link is missing")
        else:
            print("❌ Candidate resume is missing in the response")
    except json.JSONDecodeError:
        print("❌ Response is not valid JSON")
    
    # Test with candidate context for general query
    test_message = "Tell me about this candidate's experience"
    print(f"\nSending message: '{test_message}' with candidate_id: '{test_candidate_id}'")
    response = chat_step(test_message, candidate_id=test_candidate_id)
    print("\nResponse:")
    print(response)
    
    # Parse the JSON response
    try:
        response_obj = json.loads(response)
        print("\nParsed response:")
        print(json.dumps(response_obj, indent=2))
        
        # Check if the response contains LinkedIn and GitHub links
        if "content" in response_obj:
            content = response_obj["content"]
            if "linkedin.com" in content.lower():
                print("✅ LinkedIn link is mentioned in the response content")
            else:
                print("❌ LinkedIn link is not mentioned in the response content")
                
            if "github.com" in content.lower():
                print("✅ GitHub link is mentioned in the response content")
            else:
                print("❌ GitHub link is not mentioned in the response content")
    except json.JSONDecodeError:
        print("❌ Response is not valid JSON")

if __name__ == "__main__":
    test_candidate_context()

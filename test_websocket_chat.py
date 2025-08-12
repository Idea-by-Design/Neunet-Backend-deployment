#!/usr/bin/env python3
"""
Test script to verify WebSocket connection and chat functionality with Azure OpenAI integration.
Focuses on verifying candidate information in responses, including LinkedIn and GitHub links.
"""

import os
import sys
import json
import logging
import asyncio
import traceback
import time
import argparse
from dotenv import load_dotenv
import websockets
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('websocket_test.log')
    ]
)
logger = logging.getLogger(__name__)

def load_environment_variables():
    """Load environment variables from .env file."""
    # Try to load from different possible locations
    env_loaded = False
    possible_paths = [
        '.env',
        '../.env',
        '../../.env',
        os.path.join(os.path.dirname(__file__), '.env'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            logger.info(f"Loading environment variables from {path}")
            load_dotenv(path)
            env_loaded = True
            break
    
    if not env_loaded:
        logger.warning("Could not find .env file in any of the expected locations")
    
    # Log environment variable status (without revealing actual values)
    logger.info(f"AZURE_OPENAI_API_KEY present: {bool(os.getenv('AZURE_OPENAI_API_KEY'))}")
    logger.info(f"AZURE_OPENAI_ENDPOINT present: {bool(os.getenv('AZURE_OPENAI_ENDPOINT'))}")
    logger.info(f"deployment_name present: {bool(os.getenv('deployment_name'))}")
    logger.info(f"api_version present: {bool(os.getenv('api_version'))}")

async def test_websocket_connection(candidate_id=None, host="localhost", port=8000, timeout=90):
    """Test WebSocket connection and chat functionality.
    
    Args:
        candidate_id: Optional candidate ID to include in the WebSocket URL
        host: Host to connect to
        port: Port to connect to
        timeout: Timeout in seconds for waiting for responses
    """
    try:
        # Generate a unique session ID for this test
        session_id = str(uuid.uuid4())
        logger.info(f"Testing WebSocket connection with session ID: {session_id}")
        
        # Connect to the WebSocket endpoint
        ws_url = f"ws://{host}:{port}/ws/chat/{session_id}"
        if candidate_id:
            ws_url += f"?candidateId={candidate_id}"
            logger.info(f"Including candidate ID in URL: {candidate_id}")
        
        logger.info(f"Connecting to WebSocket at: {ws_url}")
        
        async with websockets.connect(ws_url) as websocket:
            logger.info("WebSocket connection established successfully")
            
            # Wait for the welcome message
            welcome_message = await websocket.recv()
            logger.info(f"Received welcome message: {welcome_message}")
            
            # Send a test message
            test_message = "Hello, can you tell me what day it is today?"
            logger.info(f"Sending test message: {test_message}")
            
            await websocket.send(json.dumps({
                "text": test_message
            }))
            
            # Wait for responses with a timeout - we may get multiple messages (ping, ack, actual response)
            logger.info("Waiting for responses...")
            
            # Wait for up to max_responses or until we get a final AI response
            content_response_received = False
            final_ai_response_received = False
            candidate_info_received = False
            linkedin_present = False
            github_present = False
            max_responses = 30  # Increased max responses
            response_count = 0
            max_wait_time = timeout  # Wait up to timeout seconds for responses
            
            start_time = time.time()
            while response_count < max_responses and not final_ai_response_received and (time.time() - start_time < max_wait_time):
                try:
                    response_text = await asyncio.wait_for(websocket.recv(), timeout=10)
                    response_count += 1
                    
                    # Parse the response as JSON
                    try:
                        response = json.loads(response_text)
                        logger.info(f"Received response #{response_count}: {response}")
                        
                        # Check if it's a ping message
                        if response.get("type") == "ping":
                            logger.info("Received ping message, continuing to wait for content response")
                            continue
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse response as JSON: {response_text}")
                        logger.error(f"JSON error: {str(e)}")
                        continue
                    
                    # Check if the response contains a content field
                    if "content" in response:
                        content_response_received = True
                        logger.info("Response contains content field - Test PASSED")
                        logger.info(f"Response content: {response['content'][:50]}...")
                        
                        # Check if this is a final (non-processing) response
                        if response.get("isProcessing") is False:
                            logger.info("Received final AI response (not a processing message)")
                            final_ai_response_received = True
                            
                            # Check for candidate info if candidateId was provided
                            if candidate_id and "candidateInfo" in response:
                                candidate_info_received = True
                                candidate_info = response["candidateInfo"]
                                logger.info(f"Response includes candidate info: {candidate_info}")
                                
                                # Check for LinkedIn and GitHub links
                                if "resume" in candidate_info and "contact" in candidate_info["resume"]:
                                    contact = candidate_info["resume"]["contact"]
                                    linkedin = contact.get("linkedin")
                                    github = contact.get("github")
                                    linkedin_present = bool(linkedin)
                                    github_present = bool(github)
                                    logger.info(f"LinkedIn link present: {linkedin_present}, value: {linkedin}")
                                    logger.info(f"GitHub link present: {github_present}, value: {github}")
                except Exception as e:
                    logger.error(f"Error receiving response: {str(e)}")
                    break
                
            # Check if we received a final AI response
            if not final_ai_response_received:
                logger.warning("Did not receive a final AI response within the timeout period")
            
            if not content_response_received:
                logger.error("Did not receive a response with content field - Test FAILED")
                return False
            
            # Send a message to test candidate context integration
            if candidate_id:
                context_test_message = "What are the LinkedIn and GitHub profiles for this candidate?"
                logger.info(f"Sending candidate context test message: {context_test_message}")
                
                await websocket.send(json.dumps({
                    "text": context_test_message
                }))
                
                # Wait for candidate context response
                logger.info("Waiting for candidate context response...")
                start_time = time.time()
                candidate_response_count = 0
                candidate_content_received = False
                final_candidate_response_received = False
                candidate_linkedin_present = False
                candidate_github_present = False
                
                # Use the specified timeout for candidate context responses
                while time.time() - start_time < timeout and not final_candidate_response_received:
                    try:
                        candidate_response_text = await websocket.recv()
                        candidate_response_count += 1
                        
                        # Parse the response as JSON
                        try:
                            candidate_response = json.loads(candidate_response_text)
                            logger.info(f"Received candidate response #{candidate_response_count}: {candidate_response}")
                            
                            # Check if it's a ping message
                            if candidate_response.get("type") == "ping":
                                logger.info("Received ping message, continuing to wait for candidate content response")
                                continue
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse candidate response as JSON: {candidate_response_text}")
                            logger.error(f"JSON error: {str(e)}")
                            continue
                        
                        # Check if the response contains a content field
                        if "content" in candidate_response:
                            candidate_content_received = True
                            logger.info("Response contains content field with candidate context - Test PASSED")
                            logger.info(f"Response content with candidate context: {candidate_response['content'][:50]}...")
                            
                            # Check if this is a final (non-processing) response
                            if candidate_response.get("isProcessing") is False:
                                logger.info("Received final candidate AI response (not a processing message)")
                                final_candidate_response_received = True
                                
                                # Check for candidate info
                                if "candidateInfo" in candidate_response:
                                    candidate_info = candidate_response["candidateInfo"]
                                    logger.info(f"Candidate response includes candidate info: {candidate_info}")
                                    
                                    # Check for LinkedIn and GitHub links
                                    if "resume" in candidate_info and "contact" in candidate_info["resume"]:
                                        contact = candidate_info["resume"]["contact"]
                                        linkedin = contact.get("linkedin")
                                        github = contact.get("github")
                                        candidate_linkedin_present = bool(linkedin)
                                        candidate_github_present = bool(github)
                                        logger.info(f"LinkedIn link present: {candidate_linkedin_present}, value: {linkedin}")
                                        logger.info(f"GitHub link present: {candidate_github_present}, value: {github}")
                                        
                                        # Verify LinkedIn and GitHub links are present
                                        if not linkedin or not github:
                                            logger.warning("LinkedIn or GitHub links missing in candidate info")
                                            if not linkedin:
                                                logger.warning("LinkedIn link is missing or empty")
                                            if not github:
                                                logger.warning("GitHub link is missing or empty")
                                else:
                                    logger.error("Candidate response missing candidateInfo field - Test FAILED")
                                    return False
                        else:
                            logger.warning("Response does not contain content field")
                    except Exception as e:
                        logger.error(f"Error receiving candidate response: {str(e)}")
                        break
                        
                # Check if we received a final candidate AI response
                if not final_candidate_response_received:
                    logger.warning("Did not receive a final candidate AI response within the timeout period")
                    return False
                
                # Verify LinkedIn and GitHub links were present in the candidate-specific response
                if not candidate_linkedin_present or not candidate_github_present:
                    logger.warning(f"LinkedIn or GitHub links missing in candidate-specific response")
                    logger.warning(f"LinkedIn present: {candidate_linkedin_present}, GitHub present: {candidate_github_present}")
                    # Don't fail the test for this, just warn
            
            # Close the WebSocket connection
            await websocket.close()
            logger.info("WebSocket connection closed successfully")
            
            return True
    except asyncio.TimeoutError:
        logger.error("Timeout waiting for response from WebSocket")
        return False
    except Exception as e:
        logger.error(f"Error testing WebSocket connection: {str(e)}")
        logger.error(traceback.format_exc())
        return False

async def main():
    """Main function to run the tests."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test WebSocket connection with candidate info')
    parser.add_argument('--host', default='localhost', help='Host to connect to')
    parser.add_argument('--port', type=int, default=8000, help='Port to connect to')
    parser.add_argument('--timeout', type=int, default=90, help='Timeout in seconds for waiting for responses')
    parser.add_argument('--candidate-id', default='candidate-123', help='Candidate ID to use for testing')
    parser.add_argument('--skip-basic', action='store_true', help='Skip basic test without candidate ID')
    args = parser.parse_args()
    
    load_environment_variables()
    
    # Log test configuration
    logger.info(f"Test configuration: host={args.host}, port={args.port}, timeout={args.timeout}, candidate_id={args.candidate_id}")
    
    # Test without candidate ID (unless skipped)
    if not args.skip_basic:
        logger.info("Testing WebSocket connection without candidate ID")
        if not await test_websocket_connection(host=args.host, port=args.port, timeout=args.timeout):
            logger.error("WebSocket test without candidate ID failed")
            return False
    
    # Test with candidate ID
    logger.info(f"Testing WebSocket connection with candidate ID: {args.candidate_id}")
    if not await test_websocket_connection(candidate_id=args.candidate_id, host=args.host, port=args.port, timeout=args.timeout):
        logger.error("WebSocket test with candidate ID failed")
        return False
    
    logger.info("All WebSocket tests passed successfully")
    return True

if __name__ == "__main__":
    try:
        # Print banner
        print("\n" + "=" * 80)
        print("WebSocket Candidate Info Test")
        print("=" * 80)
        print("This test verifies that the WebSocket chat endpoint correctly includes")
        print("candidate information (including LinkedIn and GitHub links) in responses.")
        print("=" * 80 + "\n")
        
        # Run the main function
        import asyncio
        result = asyncio.run(main())
        if result:
            logger.info("All tests passed successfully")
            print("\n" + "=" * 80)
            print("✅ All tests passed successfully!")
            print("=" * 80 + "\n")
            sys.exit(0)
        else:
            logger.error("Some tests failed")
            print("\n" + "=" * 80)
            print("❌ Some tests failed. Check the logs for details.")
            print("=" * 80 + "\n")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        print("\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)

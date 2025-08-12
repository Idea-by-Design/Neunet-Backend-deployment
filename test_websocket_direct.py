#!/usr/bin/env python3
"""
Direct WebSocket test script for debugging the chat functionality.
This script connects to the WebSocket server and sends a message directly,
then waits for a response without using the test framework.
"""

import os
import sys
import json
import logging
import asyncio
import traceback
from dotenv import load_dotenv
import websockets
import uuid
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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

async def test_websocket_direct(candidate_id=None):
    """Test WebSocket connection directly with debug output."""
    try:
        # Generate a unique session ID for this test
        session_id = str(uuid.uuid4())
        logger.info(f"Testing WebSocket connection with session ID: {session_id}")
        
        # Connect to the WebSocket endpoint
        ws_url = f"ws://localhost:8000/ws/chat/{session_id}"
        if candidate_id:
            ws_url += f"?candidateId={candidate_id}"
        
        logger.info(f"Connecting to WebSocket at: {ws_url}")
        
        async with websockets.connect(ws_url) as websocket:
            logger.info("WebSocket connection established successfully")
            
            # Wait for the welcome message
            welcome_message = await websocket.recv()
            logger.info(f"Received welcome message: {welcome_message}")
            
            # Wait for any additional initial messages (like ping)
            try:
                initial_message = await asyncio.wait_for(websocket.recv(), timeout=2)
                logger.info(f"Received initial message: {initial_message}")
            except asyncio.TimeoutError:
                logger.info("No additional initial messages received")
            
            # Send a test message to test the AI processing flow
            test_message = "Hello, can you tell me what day it is today?"
            logger.info(f"Sending test message: {test_message}")
            
            await websocket.send(json.dumps({
                "text": test_message,
                "test": False  # Set to False to use the actual AI processing
            }))
            
            # Wait for the response with a timeout (longer for AI processing)
            logger.info("Waiting for AI response...")
            direct_response = await asyncio.wait_for(websocket.recv(), timeout=30)
            logger.info(f"Received direct response: {direct_response}")
            
            # Send a message to test candidate context if candidate_id is provided
            if candidate_id:
                context_test_message = "What do you know about this candidate? Show me their LinkedIn and GitHub links."
                logger.info(f"Sending candidate context test message: {context_test_message}")
                
                await websocket.send(json.dumps({
                    "text": context_test_message,
                    "context": {"candidateId": candidate_id},
                    "test": False  # Set to False to use the actual AI processing
                }))
                
                # Wait for the response with a timeout (longer for AI processing)
                logger.info("Waiting for candidate context response...")
                context_response = await asyncio.wait_for(websocket.recv(), timeout=30)
                logger.info(f"Received candidate context response: {context_response}")
                
                # Parse and validate the response for LinkedIn and GitHub links
                try:
                    response_data = json.loads(context_response)
                    if "candidateInfo" in response_data:
                        logger.info("✅ SUCCESS: Response contains candidateInfo")
                        candidate_info = response_data["candidateInfo"]
                        
                        # Check for resume data with contact information
                        if "resume" in candidate_info and "contact" in candidate_info["resume"]:
                            contact = candidate_info["resume"]["contact"]
                            linkedin = contact.get("linkedin")
                            github = contact.get("github")
                            
                            if linkedin:
                                logger.info(f"✅ SUCCESS: LinkedIn link found: {linkedin}")
                            else:
                                logger.warning("⚠️ WARNING: No LinkedIn link found in candidate info")
                                
                            if github:
                                logger.info(f"✅ SUCCESS: GitHub link found: {github}")
                            else:
                                logger.warning("⚠️ WARNING: No GitHub link found in candidate info")
                        else:
                            logger.warning("⚠️ WARNING: Response has candidateInfo but missing resume.contact structure")
                    else:
                        logger.warning("⚠️ WARNING: Response does not contain candidateInfo")
                except json.JSONDecodeError:
                    logger.error("❌ ERROR: Could not parse response as JSON")
                except Exception as e:
                    logger.error(f"❌ ERROR: Error validating response: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # Keep the connection open for a bit to see if any other messages arrive
            logger.info("Keeping connection open for 5 seconds to see if any other messages arrive...")
            try:
                while True:
                    additional_message = await asyncio.wait_for(websocket.recv(), timeout=5)
                    logger.info(f"Received additional message: {additional_message}")
            except asyncio.TimeoutError:
                logger.info("No additional messages received after waiting")
            
            logger.info("Test completed successfully")
            return True
            
    except Exception as e:
        logger.error(f"Error during WebSocket test: {str(e)}")
        logger.error(traceback.format_exc())
        return False

async def main():
    """Main function to run the direct WebSocket test."""
    load_environment_variables()
    
    # Test without candidate ID first
    logger.info("Testing WebSocket connection without candidate ID")
    await test_websocket_direct()
    
    # Then test with a real candidate ID (cynthia@beamjobs.com)
    # Based on the memory, this candidate might not have resume_blob_name but should still work with our fixes
    sample_candidate_id = "cynthia@beamjobs.com"
    logger.info(f"Testing WebSocket connection with candidate ID: {sample_candidate_id}")
    await test_websocket_direct(sample_candidate_id)
    
    return True

if __name__ == "__main__":
    try:
        # Run the main function
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

#!/usr/bin/env python3
"""
Test script to verify WebSocket chat functionality with multiagent assistant integration.
"""

import asyncio
import websockets
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_chat():
    """Test the WebSocket chat endpoint with candidate context."""
    
    # Test candidate ID
    candidate_id = "test-candidate-123"
    session_id = "test-session-123"
    websocket_url = f"ws://localhost:8000/ws/chat/{session_id}?candidateId={candidate_id}"
    
    try:
        async with websockets.connect(websocket_url) as websocket:
            logger.info(f"Connected to WebSocket: {websocket_url}")
            
            # Wait for connection confirmation
            confirmation = await websocket.recv()
            logger.info(f"Received confirmation: {confirmation}")
            
            # Send a test message
            test_message = {
                "text": "Tell me about this candidate's background and experience",
                "context": {
                    "candidateId": candidate_id
                }
            }
            
            logger.info(f"Sending test message: {test_message}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for responses
            response_count = 0
            max_responses = 10  # Increase limit to catch AI response
            
            while response_count < max_responses:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_count += 1
                    
                    logger.info(f"Response {response_count}: {response}")
                    
                    # Try to parse as JSON
                    try:
                        response_data = json.loads(response)
                        if isinstance(response_data, dict):
                            logger.info(f"Response type: {response_data.get('type', 'unknown')}")
                            if 'candidateInfo' in response_data:
                                logger.info("✅ Response contains candidateInfo!")
                                candidate_info = response_data['candidateInfo']
                                logger.info(f"Candidate ID: {candidate_info.get('id')}")
                                logger.info(f"LinkedIn: {candidate_info.get('linkedinUrl')}")
                                logger.info(f"GitHub: {candidate_info.get('githubUrl')}")
                            else:
                                logger.warning("❌ Response missing candidateInfo")
                    except json.JSONDecodeError:
                        logger.info("Response is plain text (not JSON)")
                    
                    # Check if this looks like a final response
                    if "processing" not in response.lower() and len(response) > 100:
                        logger.info("✅ Received substantial response - likely final AI reply")
                        break
                        
                except asyncio.TimeoutError:
                    logger.warning("Timeout waiting for response")
                    break
                    
    except Exception as e:
        logger.error(f"WebSocket test failed: {str(e)}")
        return False
    
    logger.info("WebSocket test completed")
    return True

if __name__ == "__main__":
    print("🚀 Testing WebSocket chat with multiagent assistant...")
    success = asyncio.run(test_websocket_chat())
    if success:
        print("✅ WebSocket test completed successfully!")
    else:
        print("❌ WebSocket test failed!")

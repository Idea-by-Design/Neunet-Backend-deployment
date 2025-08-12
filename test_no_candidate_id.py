#!/usr/bin/env python3
import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_without_candidate_id():
    """Test WebSocket connection without candidateId - for general chat"""
    uri = "ws://localhost:8000/ws/chat/general-chat-session"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info(f"Connected to WebSocket: {uri}")
            
            # Wait for connection confirmation
            confirmation = await websocket.recv()
            logger.info(f"Received confirmation: {confirmation}")
            
            # Send a general message without candidate context
            message = {
                "text": "hi",
                "context": {}  # Empty context - no candidateId
            }
            
            logger.info(f"Sending general 'hi' message: {message}")
            await websocket.send(json.dumps(message))
            
            # Wait for responses
            response_count = 0
            while response_count < 5:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_count += 1
                    logger.info(f"Response {response_count}: {response}")
                    
                    # Parse the response
                    try:
                        data = json.loads(response)
                        if data.get("type") == "text" and not data.get("isProcessing"):
                            logger.info("✅ Received final AI response for general chat!")
                            break
                    except json.JSONDecodeError:
                        pass
                        
                except asyncio.TimeoutError:
                    logger.warning("Timeout waiting for response")
                    break
                    
    except Exception as e:
        logger.error(f"Error: {e}")

async def test_create_job_description():
    """Test creating a job description without candidate context"""
    uri = "ws://localhost:8000/ws/chat/job-desc-session"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info(f"Connected to WebSocket: {uri}")
            
            # Wait for connection confirmation
            confirmation = await websocket.recv()
            logger.info(f"Received confirmation: {confirmation}")
            
            # Send a job description creation request
            message = {
                "text": "create a job description for a senior software engineer position",
                "context": {}  # No candidate context needed
            }
            
            logger.info(f"Sending job description request: {message}")
            await websocket.send(json.dumps(message))
            
            # Wait for responses
            response_count = 0
            while response_count < 5:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    response_count += 1
                    logger.info(f"Response {response_count}: {response}")
                    
                    # Parse the response
                    try:
                        data = json.loads(response)
                        if data.get("type") == "text" and not data.get("isProcessing"):
                            logger.info("✅ Received job description response!")
                            break
                    except json.JSONDecodeError:
                        pass
                        
                except asyncio.TimeoutError:
                    logger.warning("Timeout waiting for response")
                    break
                    
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    print("🚀 Testing WebSocket without candidateId...")
    print("\n1. Testing general 'hi' message:")
    asyncio.run(test_without_candidate_id())
    
    print("\n2. Testing job description creation:")
    asyncio.run(test_create_job_description())
    
    print("✅ Tests completed!")

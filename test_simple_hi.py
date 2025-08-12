#!/usr/bin/env python3
import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_hi_message():
    uri = "ws://localhost:8000/ws/chat/test-session-hi?candidateId=test-candidate-hi"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info(f"Connected to WebSocket: {uri}")
            
            # Wait for connection confirmation
            confirmation = await websocket.recv()
            logger.info(f"Received confirmation: {confirmation}")
            
            # Send a simple "hi" message
            message = {
                "text": "hi",
                "context": {
                    "candidateId": "test-candidate-hi"
                }
            }
            
            logger.info(f"Sending 'hi' message: {message}")
            await websocket.send(json.dumps(message))
            
            # Wait for responses
            response_count = 0
            while response_count < 5:  # Wait for up to 5 responses
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_count += 1
                    logger.info(f"Response {response_count}: {response}")
                    
                    # Parse the response
                    try:
                        data = json.loads(response)
                        if data.get("type") == "text" and not data.get("isProcessing"):
                            logger.info("✅ Received final AI response!")
                            break
                    except json.JSONDecodeError:
                        pass
                        
                except asyncio.TimeoutError:
                    logger.warning("Timeout waiting for response")
                    break
                    
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    print("🚀 Testing simple 'hi' message...")
    asyncio.run(test_hi_message())
    print("✅ Test completed!")

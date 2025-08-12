import os
import sys
from dotenv import load_dotenv
import openai
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_openai_connection():
    """Test connection to standard OpenAI API"""
    
    # Load environment variables
    load_dotenv()
    
    # Print environment variables for debugging (mask sensitive parts)
    api_key = os.getenv("OPENAI_API_KEY")
    api_type = os.getenv("api_type")
    model_name = os.getenv("model_name")
    
    logger.info(f"OPENAI_API_KEY present: {bool(api_key)}")
    logger.info(f"api_type: {api_type}")
    logger.info(f"model_name: {model_name}")
    
    try:
        # Configure OpenAI client
        client = openai.OpenAI(
            api_key=api_key
        )
        
        logger.info("Client configured successfully, attempting to send a test request...")
        
        # Test with a simple completion request
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, are you working?"}
            ],
            max_tokens=50
        )
        
        logger.info("API request successful!")
        logger.info(f"Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        logger.error(f"Error connecting to OpenAI API: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_openai_connection()
    sys.exit(0 if success else 1)

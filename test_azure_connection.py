#!/usr/bin/env python3
"""
Test script to verify Azure OpenAI API connection.
This script directly tests the Azure OpenAI API connection using the environment variables.
"""

import os
import sys
import json
import logging
import traceback
from dotenv import load_dotenv
import openai
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

def test_azure_openai_connection():
    """Test the Azure OpenAI API connection."""
    try:
        # Get environment variables
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment_name = os.getenv("deployment_name")
        api_version = os.getenv("api_version")
        
        if not all([api_key, endpoint, deployment_name, api_version]):
            logger.error("Missing required environment variables for Azure OpenAI API")
            return False
        
        logger.info(f"Testing Azure OpenAI API connection with deployment: {deployment_name}")
        logger.info(f"API endpoint: {endpoint}")
        logger.info(f"API version: {api_version}")
        
        # Configure the client
        client = openai.AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint
        )
        
        # Make a simple chat completion request
        logger.info("Sending test request to Azure OpenAI API...")
        start_time = time.time()
        
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, can you tell me what day it is today?"}
            ],
            max_tokens=100
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"Request completed in {elapsed_time:.2f} seconds")
        
        # Log the response
        logger.info(f"Response received: {response}")
        logger.info(f"Content: {response.choices[0].message.content}")
        
        return True
        
    except openai.APIConnectionError as e:
        logger.error(f"Azure OpenAI API connection error: {str(e)}")
        return False
    except openai.AuthenticationError as e:
        logger.error(f"Azure OpenAI API authentication error: {str(e)}")
        return False
    except openai.NotFoundError as e:
        logger.error(f"Azure OpenAI API deployment not found: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error testing Azure OpenAI API: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main function to run the Azure OpenAI API connection test."""
    load_environment_variables()
    
    success = test_azure_openai_connection()
    
    if success:
        logger.info("✅ Azure OpenAI API connection test successful!")
        return 0
    else:
        logger.error("❌ Azure OpenAI API connection test failed!")
        return 1

if __name__ == "__main__":
    try:
        # Run the main function
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)

#!/usr/bin/env python3
"""
Test script to verify Azure OpenAI API configuration and integration with autogen.
"""

import os
import sys
import logging
import traceback
from dotenv import load_dotenv
import autogen

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
    logger.info(f"AZURE_OPENAI_DEPLOYMENT_NAME present: {bool(os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME'))}")
    logger.info(f"AZURE_OPENAI_API_VERSION present: {bool(os.getenv('AZURE_OPENAI_API_VERSION'))}")

def test_autogen_config():
    """Test autogen configuration with Azure OpenAI."""
    try:
        # Load environment variables for Azure OpenAI
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment_name = os.getenv("deployment_name", "gpt-4o")  # Use the correct env var name
        api_version = os.getenv("api_version", "2024-08-01-preview")  # Use the correct env var name and version
        
        # Log configuration details (without exposing the API key)
        logger.info(f"Azure OpenAI configuration: model={deployment_name}")
        logger.info(f"Azure endpoint: {azure_endpoint}")
        logger.info(f"Azure API version: {api_version}")
        
        # Check if required environment variables are set
        if not azure_api_key or not azure_endpoint:
            logger.error("Missing required Azure OpenAI environment variables")
            return False
        
        # Configure the OpenAI API client for Azure
        config_list = [
            {
                "model": deployment_name,
                "api_key": azure_api_key,
                "base_url": azure_endpoint,
                "api_type": "azure",
                "api_version": api_version
            }
        ]
        
        # Set up client configuration options for timeout and retries
        import openai
        openai.timeout = 60  # Increase timeout for Azure OpenAI API calls
        openai.max_retries = 3  # Add retry logic for transient errors
        
        # Test direct API connection first
        try:
            logger.info("Testing direct Azure OpenAI API connection...")
            from openai import AzureOpenAI
            import threading
            import time
            
            # Set up a timeout for the API call
            api_test_success = False
            api_test_error = None
            
            def test_api_with_timeout():
                nonlocal api_test_success, api_test_error
                try:
                    client = AzureOpenAI(
                        api_key=azure_api_key,
                        api_version=api_version,
                        azure_endpoint=azure_endpoint
                    )
                    
                    logger.info(f"Attempting to call Azure OpenAI API with model={deployment_name}")
                    response = client.chat.completions.create(
                        model=deployment_name,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": "Hello, what day is it today?"}
                        ],
                        max_tokens=100
                    )
                    
                    logger.info(f"Direct API test successful. Response: {response.choices[0].message.content}")
                    api_test_success = True
                except Exception as e:
                    api_test_error = e
                    logger.error(f"Direct API test failed: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # Start the API test in a separate thread with a timeout
            api_thread = threading.Thread(target=test_api_with_timeout)
            api_thread.daemon = True
            api_thread.start()
            
            # Wait for the API test to complete or timeout
            api_thread.join(timeout=15)  # 15 second timeout
            
            if api_thread.is_alive():
                logger.error("Direct API test timed out after 15 seconds")
                return False
            
            if not api_test_success:
                logger.error(f"Direct API test failed: {str(api_test_error)}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting up direct API test: {str(e)}")
            logger.error(traceback.format_exc())
            return False
        
        # Log the configuration (without the API key)
        logger.info(f"OpenAI API Configuration:")
        logger.info(f"Model: {config_list[0]['model']}")
        logger.info(f"Azure base_url: {config_list[0].get('base_url')}")
        logger.info(f"Azure API version: {config_list[0].get('api_version')}")
        logger.info(f"Azure API type: {config_list[0].get('api_type')}")
        
        # Create a simple autogen agent to test configuration
        try:
            logger.info("Creating autogen assistant agent...")
            assistant = autogen.AssistantAgent(
                name="assistant",
                llm_config={"config_list": config_list}
            )
            logger.info("Successfully created autogen assistant agent")
            
            # Create a user proxy agent
            logger.info("Creating autogen user proxy agent...")
            user_proxy = autogen.UserProxyAgent(
                name="user_proxy",
                human_input_mode="NEVER",
                max_consecutive_auto_reply=1,
                code_execution_config={"use_docker": False}  # Disable Docker for code execution
            )
            logger.info("Successfully created autogen user proxy agent")
            
            # Test a simple conversation
            logger.info("Testing a simple conversation...")
            user_proxy.initiate_chat(
                assistant,
                message="Hello, can you tell me what day it is today?"
            )
            logger.info("Conversation test completed successfully")
            
            return True
        except Exception as e:
            logger.error(f"Error creating autogen agents: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    except Exception as e:
        logger.error(f"Error setting up OpenAI API configuration: {str(e)}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    load_environment_variables()
    success = test_autogen_config()
    if success:
        logger.info("Azure OpenAI API configuration test passed successfully")
        sys.exit(0)
    else:
        logger.error("Azure OpenAI API configuration test failed")
        sys.exit(1)

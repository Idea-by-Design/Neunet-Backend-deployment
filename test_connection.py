import socket
import requests
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_dns_resolution(hostname):
    """Test if a hostname can be resolved via DNS"""
    try:
        logger.info(f"Attempting to resolve hostname: {hostname}")
        ip_address = socket.gethostbyname(hostname)
        logger.info(f"Successfully resolved {hostname} to {ip_address}")
        return True
    except socket.gaierror as e:
        logger.error(f"Failed to resolve hostname {hostname}: {str(e)}")
        return False

def test_http_connection(url):
    """Test if a URL is reachable via HTTP"""
    try:
        logger.info(f"Attempting to connect to URL: {url}")
        response = requests.get(url, timeout=10)
        logger.info(f"Successfully connected to {url}, status code: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to connect to URL {url}: {str(e)}")
        return False

def main():
    # Load environment variables
    load_dotenv()
    
    # Get Azure OpenAI endpoint
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
    if not endpoint:
        logger.error("AZURE_OPENAI_ENDPOINT environment variable not set")
        return False
    
    # Extract hostname from endpoint URL
    if endpoint.startswith("https://"):
        hostname = endpoint[8:]
    elif endpoint.startswith("http://"):
        hostname = endpoint[7:]
    else:
        hostname = endpoint
    
    # Remove trailing slash and path if present
    if "/" in hostname:
        hostname = hostname.split("/")[0]
    
    logger.info(f"Extracted hostname: {hostname}")
    
    # Test DNS resolution
    dns_success = test_dns_resolution(hostname)
    
    # Test standard Azure OpenAI endpoints for comparison
    logger.info("Testing standard Azure OpenAI endpoints for comparison:")
    test_dns_resolution("openai.azure.com")
    test_dns_resolution("api.openai.com")
    
    # Suggest possible correct endpoints
    logger.info("Suggesting possible correct endpoints:")
    possible_endpoints = [
        f"https://{hostname.split('.')[0]}.openai.azure.com/",
        f"https://{hostname.split('.')[0]}.api.cognitive.microsoft.com/",
        f"https://api.openai.com/"
    ]
    
    for possible_endpoint in possible_endpoints:
        logger.info(f"Possible endpoint: {possible_endpoint}")
        hostname_part = possible_endpoint.replace("https://", "").replace("http://", "").split("/")[0]
        test_dns_resolution(hostname_part)
    
    return dns_success

if __name__ == "__main__":
    main()

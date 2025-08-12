import requests
import logging
import socket

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_endpoint(endpoint):
    """Test if an endpoint is reachable"""
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
    
    logger.info(f"Testing endpoint: {endpoint}")
    logger.info(f"Extracted hostname: {hostname}")
    
    # Test DNS resolution
    try:
        ip_address = socket.gethostbyname(hostname)
        logger.info(f"✅ DNS resolution successful: {hostname} -> {ip_address}")
        
        # Try HTTP connection
        try:
            response = requests.get(endpoint, timeout=5)
            logger.info(f"✅ HTTP connection successful: Status code {response.status_code}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ HTTP connection failed: {str(e)}")
            return False
    except socket.gaierror as e:
        logger.error(f"❌ DNS resolution failed: {str(e)}")
        return False

# Test various Azure OpenAI endpoint formats
endpoints = [
    "https://openai-api-ixd.openai.azure.com/",
    "https://openai-api-ixd.azure-api.net/",
    "https://api.openai.com/",
    "https://api.cognitive.microsoft.com/",
    "https://ixd.openai.azure.com/",
    "https://ixd.api.cognitive.microsoft.com/"
]

for endpoint in endpoints:
    test_endpoint(endpoint)
    print("-" * 50)

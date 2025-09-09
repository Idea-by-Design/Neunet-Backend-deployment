# Multiagent function bridge: import and re-export all multiagent functions for agent registration
from common.database.cosmos.db_operations import (
    fetch_top_k_candidates_by_count,
    update_application_status,
    execute_sql_query,
)

from azure.communication.email import EmailClient
from azure.core.credentials import AzureKeyCredential

def send_email(to_addresses, subject, body_plain):
    print("send email function called")
    key = AzureKeyCredential("4GhT4z2rGEnNQuK8E1mPag9G2CmM37nHx10NUFxuLmp96A4C2cUiJQQJ99AKACULyCpDyPWLAAAAAZCSQasT")
    endpoint = "https://neunet-communication-service.unitedstates.communication.azure.com/"
    email_client = EmailClient(endpoint, key)
    message = {
        "content": {
            "subject": subject,
            "plainText": body_plain,
        },
        "recipients": {
            "to": [{"address": address, "displayName": "Candidate"} for address in to_addresses]
        },
        "senderAddress": "DoNotReply@ideaxdesign.com",
    }
    print(f"Message: {message}")
    try:
        poller = email_client.begin_send(message)
        print("Email send operation initiated.")
        result = poller.result()
        print(f"Result: {result}")
        return {"status": "success", "details": result}
    except Exception as ex:
        return {"status": "error", "details": str(ex)}
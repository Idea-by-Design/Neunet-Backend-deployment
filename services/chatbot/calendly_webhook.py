from fastapi import FastAPI, Request
from common.database.cosmos.db_operations import update_application_status

app = FastAPI()

@app.post("/calendly/webhook")
async def handle_calendly_webhook(request: Request):
    try:
        payload = await request.json()
        event_type = payload.get("event")  # e.g., "invitee.created"

        if event_type == "invitee.created":
            # Extract candidate email and job_id from the query parameters
            query_params = payload["payload"]["tracking"].get("query_params", {})
            candidate_email = query_params.get("email")
            job_id = query_params.get("job_id")

            # Validate and update the application status
            if candidate_email and job_id:
                update_result = update_application_status(
                    job_id=int(job_id),
                    candidate_email=candidate_email,
                    new_status="Interview Scheduled"
                )
                print(f"Update Result: {update_result}")
            else:
                print("Missing candidate_email or job_id in webhook payload.")

        return {"success": True, "message": "Webhook processed successfully."}

    except Exception as e:
        print(f"Error processing Calendly webhook: {e}")
        return {"success": False, "error": str(e)}

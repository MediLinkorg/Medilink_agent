import json
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from anthropic import Anthropic
from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from .booking_automation import BookingRequest, book_on_vezeeta

class BookRequest(BaseModel):
    user_message: str
    user_id: Optional[str] = None
    recommendations: List[Dict[str, Any]] = []

def process_book_request(req: BookRequest) -> Dict[str, Any]:
    if not ANTHROPIC_API_KEY:
        return {"status": "error", "message": "Missing ANTHROPIC_API_KEY"}

    if not req.recommendations:
        return {"status": "recommendations_only", "message": "No recommendations available to book."}

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    docs_json = json.dumps(req.recommendations, ensure_ascii=False, indent=2)
    
    prompt = f"""
You are a booking assistant. Your job is to read the user's message and determine if they want to book an appointment with one of the recommended doctors.

User Message: {req.user_message}

Recommended Doctors:
{docs_json}

Task:
Extract the following details if the user explicitly wants to book:
1. 'doctor_url': The vezeeta_url (or url) of the doctor the user chose from the list.
2. 'patient_name': The full name of the patient provided in the message.
3. 'patient_phone': The phone number of the patient provided in the message.
4. 'wants_to_book': true if they explicitly requested a booking, false otherwise.

Output ONLY a valid JSON object matching this schema exactly (no markdown formatting, no comments):
{{
  "wants_to_book": boolean,
  "doctor_url": "string or null",
  "patient_name": "string or null",
  "patient_phone": "string or null"
}}
"""

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=300,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}]
        )
        
        text = response.content[0].text.strip()
        if text.startswith("```json"):
            text = text[7:-3].strip()
        elif text.startswith("```"):
            text = text[3:-3].strip()
            
        extraction = json.loads(text)
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse user intent: {e}"}

    if not extraction.get("wants_to_book"):
        return {"status": "recommendations_only"}
        
    doctor_url = extraction.get("doctor_url")
    patient_name = extraction.get("patient_name")
    patient_phone = extraction.get("patient_phone")
    
    if not doctor_url:
        return {"status": "error", "message": "You asked to book, but I couldn't determine which doctor."}
        
    if not patient_name or not patient_phone:
        return {"status": "recommendations_only"}

    # We have everything, so trigger the booking!
    booking_req = BookingRequest(
        doctor_url=doctor_url,
        patient_name=patient_name,
        patient_phone=patient_phone,
        dry_run=True, # Safety first!
        user_confirmed_final=False
    )
    
    try:
        result = book_on_vezeeta(booking_req)
        return result
    except Exception as e:
        return {"status": "error", "message": f"Booking automation failed: {e}"}

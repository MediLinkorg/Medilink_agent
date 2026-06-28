from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from .claude_agent import run_claude_agent
from .booking_automation import BookingRequest, book_on_vezeeta
from .vezeeta_live_booking import get_live_availability, book_selected_slot

app = FastAPI(title="MediLink Agent — Claude Orchestration + Vezeeta Booking")


class AgentRequest(BaseModel):
    message: str
    user_id: Optional[str] = None


class BookingStartRequest(BaseModel):
    doctor_url: str
    patient_name: str
    patient_phone: str
    preferred_day_text: Optional[str] = None
    preferred_time_text: Optional[str] = None
    dry_run: bool = True
    user_confirmed_final: bool = False


class BookingAvailabilityRequest(BaseModel):
    user_id: str
    doctor_url: str
    headless: bool = True


class BookingConfirmRequest(BaseModel):
    user_id: str
    doctor_url: str
    selected_time_text: str
    patient_name: str
    patient_phone: str
    doctor_cache_id: Optional[int] = None
    dry_run: bool = True
    user_confirmed_final: bool = False
    headless: bool = True


@app.get("/health")
def health():
    return {"status": "ok", "service": "medi_agent"}


@app.post("/agent")
def agent(req: AgentRequest):
    return {"response": run_claude_agent(req.message, user_id=req.user_id)}


@app.post("/booking/start")
def booking_start(req: BookingStartRequest):
    return book_on_vezeeta(BookingRequest(
        doctor_url=req.doctor_url,
        patient_name=req.patient_name,
        patient_phone=req.patient_phone,
        preferred_day_text=req.preferred_day_text,
        preferred_time_text=req.preferred_time_text,
        dry_run=req.dry_run,
        user_confirmed_final=req.user_confirmed_final,
    ))


@app.post("/booking/availability")
def booking_availability(req: BookingAvailabilityRequest):
    return get_live_availability(
        user_id=req.user_id,
        doctor_url=req.doctor_url,
        headless=req.headless,
    )


@app.post("/booking/confirm")
def booking_confirm(req: BookingConfirmRequest):
    return book_selected_slot(
        user_id=req.user_id,
        doctor_url=req.doctor_url,
        selected_time_text=req.selected_time_text,
        patient_name=req.patient_name,
        patient_phone=req.patient_phone,
        doctor_cache_id=req.doctor_cache_id,
        dry_run=req.dry_run,
        user_confirmed_final=req.user_confirmed_final,
        headless=req.headless,
    )
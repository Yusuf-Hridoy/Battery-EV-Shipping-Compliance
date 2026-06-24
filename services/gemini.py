import logging
import os
from datetime import datetime, date

import google.generativeai as genai

logger = logging.getLogger("batteryship.gemini")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_AVAILABLE = bool(GEMINI_API_KEY)
MODEL_NAME = "gemini-2.0-flash-lite"

if GEMINI_AVAILABLE:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(MODEL_NAME)

SYSTEM_PROMPT = (
    "You are a dangerous goods compliance assistant specializing in "
    "lithium battery shipping regulations. You help small businesses "
    "understand IATA DGR, DOT 49 CFR, and IMDG Code rules.\n\n"
    "Rules you must always follow:\n"
    "- Be concise and practical. Maximum 200 words per response.\n"
    "- Use plain English. Avoid jargon where possible.\n"
    "- Always end responses with: "
    "'For full compliance, verify with a certified DG specialist.'\n"
    "- Never provide legal advice.\n"
    "- Stick to factual regulatory information only.\n"
    "- If unsure, say so clearly rather than guessing.\n"
    "- Regulations referenced: IATA DGR 2026, ADR 2025, IMDG Code."
)

MAX_CALLS_PER_DAY = 10

daily_usage = {}


def check_rate_limit(user_id: str) -> bool:
    today = date.today()
    if user_id not in daily_usage:
        daily_usage[user_id] = {"date": today, "count": 0}

    entry = daily_usage[user_id]
    if entry["date"] != today:
        entry["date"] = today
        entry["count"] = 0

    if entry["count"] >= MAX_CALLS_PER_DAY:
        return False

    entry["count"] += 1
    return True


def get_remaining_calls(user_id: str) -> int:
    today = date.today()
    if user_id not in daily_usage:
        return MAX_CALLS_PER_DAY
    entry = daily_usage[user_id]
    if entry["date"] != today:
        return MAX_CALLS_PER_DAY
    return max(0, MAX_CALLS_PER_DAY - entry["count"])


def _fallback_explain(classification: dict) -> dict:
    requires_decl = classification.get("requires_shippers_declaration", False)
    requires_un38 = classification.get("requires_un38_3", False)
    decl_text = "Shipper's Declaration required." if requires_decl else "No Shipper's Declaration required for this shipment."
    un38_text = "UN38.3 Test Summary required." if requires_un38 else ""
    explanation = (
        f"Classification summary: {classification.get('un_number', '')} — "
        f"{classification.get('proper_shipping_name', '')}. "
        f"Packing instruction {classification.get('packing_instruction', '')} applies. "
        f"Section {classification.get('section', '')}. "
        f"{decl_text} {un38_text} "
        f"For full compliance, verify with a certified DG specialist."
    )
    return {
        "explanation": explanation,
        "remaining_calls": MAX_CALLS_PER_DAY,
        "source": "fallback",
        "model": None,
    }


def explain_classification(classification: dict, user_id: str) -> dict:
    if not GEMINI_AVAILABLE:
        return _fallback_explain(classification)

    if not check_rate_limit(user_id):
        return {
            "explanation": "Daily AI explanation limit reached (10/day). Please try again tomorrow.",
            "remaining_calls": 0,
            "source": "rate_limit",
            "model": MODEL_NAME,
        }

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"A shipper has received this classification result:\n"
        f"- UN Number: {classification.get('un_number', '')}\n"
        f"- Proper Shipping Name: {classification.get('proper_shipping_name', '')}\n"
        f"- Packing Instruction: {classification.get('packing_instruction', '')}\n"
        f"- Section: {classification.get('section', '')}\n"
        f"- Transport Mode: {classification.get('transport_mode', '')}\n"
        f"- Requires Shipper's Declaration: {classification.get('requires_shippers_declaration', False)}\n"
        f"- Requires UN38.3: {classification.get('requires_un38_3', False)}\n"
        f"- Hazard Class: {classification.get('hazard_class', '')}\n"
        f"- Confidence: {classification.get('confidence', '')}\n\n"
        f"Please explain:\n"
        f"1. Why this UN number applies (1-2 sentences)\n"
        f"2. What the packing instruction requires (2-3 sentences)\n"
        f"3. What documents they need to prepare (bullet list)\n"
        f"4. Any key warnings or things to watch out for (1-2 sentences)\n\n"
        f"Keep total response under 200 words."
    )

    try:
        response = model.generate_content(prompt)
        text = response.text
        return {
            "explanation": text,
            "remaining_calls": get_remaining_calls(user_id),
            "source": "gemini",
            "model": MODEL_NAME,
        }
    except Exception as e:
        logger.warning(f"Gemini explain_classification failed: {e}")
        fallback = _fallback_explain(classification)
        fallback["remaining_calls"] = get_remaining_calls(user_id)
        fallback["source"] = "fallback"
        fallback["model"] = MODEL_NAME
        return fallback


def check_edge_case(user_question: str, classification: dict, user_id: str) -> dict:
    if not GEMINI_AVAILABLE:
        return {
            "answer": (
                f"AI edge case checking requires Gemini API configuration. "
                f"Your question: '{user_question}'. Current classification: "
                f"{classification.get('un_number', '')}. "
                f"Please consult a certified DG specialist for edge case questions."
            ),
            "remaining_calls": MAX_CALLS_PER_DAY,
            "source": "fallback",
            "model": None,
        }

    if not check_rate_limit(user_id):
        return {
            "answer": "Daily AI limit reached (10/day). Try again tomorrow.",
            "remaining_calls": 0,
            "source": "rate_limit",
            "model": MODEL_NAME,
        }

    question = user_question.strip()
    if len(question) < 5:
        return {
            "answer": "Please provide a more specific question.",
            "remaining_calls": get_remaining_calls(user_id),
            "source": "validation",
            "model": MODEL_NAME,
        }

    if len(question) > 500:
        question = question[:500]

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Current shipment classification context:\n"
        f"- UN Number: {classification.get('un_number', '')}\n"
        f"- Proper Shipping Name: {classification.get('proper_shipping_name', '')}\n"
        f"- Packing Instruction: {classification.get('packing_instruction', '')}\n"
        f"- Section: {classification.get('section', '')}\n"
        f"- Transport Mode: {classification.get('transport_mode', '')}\n\n"
        f"The shipper asks: '{question}'\n\n"
        f"Answer their specific question directly and concisely. "
        f"Maximum 150 words. Be practical and actionable."
    )

    try:
        response = model.generate_content(prompt)
        return {
            "answer": response.text,
            "remaining_calls": get_remaining_calls(user_id),
            "source": "gemini",
            "model": MODEL_NAME,
        }
    except Exception as e:
        logger.warning(f"Gemini check_edge_case failed: {e}")
        return {
            "answer": (
                "AI assistance is temporarily unavailable. "
                f"Your question: '{user_question}'. Current classification: "
                f"{classification.get('un_number', '')}. "
                "Please consult a certified DG specialist for edge case questions."
            ),
            "remaining_calls": get_remaining_calls(user_id),
            "source": "fallback",
            "model": MODEL_NAME,
        }

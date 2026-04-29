import re
import pickle
from pathlib import Path
from datetime import date, timedelta

import dateparser
import spacy

from .models import AgentMemory
from sqlalchemy.orm import Session
#from .models import LeaveRequest
from datetime import date
#----------------------
# Adding memory yahoooo :)
#----------------------
from dataclasses import dataclass
from typing import Optional

@dataclass
class AgentState:
    intent: Optional[str] = None
    stage: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    duration_days: Optional[int] = None
    reason: Optional[str] = None
    leave_type: Optional[str] = None
    awaiting_field: Optional[str] = None
#-------------------------------
#defining stages
#-------------------------------
STAGES = [
    "START",
    "COLLECTING_DATES",
    "COLLECTING_REASON",
    "CONFIRMATION",
    "COMPLETED"
]
#---------------------------------

#USER_STATES = {}
#----------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

# -----------------------------
# Load models once at startup
# -----------------------------
with open(BASE_DIR / "intent_model.pkl", "rb") as f:
    intent_model = pickle.load(f)

ner_nlp = spacy.load(str(BASE_DIR / "leave_ner_model_new"))

DATE_SETTINGS = {
    "PREFER_DATES_FROM": "future",
    "DATE_ORDER": "DMY",
}
from datetime import datetime, timedelta 

def load_state_from_db(db: Session, user_id: int) -> AgentState:
    mem = db.query(AgentMemory).filter(AgentMemory.user_id == user_id).first()

    if not mem:
        return AgentState(stage="START")

    if mem.last_updated:
        if datetime.utcnow() - mem.last_updated > timedelta(minutes=10):
            return AgentState(stage="START")

    return AgentState(
        intent=mem.intent,
        stage=mem.stage,
        start_date=mem.start_date,
        end_date=mem.end_date,
        duration_days=mem.duration_days,
        reason=mem.reason,
        leave_type=mem.leave_type,
    )
def save_state_to_db(db: Session, user_id: int, state: AgentState):
    mem = db.query(AgentMemory).filter(AgentMemory.user_id == user_id).first()

    if not mem:
        mem = AgentMemory(user_id=user_id)
        db.add(mem)

    mem.intent = state.intent
    mem.stage = state.stage
    mem.start_date = state.start_date
    mem.end_date = state.end_date
    mem.duration_days = state.duration_days
    mem.reason = state.reason
    mem.leave_type = state.leave_type

    mem.last_updated = datetime.utcnow()

    db.commit()

def reset_state(db: Session, user_id: int):
    mem = db.query(AgentMemory).filter(AgentMemory.user_id == user_id).first()

    if mem:
        db.delete(mem)
        db.commit()
#------------------------------
# updating state from message :)
#------------------------------
def update_state(state: AgentState, message: str):
    # Only detect intent if it's not already set
    intent = detect_intent(message)

    if intent != "UNKNOWN" and intent != state.intent:
        state.intent = intent
        state.stage = "START"
        state.start_date = None
        state.end_date = None
        state.duration_days = None
        state.reason = None
        state.leave_type = None
    # Continue extracting details ONLY if APPLY_LEAVE
    if state.intent == "APPLY_LEAVE":
        start, end = extract_dates(message)
        reason = extract_reason(message)
        leave_type = extract_leave_type(message)
        duration = extract_duration_days(message)

        if start:
            state.start_date = start
        if end:
            state.end_date = end
        if reason:
            state.reason = reason
        if leave_type:
            state.leave_type = leave_type
        if duration:
            state.duration_days = duration

    return state

# -----------------------------

def is_valid_input(message: str) -> bool:
    msg = message.strip().lower()

    #if the message is too short → ignore
    if len(msg) < 3 and (msg != "hi" and msg!="hii"):
        return False

    #for repeated same characters like "vvvv", "aaaa"
    if re.fullmatch(r"(.)\1+", msg):
        return False

    return True

# -----------------------------
# Intent
# -----------------------------
def detect_intent(message: str) -> str:
    msg = message.strip().lower()

    if msg in ["hi", "hii","hiiiiiiiiiiiiiiiiiiiiiii", "hello", "hey", "heyy"]:
        return "GREETING"

    if not is_valid_input(message):
        return "UNKNOWN"

    pred = intent_model.predict([message])[0]

    if pred == "apply_leave":
        if not any(word in msg for word in ["leave", "sick", "vacation", "off", "holiday"]):
            return "UNKNOWN"

    label_map = {
        "apply_leave": "APPLY_LEAVE",
        "check_balance": "CHECK_BALANCE",
        "leave_status": "VIEW_HISTORY",
        "view_history": "VIEW_HISTORY",
        "greeting": "GREETING",
        "cancel_leave": "CANCEL_LEAVE",
    }

    return label_map.get(pred, "UNKNOWN")
#---------------------------------
# adding decision function (this will make it agent) :)
#---------------------------------
def decide_next_step(state: AgentState, message: str):
    if state.intent == "CHECK_BALANCE":
        return {"action": "CHECK_BALANCE"}

    if state.intent == "VIEW_HISTORY":
        return {"action": "VIEW_HISTORY"}
    
    if state.intent == "GREETING":
        return {
            "action": "ASK",
            "message": "Hello! How can I assist you today?"
        }
    
    if state.intent == "APPLY_LEAVE":

        if not state.start_date:
            state.stage = "COLLECTING_DATES";
            return {
                "action": "ASK",
                "message": "Please tell me the start date of your leave."
            }
        msg = message.lower()

        if not state.end_date and not state.duration_days:
            if (
                "today" in msg
                or "tomorrow" in msg
                or re.search(r"\bon\s+", msg)
            ) and not re.search(r"\bfrom\s+", msg):
                state.end_date = state.start_date
            else:
                state.stage = "COLLECTING_DATES";
                return {
                    "action": "ASK",
                    "message": "Please tell me the end date or number of days."
                }

        if not state.reason:
            state.stage= "COLLECTING_REASON";
            return {
                "action": "ASK",
                "message": "Please tell me the reason for leave."
            }

        state.stage = "COMPLETED";
        return {"action": "APPLY_LEAVE"}

    return {
        "action": "ASK",
        "message": "Please use this section only to apply for leave."
    }


# -----------------------------
# Leave type
# -----------------------------
def extract_leave_type(message: str) -> str:
    msg = message.lower()

    if "casual" in msg or re.search(r"\bcl\b", msg):
        return "CL"
    if "sick" in msg or re.search(r"\bsl\b", msg):
        return "SL"
    if "medical" in msg or re.search(r"\bml\b", msg):
        return "ML"

    # serious illness → ML
    if any(word in msg for word in ["surgery", "hospital", "operation", "serious", "fracture"]):
        return "ML"

    # medical fallback
    if any(word in msg for word in ["fever", "cold", "headache", "illness", "sick"]):
        return "SL"

    return "CL"


# -----------------------------
# Entity extraction from NER
# -----------------------------
def extract_entities(message: str):

    doc = ner_nlp(message)

    start_date_text = None
    end_date_text = None
    duration_text = None
    reason_text = None

    for ent in doc.ents:
        print("ENTITY:", ent.text, ent.label_)

        if ent.label_ == "START_DATE" and not start_date_text:
            start_date_text = ent.text
        elif ent.label_ == "END_DATE" and not end_date_text:
            end_date_text = ent.text
        elif ent.label_ == "DURATION" and not duration_text:
            duration_text = ent.text
        elif ent.label_ == "REASON" and not reason_text:
            reason_text = ent.text
       
    return start_date_text, end_date_text, duration_text, reason_text


# -----------------------------
# Duration parser
# -----------------------------
def extract_duration_days(message: str) -> int | None:
    _, _, duration_text, _ = extract_entities(message)

    text = (duration_text or message).lower()

    m = re.search(r"\b(\d+)\s*(day|days)\b", text)
    if m:
        return int(m.group(1))

    word_to_num = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }

    m2 = re.search(
        r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\s*(day|days)\b",
        text,
    )
    if m2:
        return word_to_num[m2.group(1)]

    return None


# -----------------------------
# Dates
# -----------------------------
def extract_dates(message: str) -> tuple[date | None, date | None]:
    start_text, end_text, duration_text, _ = extract_entities(message)

    print("START TEXT:", start_text)
    print("END TEXT:", end_text)
    print("DURATION TEXT:", duration_text)

    start = dateparser.parse(start_text, settings=DATE_SETTINGS) if start_text else None
    end = dateparser.parse(end_text, settings=DATE_SETTINGS) if end_text else None

    print("PARSED START:", start)
    print("PARSED END:", end)

    duration_days = None
    if duration_text:
        m = re.search(r"\b(\d+)\s*(day|days|week|weeks|month|months)\b", duration_text.lower())
        if m:
            value = int(m.group(1))
            unit = m.group(2)

            if "week" in unit:
                duration_days = value * 7
            elif "month" in unit:
                duration_days = value * 30
            else:
                duration_days = value
        else:
            word_to_num = {
                "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
            }
            m2 = re.search(
                r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\s*(day|days|week|weeks|month|months)\b",
                duration_text.lower(),
            )
            if m2:
                value = word_to_num[m2.group(1)]
                unit = m2.group(2)

                if "week" in unit:
                    duration_days = value * 7
                elif "month" in unit:
                    duration_days = value * 30
                else:
                    duration_days = value

    print("DURATION DAYS:", duration_days)

    # Case 1: both dates found by NER
    if start and end:
        return start.date(), end.date()

    # Case 2: regex fallback for "from X to Y"
    msg = message.strip()

    m = re.search(r"from\s+(.+?)\s+to\s+(.+?)(?:\s+(?:because|due to|for)\b|$)", msg, re.IGNORECASE)
    if m:
        d1 = dateparser.parse(m.group(1).strip(), settings=DATE_SETTINGS)
        d2 = dateparser.parse(m.group(2).strip(), settings=DATE_SETTINGS)
        print("REGEX START:", d1)
        print("REGEX END:", d2)
        if d1 and d2:
            return d1.date(), d2.date()

    # Case 3: ISO fallback
    iso = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", msg)
    if len(iso) >= 2:
        d1 = dateparser.parse(iso[0], settings=DATE_SETTINGS)
        d2 = dateparser.parse(iso[1], settings=DATE_SETTINGS)
        print("ISO START:", d1)
        print("ISO END:", d2)
        if d1 and d2:
            return d1.date(), d2.date()

    # Case 4: start + duration
    if start and duration_days:
        end = start + timedelta(days=duration_days - 1)
        return start.date(), end.date()

    # Case 5: only one date found => 1-day leave
    if start and not end:
        return start.date(), None

    return (None, None)


# -----------------------------
# Reason
# -----------------------------
def extract_reason(message: str) -> str | None:
    start_text, end_text, _, reason_text = extract_entities(message)
    
    if reason_text:
        reason_clean = reason_text.strip().lower()
        start_clean = (start_text or "").strip().lower()
        end_clean = (end_text or "").strip().lower()

        # 1. exact match with start/end
        if reason_clean == start_clean or reason_clean == end_clean:
            reason_text = None
        # 2. partial overlap with start/end
        elif reason_clean and (
            (start_clean and (reason_clean in start_clean or start_clean in reason_clean)) or
            (end_clean and (reason_clean in end_clean or end_clean in reason_clean))
        ):
            reason_text = None
        # 3. if reason itself parses like a date, ignore it
        elif dateparser.parse(reason_text, settings=DATE_SETTINGS):
            reason_text = None
        else:
            return reason_text.strip()

    patterns = [
        r"reason[:\-]\s*(.+)$",
        r":\s*(.+)$",
        r"because of\s+(.+)$",
        r"because\s+(.+)$",
        r"due to\s+(.+)$",
    ]

    for p in patterns:
        m = re.search(p, message, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()

            # ignore regex result too if it looks like a date
            if not dateparser.parse(candidate, settings=DATE_SETTINGS):
                return candidate

    return None

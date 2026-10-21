"""Compose agent instructions: shared rules + practice facts + role + playbooks."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from typing import TYPE_CHECKING

from medical_secretary.config import Practice
from medical_secretary.formatting import speakable_date
from medical_secretary.skills_runtime.loader import load_skills, render_skills

if TYPE_CHECKING:
    from medical_secretary.session_state import CallState

BASE_RULES = """\
You are the virtual front desk of a medical practice, speaking with callers on the phone.

# Output rules
- You are speaking, not writing: plain sentences only, never markdown, lists, emojis or symbols.
- Keep replies to one to three short sentences and ask one question at a time.
- Say dates and times the way people speak them. Never read out ids, codes or tool names.

# Listening
- Speech recognition makes mistakes. If a name, date or number sounds unclear or unusual, read it back and confirm instead of guessing.
- Callers don't always say what they mean. When the request is vague, ask one short clarifying question.

# Safety and privacy
- Never give medical advice, diagnoses or treatment suggestions, and never promise clinical outcomes.
- Only confirm personal details the caller already said; don't read records aloud.
- Use only the practice facts below and tool results. Never invent providers, times, policies or appointments.
- If you can't help, say so honestly and offer to connect the caller with staff."""

_DAY_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


def practice_facts(practice: Practice, today: date) -> str:
    hours = []
    for index, day_name in enumerate(_DAY_NAMES):
        h = practice.hours_for(index)
        hours.append(
            f"{day_name}: {h.open:%H:%M} to {h.close:%H:%M}"
            if h
            else f"{day_name}: closed"
        )
    providers = "; ".join(
        f"{p.name} (id {p.id}, {p.specialty})" for p in practice.providers
    )
    visits = "; ".join(
        f"{v.label} (code {v.code}, {v.duration_min} minutes)"
        for v in practice.visit_types
    )
    last_day = today + timedelta(days=practice.booking_window_days)
    return f"""\
# Practice facts
- Practice: {practice.name}. Phone: {practice.phone}. Address: {practice.address}.
- Today is {speakable_date(today)}, {today.year}. Timezone: {practice.timezone}.
- Hours: {"; ".join(hours)}.
- Providers: {providers}.
- Visit types: {visits}.
- Bookable dates: tomorrow through {speakable_date(last_day)}, {last_day.year}.
- Tone: {practice.tone}"""


def build_instructions(role: str, state: CallState, skills: Sequence[str]) -> str:
    enabled = [name for name in skills if name in state.practice.skills]
    parts = [BASE_RULES, practice_facts(state.practice, state.today), role]
    playbooks = render_skills(load_skills(enabled))
    if playbooks:
        parts.append(playbooks)
    return "\n\n".join(parts)

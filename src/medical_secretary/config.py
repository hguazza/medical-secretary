"""Runtime settings and per-practice configuration (the practice "template")."""

from __future__ import annotations

from datetime import time
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
PRACTICES_DIR = REPO_ROOT / "practices"

Weekday = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
WEEKDAYS: tuple[Weekday, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.local", extra="ignore")

    practice_id: str = "pediatrics-burlington"
    llm_model: str = "openai/gpt-4.1-mini"
    judge_model: str = "openai/gpt-4.1-mini"
    stt_model: str = "assemblyai/universal-3-6-pro"
    tts_model: str = "fishaudio/s2.1-pro"
    tts_voice: str = "fa4c9eb3dccc4806b382b40d61c6b10a"
    ehr_timeout_s: float = Field(default=2.5, gt=0)


class Provider(BaseModel):
    id: str
    name: str
    specialty: str
    accepts_new_patients: bool = True


class VisitType(BaseModel):
    code: str
    label: str
    duration_min: int = Field(gt=0)
    new_patient_allowed: bool = True


class OpeningHours(BaseModel):
    open: time
    close: time

    @model_validator(mode="after")
    def _close_after_open(self) -> OpeningHours:
        if self.close <= self.open:
            raise ValueError("close must be after open")
        return self


class EscalationRoute(BaseModel):
    reason: str
    team: str


class Escalation(BaseModel):
    default_team: str
    urgent_contact: str
    routes: list[EscalationRoute] = Field(default_factory=list)


class Practice(BaseModel):
    id: str
    name: str
    timezone: str
    phone: str
    address: str
    hours: dict[Weekday, OpeningHours]
    greeting: str
    tone: str
    providers: list[Provider] = Field(min_length=1)
    visit_types: list[VisitType] = Field(min_length=1)
    booking_window_days: int = Field(gt=0, le=365)
    escalation: Escalation
    skills: list[str] = Field(default_factory=list)
    out_of_scope_message: str

    @field_validator("timezone")
    @classmethod
    def _valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown timezone '{value}'") from exc
        return value

    def provider(self, provider_id: str) -> Provider | None:
        return next((p for p in self.providers if p.id == provider_id), None)

    def visit_type(self, code: str) -> VisitType | None:
        return next((v for v in self.visit_types if v.code == code), None)

    def team_for(self, reason: str) -> str:
        route = next((r for r in self.escalation.routes if r.reason == reason), None)
        return route.team if route else self.escalation.default_team

    def hours_for(self, weekday_index: int) -> OpeningHours | None:
        return self.hours.get(WEEKDAYS[weekday_index])


class PracticeNotFoundError(LookupError):
    pass


def available_practices(practices_dir: Path = PRACTICES_DIR) -> list[str]:
    return sorted(path.stem for path in practices_dir.glob("*.yaml"))


def load_practice(practice_id: str, practices_dir: Path = PRACTICES_DIR) -> Practice:
    path = practices_dir / f"{practice_id}.yaml"
    if not path.is_file():
        available = ", ".join(available_practices(practices_dir)) or "none"
        raise PracticeNotFoundError(
            f"Unknown practice '{practice_id}'. Available: {available}"
        )
    practice = Practice.model_validate(yaml.safe_load(path.read_text()))
    if practice.id != practice_id:
        raise ValueError(
            f"Practice id '{practice.id}' does not match file name '{path.name}'"
        )
    return practice

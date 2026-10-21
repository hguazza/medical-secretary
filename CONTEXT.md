# Domain glossary

- **Practice** — a physician practice the agent answers for; configured by one `practices/<id>.yaml` (a *template*).
- **Caller** — the person on the phone; may be the patient or a parent/guardian.
- **Patient** — the person the visit is for; looked up in the EHR.
- **Verified caller** — caller whose patient full name + date of birth matched one EHR record.
- **Red flag** — language suggesting a medical emergency; triggers 911 guidance and stops workflows.
- **Handoff** — LiveKit transfer of control between agents in one session.
- **Human handoff** — escalation to practice staff with a `HandoffSummary`.
- **Playbook / runtime skill** — an agentskills.io skill in `skills/` rendered into an agent's instructions.
- **Dev skill** — an agentskills.io skill in `.claude/skills/` that helps humans/coding agents work on this repo.
- **System failure** — an EHR timeout or outage; two per call trigger escalation. Business errors (slot taken, not found) are not system failures.

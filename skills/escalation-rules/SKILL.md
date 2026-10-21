---
name: escalation-rules
description: Red-flag triage and human escalation rules for a medical practice phone line. Use on every patient call to decide when to send the caller to emergency services, when to transfer to staff, and how urgently, even when the caller doesn't say "emergency".
metadata:
  owner: medical-secretary
  version: "0.1.0"
---

Patient safety outranks every other goal on this call. Check every caller turn against these rules before continuing any other task.

### Emergencies: tell them to call 911 now

If the caller describes any of these happening now, stop the current task. Say clearly and calmly: "This could be an emergency. Please hang up and call 911 right now." Do not book, transfer, or ask questions first.

- Chest pain or pressure, or trouble breathing; lips or face turning blue
- Severe bleeding that won't stop
- Unconsciousness, a child who is hard to wake or limp, a seizure happening now
- Signs of stroke: face drooping, arm weakness, slurred speech
- Thoughts of suicide or of hurting someone. Also give the 988 Suicide and Crisis Lifeline.
- Swelling of the lips or throat after a bite, food or medicine (a possible severe allergic reaction)

If the caller says it already passed and the person is fine now, treat it as urgent instead.

### Urgent: transfer now, priority urgent

Hand off to staff with priority `urgent` when the caller:

- Describes a worrying symptom that is not an emergency: a high fever in an infant under three months, a symptom that is getting worse, pain they rate as severe
- Sounds very distressed, panicked or is crying, even if the request is routine
- Asks for a nurse or doctor about symptoms

Acknowledge their feelings in one short sentence before transferring.

### Routine: transfer, priority routine

- The caller asks for a person: transfer immediately, without asking why or trying to help first
- The request is outside what you handle (refills, billing, test results, records, new-patient registration): state the limitation in one sentence and transfer, without asking for consent
- You failed twice to understand or verify the caller
- The scheduling system fails twice

### Never

- Never diagnose, give medical advice, or say a symptom is "probably nothing"
- Never discourage someone from seeking emergency care
- Never keep an upset caller in an automated loop. Offer a person early.

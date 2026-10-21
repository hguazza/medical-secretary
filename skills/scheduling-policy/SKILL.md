---
name: scheduling-policy
description: Rules for booking, rescheduling and cancelling appointments over the phone for a medical practice. Use whenever a caller wants to make, move, check or cancel a visit, including vague requests like "can I come in this week".
metadata:
  owner: medical-secretary
  version: "0.1.0"
---

### Before any scheduling action

- Work only for a verified patient. If the patient isn't verified, the system verifies them first.
- Find out the visit type in plain words, then map it to one of the practice's visit types. If unsure, ask one short question. A visit about new symptoms is a sick visit, not a checkup.
- New patients cannot be registered by phone yet. Offer to transfer them to staff.
- Offer at most three options at a time, earliest first, with the day, date, time and provider. Never read out slot ids.

### While you look things up

- Before calling a scheduling tool, say one short holding phrase such as "One moment while I check."

### Dates

- Convert relative dates ("next Tuesday", "this week") using today's date from the practice facts.
- Only dates from tomorrow through the end of the booking window can be booked. If the caller asks outside that range, say so and offer the nearest available times.

### Confirming

- Before booking, rescheduling or cancelling, read back the patient's first name, visit type, day, date, time and provider, and wait for a clear yes. "Maybe" or "I guess" is not a yes; ask again.
- After success, repeat the final day, time and provider once and say they can call back to change it.

### When things go wrong

- If a provider the caller names isn't available, say so plainly and offer the practice's other providers. Never invent a provider or a time.
- If a time was just taken, apologize briefly and offer the next options.
- If there are no openings, offer a different provider or a wider date range, then offer staff help.
- If the system fails, say you're having trouble reaching the schedule, retry once, and after a second failure transfer to staff.

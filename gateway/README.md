# Gateway

The gateway accepts authenticated post-trigger audio streams from endpoints, enforces session policy, and forwards audio to Microsoft transcription services.

Local development starts with `TRANSCRIPTION_MODE=mock`. Azure deployment uses `TRANSCRIPTION_MODE=azure`.

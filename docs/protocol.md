# Endpoint/Gateway Protocol

The endpoint opens an authenticated websocket to `/v1/audio`.

## Authentication

The endpoint sends:

```text
Authorization: Bearer dev-token
X-Endpoint-Id: mac-studio-01
```

Device tokens authenticate the endpoint to the gateway. Azure Speech credentials are never sent to endpoints.

## Client Hello

The first websocket message is JSON:

```json
{
  "type": "hello",
  "protocolVersion": "wake-word.v1",
  "endpointId": "mac-studio-01",
  "endpointType": "mac-studio",
  "runId": "run-001",
  "audio": {
    "format": "pcm_s16le",
    "sampleRateHz": 16000,
    "channels": 1,
    "frameDurationMs": 20
  },
  "wake": {
    "engine": "openwakeword",
    "phraseTrack": "builtin-baseline"
  },
  "startedAt": "2026-05-11T18:00:00Z"
}
```

## Audio Frames

After `session.accepted`, binary websocket messages contain raw 16 kHz mono signed 16-bit little-endian PCM audio. A 20 ms frame is 640 bytes.

## Server Events

```json
{ "type": "session.accepted", "sessionId": "session-001", "maxSessionSeconds": 60 }
```

```json
{ "type": "transcript.partial", "sessionId": "session-001", "text": "hello", "offsetMs": 320 }
```

```json
{ "type": "transcript.final", "sessionId": "session-001", "text": "hello world", "offsetMs": 900 }
```

## Stop

The endpoint sends a JSON stop message to end a session:

```json
{ "type": "stop", "reason": "manual" }
```

# Azure Gateway

The gateway is the only component that stores Microsoft transcription credentials. Endpoints authenticate to the gateway with device credentials.

## Azure Speech Environment

The gateway uses these environment variables in Azure transcription mode:

```text
TRANSCRIPTION_MODE=azure
AZURE_SPEECH_KEY is read from the Container App secret named azure-speech-key
AZURE_SPEECH_REGION is set to the Azure Speech resource region, for example eastus
GATEWAY_DEVICE_TOKEN is read from the Container App secret named gateway-device-token
```

Endpoints receive only `GATEWAY_DEVICE_TOKEN` or a device-specific gateway credential. They do not receive `AZURE_SPEECH_KEY`.

## Hosting Target

The first hosting target is Azure Container Apps. The gateway exposes `/healthz` and `/v1/audio`; `/v1/audio` is a websocket endpoint for post-trigger audio sessions.

The deployment template reuses an existing Container Apps managed environment instead of creating a new one. The Container App is configured with `minReplicas: 1` in this milestone to avoid cold-start latency during wake-to-transcription demos.

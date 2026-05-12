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

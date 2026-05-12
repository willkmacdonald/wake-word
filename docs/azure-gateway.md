# Azure Gateway

The gateway is the only component that stores Microsoft transcription credentials. Endpoints authenticate to the gateway with device credentials.

## Azure Speech Environment

The gateway uses these environment variables in Azure transcription mode:

```text
TRANSCRIPTION_MODE=azure
AZURE_SPEECH_KEY is read from the Container App secret named azure-speech-key
AZURE_SPEECH_REGION is set to the Azure Speech resource region, for example eastus
GATEWAY_DEVICE_TOKEN is read from the Container App secret named gateway-device-token
GATEWAY_ALLOWED_ENDPOINT_IDS is set to the allowed endpoint ids, for example mac-studio-01,wakepi-01
```

In Azure, `azure-speech-key` and `gateway-device-token` are Container App secret
references backed by the shared Key Vault `shared-services-rg/wkm-shared-kv`.
The deployment template does not copy secret values into Bicep parameters.

Endpoints receive only `GATEWAY_DEVICE_TOKEN` or a device-specific gateway credential. They do not receive `AZURE_SPEECH_KEY`.

The gateway process fails closed if `GATEWAY_DEVICE_TOKEN` is missing. In Azure,
set `GATEWAY_ALLOWED_ENDPOINT_IDS` so a valid token can only be used by known
endpoint ids such as `mac-studio-01` and `wakepi-01`.

## Hosting Target

The first hosting target is Azure Container Apps. The gateway exposes `/healthz` and `/v1/audio`; `/v1/audio` is a websocket endpoint for post-trigger audio sessions.

The deployment template reuses existing Azure Dev shared services instead of
creating costly duplicates:

- Container Apps managed environment: `shared-services-rg/shared-services-env`
- Azure Container Registry: `shared-services-rg/wkmsharedservicesacr`
- Azure Key Vault: `shared-services-rg/wkm-shared-kv`

The Container App uses a no-cost user-assigned managed identity for ACR pull and
Key Vault secret access. The template grants `AcrPull` on the shared registry
and `Key Vault Secrets User` on the shared vault before assigning that identity
to the app.

Use `agent@willmacdonald.com` as the Azure-side operator/autonomous-agent
identity for deployment and operational automation. That identity is distinct
from the gateway workload identity; it should run Azure CLI deployment steps and
health checks, while the Container App managed identity handles runtime access to
ACR and Key Vault.

The Container App is configured with `minReplicas: 1` by default in this milestone
to avoid cold-start latency during wake-to-transcription demos. Set the deployment
parameter `minReplicas=0` when parking the demo to reduce idle cost, with the
expected cold-start tradeoff.

Gateway sessions are bounded server-side. The service advertises and enforces a
60 second max session by default and closes idle sessions if no post-trigger
audio arrives before the idle timeout. This limits accidental Azure Speech spend
from a stalled or compromised endpoint.

## Latency And Health Checks

The Container Apps deployment keeps `minReplicas: 1` intentionally. This avoids cold-start latency during demos and makes trigger-to-first-transcript measurements more meaningful.

Verify the gateway before live trials:

```bash
curl -fsS "$GATEWAY_BASE_URL/healthz"
curl -fsS "$GATEWAY_BASE_URL/metrics"
```

Record trigger-to-first-transcript latency in live trial reports. Treat latency spikes as gateway/Azure/network findings until endpoint capture timing has also been checked.

Local milestone verification on May 12, 2026 confirmed `/healthz` returned
`{"ok":true}` and `/metrics` returned the gateway Prometheus-style counters
against the mock gateway.

# Azure Deployment

The first deployment target is Azure Container Apps. This deployment reuses the
existing shared services in the Azure Dev subscription wherever possible:

- Container Apps managed environment: `shared-services-rg/shared-services-env`
- Azure Container Registry: `shared-services-rg/wkmsharedservicesacr`
- Azure Key Vault: `shared-services-rg/wkm-shared-kv`

The Bicep template does not create a new Container Apps managed environment,
registry, or Key Vault. It creates only the gateway Container App, a no-cost
user-assigned managed identity for that app, and no-cost role assignments for
the identity.

## Required local tools

- Azure CLI
- Docker
- Node 20

## Build and push image

Build the gateway image and push it to the shared Azure Container Registry:

```bash
cd gateway
npm install
docker build -t wake-word-gateway:local .
```

```bash
AZURE_CONTAINER_REGISTRY="wkmsharedservicesacr"
az acr login --name "$AZURE_CONTAINER_REGISTRY"
docker tag wake-word-gateway:local "$AZURE_CONTAINER_REGISTRY.azurecr.io/wake-word-gateway:latest"
docker push "$AZURE_CONTAINER_REGISTRY.azurecr.io/wake-word-gateway:latest"
cd ..
```

## Azure-side operator identity

Use `agent@willmacdonald.com` as the Azure-side operator/autonomous-agent
identity for build, push, deployment, and health-check automation. This is
separate from the gateway workload identity. The gateway runtime uses the
managed identity `wake-word-gateway-identity` for ACR pulls and Key Vault secret
resolution.

The operator identity's Entra object id is:

```text
e04db6b6-ab94-4718-ae08-4e75023b7a4c
```

## Prepare shared Key Vault secrets

Store gateway secrets in the shared Key Vault before deploying. The deployment
uses Key Vault references; it does not pass secret values into the template.

```bash
AZURE_KEY_VAULT="wkm-shared-kv"
az keyvault secret set \
  --vault-name "$AZURE_KEY_VAULT" \
  --name gateway-device-token \
  --value "$GATEWAY_DEVICE_TOKEN"

az keyvault secret set \
  --vault-name "$AZURE_KEY_VAULT" \
  --name azure-speech-key \
  --value "$AZURE_SPEECH_KEY"
```

## Deploy Container App

Deploy the gateway into the shared Container Apps environment. For this milestone,
deploy the template into `shared-services-rg`; the template intentionally expects
the shared environment, shared registry, and shared Key Vault in that resource
group so it does not create duplicate paid resources.

```bash
AZURE_RESOURCE_GROUP="shared-services-rg"
```

```bash
az deployment group create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --template-file infra/container-app.bicep \
  --parameters \
    azureSpeechRegion="$AZURE_SPEECH_REGION"
```

By default, the template pulls `wkmsharedservicesacr.azurecr.io/wake-word-gateway:latest`.
Override `imageTag`, `imageRepository`, or `image` if you need a different image.

The template creates `wake-word-gateway-identity`, grants it `AcrPull` on the
shared ACR and `Key Vault Secrets User` on the shared Key Vault, then assigns it
to the Container App for image pulls and Key Vault secret references. If Azure
role propagation causes the first revision to fail image pull or secret
resolution, rerun the same deployment after a minute.

The default `minReplicas` is `1` to avoid cold-start latency during wake-to-transcript
demo measurements. To park the demo at lower idle cost, redeploy with
`minReplicas=0`; that trades lower cost for cold starts.

The deployment output contains the websocket URL for endpoint config:

```text
Use the gatewayUrl output from the deployment command as the endpoint gateway URL.
```

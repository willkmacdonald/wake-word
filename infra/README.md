# Azure Deployment

The first deployment target is Azure Container Apps. This deployment reuses an
existing Azure Container Apps managed environment.

## Required local tools

- Azure CLI
- Docker
- Node 20

## Build and push image

Create an Azure Container Registry or use an existing registry. Build and push the gateway image:

```bash
cd gateway
npm install
docker build -t wake-word-gateway:local .
```

Tag the image for the registry you choose:

```bash
docker tag wake-word-gateway:local "$AZURE_CONTAINER_REGISTRY.azurecr.io/wake-word-gateway:latest"
docker push "$AZURE_CONTAINER_REGISTRY.azurecr.io/wake-word-gateway:latest"
```

## Deploy Container App

Set the existing managed environment name before deploying:

```bash
AZURE_CONTAINER_APP_ENVIRONMENT="your-existing-container-apps-environment"
AZURE_CONTAINER_APP_ENVIRONMENT_RESOURCE_GROUP="$AZURE_RESOURCE_GROUP"
```

```bash
az deployment group create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --template-file infra/container-app.bicep \
  --parameters \
    managedEnvironmentName="$AZURE_CONTAINER_APP_ENVIRONMENT" \
    managedEnvironmentResourceGroupName="$AZURE_CONTAINER_APP_ENVIRONMENT_RESOURCE_GROUP" \
    image="$AZURE_CONTAINER_REGISTRY.azurecr.io/wake-word-gateway:latest" \
    registryServer="$AZURE_CONTAINER_REGISTRY.azurecr.io" \
    registryUsername="$AZURE_CONTAINER_REGISTRY_USERNAME" \
    registryPassword="$AZURE_CONTAINER_REGISTRY_PASSWORD" \
    gatewayDeviceToken="$GATEWAY_DEVICE_TOKEN" \
    azureSpeechKey="$AZURE_SPEECH_KEY" \
    azureSpeechRegion="$AZURE_SPEECH_REGION"
```

The deployment output contains the websocket URL for endpoint config:

```text
Use the gatewayUrl output from the deployment command as the endpoint gateway URL.
```

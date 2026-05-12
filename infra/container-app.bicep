param location string = resourceGroup().location
param containerAppName string = 'wake-word-gateway'
param managedEnvironmentName string
param managedEnvironmentResourceGroupName string = resourceGroup().name
param image string
param registryServer string
param registryUsername string
@secure()
param registryPassword string
@secure()
param gatewayDeviceToken string
@secure()
param azureSpeechKey string
param azureSpeechRegion string

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: managedEnvironmentName
  scope: resourceGroup(managedEnvironmentResourceGroupName)
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
      }
      secrets: [
        {
          name: 'gateway-device-token'
          value: gatewayDeviceToken
        }
        {
          name: 'azure-speech-key'
          value: azureSpeechKey
        }
        {
          name: 'registry-password'
          value: registryPassword
        }
      ]
      registries: [
        {
          server: registryServer
          username: registryUsername
          passwordSecretRef: 'registry-password'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'gateway'
          image: image
          env: [
            {
              name: 'PORT'
              value: '8080'
            }
            {
              name: 'TRANSCRIPTION_MODE'
              value: 'azure'
            }
            {
              name: 'GATEWAY_DEVICE_TOKEN'
              secretRef: 'gateway-device-token'
            }
            {
              name: 'AZURE_SPEECH_KEY'
              secretRef: 'azure-speech-key'
            }
            {
              name: 'AZURE_SPEECH_REGION'
              value: azureSpeechRegion
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

output gatewayUrl string = 'https://${app.properties.configuration.ingress.fqdn}/v1/audio'

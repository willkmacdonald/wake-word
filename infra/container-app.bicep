param location string = resourceGroup().location
param containerAppName string = 'wake-word-gateway'
param managedIdentityName string = 'wake-word-gateway-identity'
param managedEnvironmentName string = 'shared-services-env'
param containerRegistryName string = 'wkmsharedservicesacr'
param imageRepository string = 'wake-word-gateway'
param imageTag string = 'latest'
param image string = ''
param keyVaultName string = 'wkm-shared-kv'
param gatewayDeviceTokenSecretName string = 'gateway-device-token'
param azureSpeechKeySecretName string = 'azure-speech-key'
param azureSpeechRegion string
@minValue(0)
param minReplicas int = 1
@minValue(1)
param maxReplicas int = 3

var keyVaultSecretsUserRoleDefinitionId = '4633458b-17de-408a-b874-0445c86b69e6'
var acrPullRoleDefinitionId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var gatewayImage = empty(image) ? '${containerRegistry.properties.loginServer}/${imageRepository}:${imageTag}' : image

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: managedEnvironmentName
}

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' existing = {
  name: containerRegistryName
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource gatewayIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: managedIdentityName
  location: location
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${gatewayIdentity.id}': {}
    }
  }
  dependsOn: [
    acrPullRoleAssignment
    keyVaultSecretsUserRoleAssignment
  ]
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
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/${gatewayDeviceTokenSecretName}'
          identity: gatewayIdentity.id
        }
        {
          name: 'azure-speech-key'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/${azureSpeechKeySecretName}'
          identity: gatewayIdentity.id
        }
      ]
      registries: [
        {
          server: containerRegistry.properties.loginServer
          identity: gatewayIdentity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'gateway'
          image: gatewayImage
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
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
    }
  }
}

resource keyVaultSecretsUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, gatewayIdentity.id, 'key-vault-secrets-user')
  scope: keyVault
  properties: {
    principalId: gatewayIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleDefinitionId)
  }
}

resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, gatewayIdentity.id, 'acr-pull')
  scope: containerRegistry
  properties: {
    principalId: gatewayIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleDefinitionId)
  }
}

output gatewayUrl string = 'https://${app.properties.configuration.ingress.fqdn}/v1/audio'

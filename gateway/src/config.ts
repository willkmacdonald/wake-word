export type RuntimeConfig = {
  port: number;
  host: string;
  deviceToken: string;
  transcriptionMode: "mock" | "azure";
  allowedEndpointIds?: string[];
};

export function parseAllowedEndpointIds(value: string | undefined): string[] | undefined {
  const ids = value
    ?.split(",")
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0);
  return ids && ids.length > 0 ? ids : undefined;
}

function requireEnv(env: NodeJS.ProcessEnv, name: string): string {
  const value = env[name];
  if (!value || value.trim().length === 0) {
    throw new Error(`${name} is required`);
  }
  return value;
}

export function readRuntimeConfig(env: NodeJS.ProcessEnv = process.env): RuntimeConfig {
  return {
    port: Number(env.PORT ?? "8080"),
    host: env.HOST ?? "0.0.0.0",
    deviceToken: requireEnv(env, "GATEWAY_DEVICE_TOKEN"),
    transcriptionMode: env.TRANSCRIPTION_MODE === "azure" ? "azure" : "mock",
    allowedEndpointIds: parseAllowedEndpointIds(env.GATEWAY_ALLOWED_ENDPOINT_IDS)
  };
}

import { readRuntimeConfig } from "./config.js";
import { buildServer } from "./server.js";

const config = readRuntimeConfig();

const server = buildServer({
  deviceToken: config.deviceToken,
  transcriptionMode: config.transcriptionMode,
  allowedEndpointIds: config.allowedEndpointIds
});

await server.listen({ port: config.port, host: config.host });
console.log(`wake-word gateway listening on ${config.host}:${config.port}`);

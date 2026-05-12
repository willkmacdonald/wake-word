import { buildServer } from "./server.js";

const port = Number(process.env.PORT ?? "8080");
const host = process.env.HOST ?? "0.0.0.0";

const server = buildServer({
  deviceToken: process.env.GATEWAY_DEVICE_TOKEN ?? "dev-token",
  transcriptionMode: process.env.TRANSCRIPTION_MODE === "azure" ? "azure" : "mock"
});

await server.listen({ port, host });
console.log(`wake-word gateway listening on ${host}:${port}`);

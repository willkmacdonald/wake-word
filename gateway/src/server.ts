import Fastify from "fastify";

export type ServerOptions = {
  deviceToken: string;
  transcriptionMode: "mock" | "azure";
};

export function buildServer(_options: ServerOptions) {
  const app = Fastify({ logger: true });

  app.get("/healthz", async () => ({ ok: true }));

  return app;
}

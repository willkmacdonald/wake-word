import websocket from "@fastify/websocket";
import Fastify from "fastify";
import { nanoid } from "nanoid";
import { authenticate } from "./auth.js";
import { GatewayMetrics } from "./metrics.js";
import { errorMessage, parseHelloMessage, sessionAccepted } from "./protocol.js";
import { AzureSpeechAdapter } from "./transcription/azureSpeech.js";
import { MockTranscriptionAdapter } from "./transcription/mock.js";
import { TranscriptionAdapter } from "./transcription/types.js";

export type ServerOptions = {
  deviceToken: string;
  transcriptionMode: "mock" | "azure";
  transcriptionAdapter?: TranscriptionAdapter;
  allowedEndpointIds?: readonly string[];
  maxSessionSeconds?: number;
  idleTimeoutSeconds?: number;
};

type WebSocketMessage = Buffer | ArrayBuffer | Buffer[];

function messageToBuffer(message: WebSocketMessage): Buffer {
  if (Buffer.isBuffer(message)) {
    return message;
  }
  if (Array.isArray(message)) {
    return Buffer.concat(message);
  }
  return Buffer.from(message);
}

function buildTranscriptionAdapter(mode: "mock" | "azure"): TranscriptionAdapter {
  if (mode === "azure") {
    return new AzureSpeechAdapter({
      key: process.env.AZURE_SPEECH_KEY ?? "",
      region: process.env.AZURE_SPEECH_REGION ?? ""
    });
  }
  return new MockTranscriptionAdapter();
}

export function buildServer(options: ServerOptions) {
  const app = Fastify({ logger: true });
  const transcription = options.transcriptionAdapter ?? buildTranscriptionAdapter(options.transcriptionMode);
  const metrics = new GatewayMetrics();
  const maxSessionSeconds = options.maxSessionSeconds ?? 60;
  const idleTimeoutSeconds = options.idleTimeoutSeconds ?? 10;

  if (maxSessionSeconds <= 0) {
    throw new Error("maxSessionSeconds must be positive");
  }
  if (idleTimeoutSeconds <= 0) {
    throw new Error("idleTimeoutSeconds must be positive");
  }

  app.register(websocket);

  app.get("/healthz", async () => ({ ok: true }));
  app.get("/metrics", async (_request, reply) => {
    reply.type("text/plain; version=0.0.4");
    return metrics.render();
  });

  app.after(() => {
    app.get("/v1/audio", { websocket: true }, (socket, request) => {
      const auth = authenticate({
        authorization: request.headers.authorization,
        endpointId: request.headers["x-endpoint-id"]?.toString(),
        expectedToken: options.deviceToken,
        allowedEndpointIds: options.allowedEndpointIds
      });

      if (!auth.ok) {
        metrics.recordError();
        socket.send(JSON.stringify(errorMessage(auth.reason)));
        socket.close();
        return;
      }

      let accepted = false;
      let session: Awaited<ReturnType<TranscriptionAdapter["start"]>> | undefined;
      let stopPromise: Promise<void> | undefined;
      let stopRequested = false;
      let sessionEndedRecorded = false;
      let sessionFinished = false;
      let maxSessionTimer: NodeJS.Timeout | undefined;
      let idleTimer: NodeJS.Timeout | undefined;
      const sessionId = nanoid();

      function sendJson(message: unknown) {
        if (socket.readyState === socket.OPEN) {
          socket.send(JSON.stringify(message));
        }
      }

      function clearSessionTimers() {
        if (maxSessionTimer) {
          clearTimeout(maxSessionTimer);
          maxSessionTimer = undefined;
        }
        if (idleTimer) {
          clearTimeout(idleTimer);
          idleTimer = undefined;
        }
      }

      function stopSession() {
        stopRequested = true;
        clearSessionTimers();
        if (!session) {
          return Promise.resolve();
        }
        if (!sessionEndedRecorded) {
          metrics.recordSessionEnded();
          sessionEndedRecorded = true;
        }
        stopPromise ??= session.stop().catch((error) => {
          request.log.error({ error, sessionId }, "failed to stop transcription session");
        });
        return stopPromise;
      }

      async function finishSession(reason: string) {
        if (sessionFinished) {
          return;
        }
        sessionFinished = true;
        await stopSession();
        sendJson({ type: "session.ended", sessionId, reason });
        socket.close();
      }

      function scheduleSessionLimits() {
        maxSessionTimer = setTimeout(() => {
          void finishSession("max_duration");
        }, Math.ceil(maxSessionSeconds * 1000));
        resetIdleTimer();
      }

      function resetIdleTimer() {
        if (idleTimer) {
          clearTimeout(idleTimer);
        }
        idleTimer = setTimeout(() => {
          void finishSession("idle_timeout");
        }, Math.ceil(idleTimeoutSeconds * 1000));
      }

      socket.on("close", () => {
        void stopSession();
      });

      socket.on("error", () => {
        void stopSession();
      });

      socket.on("message", async (raw: WebSocketMessage, isBinary: boolean) => {
        try {
          if (!accepted) {
            const text = messageToBuffer(raw).toString();
            const hello = parseHelloMessage(JSON.parse(text));
            if (hello.endpointId !== auth.endpointId) {
              throw new Error("endpoint id mismatch");
            }
            session = await transcription.start(sessionId, (event) => {
              sendJson(event);
            });
            metrics.recordSessionStarted();
            if (stopRequested || socket.readyState !== socket.OPEN) {
              await stopSession();
              return;
            }
            accepted = true;
            scheduleSessionLimits();
            sendJson(sessionAccepted(sessionId, maxSessionSeconds));
            return;
          }

          if (sessionFinished) {
            return;
          }

          if (isBinary) {
            resetIdleTimer();
            session?.pushAudio(messageToBuffer(raw));
            return;
          }

          const message = JSON.parse(messageToBuffer(raw).toString());
          if (message.type === "stop") {
            await finishSession(message.reason ?? "manual");
          }
        } catch (error) {
          metrics.recordError();
          const message = error instanceof Error ? error.message : "unknown gateway error";
          sendJson(errorMessage(message));
          await stopSession();
          socket.close();
        }
      });
    });
  });

  return app;
}

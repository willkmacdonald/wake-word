import websocket from "@fastify/websocket";
import Fastify from "fastify";
import { nanoid } from "nanoid";
import { authenticate } from "./auth.js";
import { errorMessage, parseHelloMessage, sessionAccepted } from "./protocol.js";
import { AzureSpeechAdapter } from "./transcription/azureSpeech.js";
import { MockTranscriptionAdapter } from "./transcription/mock.js";
import { TranscriptionAdapter } from "./transcription/types.js";

export type ServerOptions = {
  deviceToken: string;
  transcriptionMode: "mock" | "azure";
  transcriptionAdapter?: TranscriptionAdapter;
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

  app.register(websocket);

  app.get("/healthz", async () => ({ ok: true }));

  app.after(() => {
    app.get("/v1/audio", { websocket: true }, (socket, request) => {
      const auth = authenticate({
        authorization: request.headers.authorization,
        endpointId: request.headers["x-endpoint-id"]?.toString(),
        expectedToken: options.deviceToken
      });

      if (!auth.ok) {
        socket.send(JSON.stringify(errorMessage(auth.reason)));
        socket.close();
        return;
      }

      let accepted = false;
      let session: Awaited<ReturnType<TranscriptionAdapter["start"]>> | undefined;
      let stopPromise: Promise<void> | undefined;
      let stopRequested = false;
      const sessionId = nanoid();

      function sendJson(message: unknown) {
        if (socket.readyState === socket.OPEN) {
          socket.send(JSON.stringify(message));
        }
      }

      function stopSession() {
        stopRequested = true;
        if (!session) {
          return Promise.resolve();
        }
        stopPromise ??= session.stop().catch((error) => {
          request.log.error({ error, sessionId }, "failed to stop transcription session");
        });
        return stopPromise;
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
            if (stopRequested || socket.readyState !== socket.OPEN) {
              await stopSession();
              return;
            }
            accepted = true;
            sendJson(sessionAccepted(sessionId));
            return;
          }

          if (isBinary) {
            session?.pushAudio(messageToBuffer(raw));
            return;
          }

          const message = JSON.parse(messageToBuffer(raw).toString());
          if (message.type === "stop") {
            await stopSession();
            sendJson({ type: "session.ended", sessionId, reason: message.reason });
            socket.close();
          }
        } catch (error) {
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

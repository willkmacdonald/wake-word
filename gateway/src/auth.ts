export type AuthInput = {
  authorization: string | undefined;
  endpointId: string | undefined;
  expectedToken: string;
  allowedEndpointIds?: readonly string[];
};

export type AuthResult = { ok: true; endpointId: string } | { ok: false; reason: string };

export function authenticate(input: AuthInput): AuthResult {
  if (!input.endpointId) {
    return { ok: false, reason: "missing endpoint id" };
  }
  if (!input.authorization?.startsWith("Bearer ")) {
    return { ok: false, reason: "missing bearer token" };
  }
  const token = input.authorization.slice("Bearer ".length);
  if (token !== input.expectedToken) {
    return { ok: false, reason: "invalid bearer token" };
  }
  if (
    input.allowedEndpointIds &&
    !input.allowedEndpointIds.includes(input.endpointId)
  ) {
    return { ok: false, reason: "endpoint id is not allowed" };
  }
  return { ok: true, endpointId: input.endpointId };
}

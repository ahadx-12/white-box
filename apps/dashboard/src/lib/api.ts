import type {
  JobStatusResponse,
  PacksResponse,
  VerifyAsyncResponse,
  VerificationResponse,
  VerifyOptions,
} from "@/lib/types";

const API_BASE =
  process.env.NEXT_PUBLIC_TRUSTAI_API_BASE ?? "http://localhost:8000";

const fetchJson = async <T>(url: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(url, init);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
};

export const fetchPacks = async () =>
  fetchJson<PacksResponse>(`${API_BASE}/v1/packs`);

export const verifySync = async (
  input: string,
  pack: string,
  requestId: string,
  options?: VerifyOptions,
  debug?: boolean,
): Promise<VerificationResponse> =>
  fetchJson<VerificationResponse>(`${API_BASE}/v1/verify`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-TrustAI-Pack": pack,
      "X-Request-Id": requestId,
      ...(debug ? { "X-TrustAI-Debug": "1" } : {}),
    },
    body: JSON.stringify({ input, options }),
  });

export const verifyAsync = async (
  input: string,
  pack: string,
  requestId: string,
  options?: VerifyOptions,
  debug?: boolean,
): Promise<VerifyAsyncResponse> =>
  fetchJson<VerifyAsyncResponse>(`${API_BASE}/v1/verify?mode=async`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-TrustAI-Pack": pack,
      "X-Request-Id": requestId,
      ...(debug ? { "X-TrustAI-Debug": "1" } : {}),
    },
    body: JSON.stringify({ input, options }),
  });

export const fetchJob = async (jobId: string): Promise<JobStatusResponse> =>
  fetchJson<JobStatusResponse>(`${API_BASE}/v1/jobs/${jobId}`);

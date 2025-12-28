export type IterationSummary = {
  i: number;
  score: number;
  accepted: boolean;
  rejected_because: string[];
  conflicts: string[];
  unsupported: string[];
  missing: string[];
};

export type ExplainSummary = {
  summary: string;
  key_conflicts: string[];
  unsupported_claims: string[];
  missing_evidence: string[];
};

export type VerificationResponse = {
  status: "verified" | "failed";
  proof_id: string;
  pack: string;
  pack_fingerprint: string;
  evidence_manifest_hash: string;
  final_answer: string | null;
  iterations: IterationSummary[];
  similarity_history: number[];
  explain: ExplainSummary;
  proof: Record<string, unknown>;
};

export type VerifyAsyncResponse = {
  job_id: string;
  status: string;
};

export type JobStatusResponse = {
  job_id: string;
  status: string;
  proof_id?: string;
  result?: VerificationResponse;
  error?: string;
};

export type PacksResponse = {
  packs: string[];
};

export type VerifyOptions = {
  max_iters?: number;
  threshold?: number;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: string;
  mode: "sync" | "async";
  jobId?: string;
  proof?: VerificationResponse;
};

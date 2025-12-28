export const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const generateRequestId = () => {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `req-${Math.random().toString(36).slice(2, 10)}`;
};

export const formatScore = (score: number) => score.toFixed(3);

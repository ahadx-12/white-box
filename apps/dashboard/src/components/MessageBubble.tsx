import type { ChatMessage } from "@/lib/types";

const roleStyles: Record<string, string> = {
  user: "bg-slate-800 text-slate-100 border-slate-700",
  assistant: "bg-indigo-900/40 text-slate-100 border-indigo-700/50",
};

export default function MessageBubble({ message }: { message: ChatMessage }) {
  return (
    <div
      className={`rounded-lg border px-4 py-3 shadow-sm ${
        roleStyles[message.role]
      }`}
      data-testid={`message-${message.role}`}
    >
      <div className="mb-1 flex items-center justify-between text-xs uppercase tracking-wide text-slate-300">
        <span>{message.role === "user" ? "User" : "Verifier"}</span>
        {message.status ? (
          <span className="rounded-full bg-slate-700 px-2 py-0.5 text-[10px] text-slate-200">
            {message.status}
          </span>
        ) : null}
      </div>
      <p className="whitespace-pre-wrap text-sm leading-relaxed">
        {message.content}
      </p>
    </div>
  );
}

// Wire contracts shared with the backend: the chat envelope and the SSE event
// union. These mirror the Pydantic models field-for-field; the SSE union is
// closed and the reducer/render switches over it must stay exhaustive.

export type Route = "coach" | "workout_generate" | "workout_log";

export type Claim =
  | "included"
  | "excluded"
  | "added"
  | "matched"
  | "substituted"
  | "note";

export type Relation =
  | "loads_joint"
  | "matches_target"
  | "bilateral_pair_of"
  | "equipment_match"
  | "name_match";

export interface Reason {
  claim: Claim;
  subject: string;
  relation: Relation;
  object: string | null;
  detail: string | null;
}

export interface ClarificationPrompt {
  question: string;
  options: string[];
}

export type BlockName = "warmup" | "main" | "cooldown";

export interface Prescription {
  exercise_id: string;
  name: string;
  sets: number;
  reps: number | null;
  duration_seconds: number | null;
  rest_seconds: number;
  weight: string | null;
}

export interface Block {
  name: BlockName;
  exercises: Prescription[];
}

export interface WorkoutPayload {
  blocks: Block[];
}

export interface LogEntry {
  session_id: string;
  exercise_id: string | null;
  raw_name: string;
  sets: number | null;
  reps: number | null;
  weight: number | null;
  unmatched: boolean;
  logged_at: string;
}

export interface LogPayload {
  entries: LogEntry[];
}

export type StructuredPayload = WorkoutPayload | LogPayload;

// The aggregated (non-streamed) response. Every field is present on every turn,
// null where the turn did not produce it.
export interface ChatRequest {
  message: string;
  session_id: string | null;
}

export interface ChatResponse {
  route: Route | null;
  reply_text: string;
  structured: StructuredPayload | null;
  explanation: Reason[];
  clarification: ClarificationPrompt | null;
}

// The streamed event union — six closed variants, tagged by `type`.
export type SSEEvent =
  | { type: "route"; route: Route }
  | { type: "token"; text: string }
  | { type: "structured"; payload: StructuredPayload }
  | { type: "clarification"; question: string; options: string[] }
  | { type: "done" }
  | { type: "error"; message: string };

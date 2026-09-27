export type TaskState = "done" | "working" | "pending" | "blocked";
export interface Task {
  title: string;
  owner: string;
  state: TaskState;
  updated: string;
}
export interface Work {
  id: string;
  name: string;
  topic: string;
  state: "working" | "done" | "unknown" | "stale" | "blocked" | "idle";
  updated: string;
  tasks: Task[] | null;
  review?: { label: string; url: string };
  visited?: boolean;
}
const preview =
  "/iframe.html?id=lab-stage-crew--just-faces&viewMode=story";
export const conversations: Work[] = [
  {
    id: "astra",
    name: "Astra",
    topic: "Mobile companion",
    state: "working",
    updated: "12s ago",
    tasks: [
      {
        title: "Map desktop controls",
        owner: "Astra",
        state: "done",
        updated: "18m ago",
      },
      {
        title: "Prepare shared fixtures",
        owner: "Astra",
        state: "done",
        updated: "14m ago",
      },
      {
        title: "Design agent cards",
        owner: "Mira · design",
        state: "done",
        updated: "7m ago",
      },
      {
        title: "Refine talk interactions",
        owner: "Mira · design",
        state: "working",
        updated: "12s ago",
      },
      {
        title: "Check keyboard access",
        owner: "Rook · quality",
        state: "working",
        updated: "1m ago",
      },
      {
        title: "Review both themes",
        owner: "Rook · quality",
        state: "pending",
        updated: "7m ago",
      },
      {
        title: "Prepare design handoff",
        owner: "Astra",
        state: "pending",
        updated: "7m ago",
      },
    ],
  },
  {
    id: "lux",
    name: "Lux",
    topic: "Native audio investigation",
    state: "working",
    updated: "2m ago",
    tasks: [
      {
        title: "Investigate device handover",
        owner: "Lux",
        state: "working",
        updated: "2m ago",
      },
    ],
  },
  {
    id: "mira",
    name: "Mira",
    topic: "Company Stage",
    state: "done",
    updated: "Just now",
    tasks: [
      {
        title: "Prepare company portraits",
        owner: "Mira",
        state: "done",
        updated: "Just now",
      },
    ],
    review: { label: "Review Stage designs", url: preview },
  },
  {
    id: "flux",
    name: "Flux",
    topic: "Conversation routing",
    state: "unknown",
    updated: "No update available",
    tasks: null,
  },
  {
    id: "rook",
    name: "Rook",
    topic: "Regression checks",
    state: "done",
    updated: "4m ago",
    tasks: [
      {
        title: "Verify audio controls",
        owner: "Rook",
        state: "done",
        updated: "4m ago",
      },
    ],
  },
  {
    id: "nova",
    name: "Nova",
    topic: "Avatar frames",
    state: "done",
    updated: "8m ago",
    visited: true,
    tasks: [
      {
        title: "Prepare portrait layouts",
        owner: "Nova",
        state: "done",
        updated: "8m ago",
      },
    ],
    review: { label: "Open portrait preview", url: preview },
  },
];
export const scenarios = {
  idle: {
    ...conversations[0]!,
    state: "idle" as const,
    updated: "Ready when you are",
    tasks: [],
  },
  stale: { ...conversations[0]!, state: "stale" as const, updated: "28m ago" },
  blocked: {
    ...conversations[0]!,
    state: "blocked" as const,
    updated: "3m ago",
    tasks: conversations[0]!.tasks!.map((t, i) =>
      i === 3
        ? {
            ...t,
            state: "blocked" as const,
            title: "Waiting for design source",
          }
        : t,
    ),
  },
  completed: {
    ...conversations[0]!,
    state: "done" as const,
    updated: "Just now",
    tasks: conversations[0]!.tasks!.map((t) => ({
      ...t,
      state: "done" as const,
    })),
    review: { label: "Review Stage designs", url: preview },
  },
};
export function counts(work: Work) {
  const tasks = work.tasks ?? [];
  return {
    done: tasks.filter((t) => t.state === "done").length,
    working: tasks.filter((t) => t.state === "working").length,
    pending: tasks.filter((t) => t.state === "pending").length,
    blocked: tasks.filter((t) => t.state === "blocked").length,
    total: tasks.length,
  };
}

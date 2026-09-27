export interface ReviewItem {
  id: string;
  title: string;
  state: "working" | "ready" | "blocked" | "done";
  owner: string;
  model: string | null;
  completed: number;
  total: number;
  review?: string;
}
export interface ReviewThread {
  id: string;
  title: string;
  voice: string;
  manager: string;
  items: ReviewItem[];
}
const stage =
  "/iframe.html?id=lab-company-stage--company-portrait&viewMode=story";
export const reviewThreads: ReviewThread[] = [
  {
    id: "release",
    title: "Bug fixing",
    voice: "ara",
    manager: "Main thread",
    items: [
      {
        id: "stage",
        title: "Company Stage: department leads and specialist portraits",
        state: "ready",
        owner: "Design agent",
        model: "GPT-6 Astra",
        completed: 4,
        total: 4,
        review: stage,
      },
      {
        id: "mobile",
        title: "Mobile talk screen and recipient selection",
        state: "working",
        owner: "Mobile agent",
        model: "GPT-6 Astra",
        completed: 3,
        total: 7,
      },
      {
        id: "usage",
        title: "Provider limits and account reset times",
        state: "ready",
        owner: "Dashboard agent",
        model: "GPT-6 Sol",
        completed: 5,
        total: 5,
        review: stage,
      },
      {
        id: "audio",
        title: "Investigate audio device handover after wake",
        state: "working",
        owner: "Audio agent",
        model: "GPT-6 Sol",
        completed: 1,
        total: 3,
      },
      {
        id: "windows",
        title: "Windows signing and native audio research",
        state: "blocked",
        owner: "Desktop agent",
        model: null,
        completed: 2,
        total: 6,
      },
    ],
  },
  {
    id: "routing",
    title: "Bucky",
    voice: "eve",
    manager: "Solo thread",
    items: [
      {
        id: "socket",
        title: "Restore the saved wake connection",
        state: "working",
        owner: "Main agent",
        model: "GPT-6 Astra",
        completed: 2,
        total: 4,
      },
    ],
  },
  {
    id: "website",
    title: "QA",
    voice: "leo",
    manager: "Solo thread",
    items: [
      {
        id: "download",
        title: "Preview the new download section",
        state: "ready",
        owner: "Main agent",
        model: "GPT-6 Astra",
        completed: 3,
        total: 3,
        review: stage,
      },
    ],
  },
];

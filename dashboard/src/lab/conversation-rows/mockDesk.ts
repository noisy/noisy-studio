/** A make-believe daemon for the Playground story: it applies the list's
 *  events to a copy of the fixtures, so every action visibly does something.
 *  Lab only; the real actions are daemon calls that do not exist yet. */
import { ref } from "vue";
import type { AgentState, DelegatedAgent, ManagerConversation, Project } from "./orgModel";

export function useMockDesk(initial: Project[], now: number, mic: string | null) {
  // A deep copy: Storybook's args may be reactive proxies, which structuredClone rejects.
  const projects = ref<Project[]>(JSON.parse(JSON.stringify(initial)));
  const micId = ref(mic);

  const managers = () => projects.value.flatMap((project) => project.managers);
  const editManager = (id: string, change: (manager: ManagerConversation) => void) => {
    const manager = managers().find((candidate) => candidate.id === id);
    if (manager) change(manager);
  };
  const setAgent = (id: string, from: AgentState[], to: AgentState) => {
    const agent = managers().flatMap((manager) => manager.agents).find((candidate: DelegatedAgent) => candidate.id === id);
    if (agent && from.includes(agent.state)) agent.state = to;
  };

  return {
    projects,
    micId,
    select: (id: string) => { micId.value = id; },
    settle: (id: string) => editManager(id, (manager) => { manager.settled = true; manager.endedAt = now; }),
    restore: (id: string) => editManager(id, (manager) => { manager.settled = false; manager.endedAt = null; if (manager.status === "ended") manager.status = "idle"; }),
    snooze: (id: string, until: number) => editManager(id, (manager) => { manager.snoozedUntil = until; }),
    pause: (id: string) => setAgent(id, ["working", "pending"], "paused"),
    resume: (id: string) => setAgent(id, ["paused"], "working"),
    stop: (id: string) => setAgent(id, ["working", "pending", "paused", "blocked", "review"], "done"),
    review: (id: string) => setAgent(id, ["review"], "done"),
    focus: (id: string, focused: boolean) => {
      const project = projects.value.find((candidate) => candidate.id === id);
      if (project) project.focused = focused;
    },
    pauseProject: (id: string) => {
      const project = projects.value.find((candidate) => candidate.id === id);
      for (const agent of project?.managers.flatMap((manager) => manager.agents) ?? []) {
        if (agent.state === "working" || agent.state === "pending") agent.state = "paused";
      }
    },
  };
}

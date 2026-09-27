export interface TaskReport {
  task_id: string;
  revision: number;
  title: string;
  state: "pending" | "working" | "blocked" | "done";
  completed: number | null;
  total: number | null;
  participant: string | null;
  role: string | null;
  model: string | null;
  review: { label: string; url: string } | null;
}
export interface ReportedTask {
  report: TaskReport;
  updated_at: number;
  review_state: "unopened" | "opened" | "approved";
  stale: boolean;
}
export interface TaskSnapshot {
  threads: Record<string, Record<string, ReportedTask>>;
  error: string | null;
}
export interface ReviewTarget {
  agent: string;
  task: ReportedTask;
}
export function reviewUrl(task: ReportedTask): string | null {
  try {
    const url = new URL(task.report.review?.url ?? "");
    return ["http:", "https:"].includes(url.protocol) &&
      !url.username &&
      !url.password
      ? url.href
      : null;
  } catch {
    return null;
  }
}
export function readyForReview(task: ReportedTask): boolean {
  return (
    task.report.state === "done" &&
    task.review_state !== "approved" &&
    reviewUrl(task) !== null
  );
}

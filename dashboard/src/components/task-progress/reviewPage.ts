import { reviewUrl, type ReportedTask } from './types';

// Set true to restore the review wrapper; explicit review.direct still wins.
export const REVIEW_IFRAMES_ENABLED = false;

export function canEmbedReview(task: ReportedTask): boolean {
  return REVIEW_IFRAMES_ENABLED && task.report.review?.direct !== true;
}

export function reviewTargetUrl(agent: string, task: ReportedTask): string {
  return canEmbedReview(task)
    ? reviewPageUrl(agent, task.report.task_id, task.report.revision)
    : reviewUrl(task) ?? '';
}

export function reviewPageUrl(agent: string, taskId: string, revision: number, base = window.location.href): string {
  const url = new URL(base);
  url.search = '';
  url.hash = '';
  url.searchParams.set('review_agent', agent);
  url.searchParams.set('review_task', taskId);
  url.searchParams.set('review_revision', String(revision));
  return url.href;
}
export function reviewPageTarget(search: string) {
  const params = new URLSearchParams(search);
  if (!params.has('review_task') && !params.has('review_agent')) return null;
  return { agent: params.get('review_agent') ?? '', taskId: params.get('review_task') ?? '', revision: Number(params.get('review_revision')) };
}

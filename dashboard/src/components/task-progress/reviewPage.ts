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

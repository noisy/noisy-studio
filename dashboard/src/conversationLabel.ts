/** Display titles never fall back to routing identities or filesystem paths. */
export function conversationLabel(title?: string | null, ...identities: string[]): string {
  const text = title?.trim() ?? "";
  const opaqueId = /^[0-9a-f]{8,}$/i.test(text) ||
    /^(?:[a-z][\w.-]*[:_-])*[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(text);
  const routingId = identities.some((identity) => identity && (text === identity ||
    (text.length >= 8 && (identity.startsWith(text) || identity.endsWith(text)))));
  return !text || /[/\\]/.test(text) || /\b[A-Za-z]:/.test(text) || opaqueId || routingId
    ? "New conversation"
    : text;
}

/** Keep display names path-free even when connected to an older daemon (#107).
 * Mirrors the backend's conservative policy: directory separators (including
 * those embedded in prose) and drive prefixes are not allowed in tab names.
 * Routing keys remain untouched; a basename is not a safe display fallback.
 */
export function conversationLabel(title?: string | null): string {
  const text = title?.trim() ?? "";
  return !text || /[/\\]/.test(text) || /\b[A-Za-z]:/.test(text)
    ? "New conversation"
    : text;
}

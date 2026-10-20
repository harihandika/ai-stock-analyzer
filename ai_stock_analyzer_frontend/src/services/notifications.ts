export const NOTIFICATIONS_UPDATED = "stock-notifications-updated";

export function publishUnread(userId: string | undefined, unread: number) {
  if (userId && Number.isSafeInteger(unread) && unread >= 0)
    window.dispatchEvent(
      new CustomEvent(NOTIFICATIONS_UPDATED, { detail: { userId, unread } }),
    );
}

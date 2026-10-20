"use client";

import { useCallback, useEffect, useRef } from "react";

export const confirmDiscard = () =>
  window.confirm(
    "Catatan belum disimpan. Pilih Batal untuk tetap mengedit, atau OK untuk membuang draft dan melanjutkan.",
  );

export function useUnsavedChanges(dirty: boolean) {
  const allowed = useRef(false);
  const allowLeave = useCallback(() => {
    if (!dirty || confirmDiscard()) {
      allowed.current = true;
      return true;
    }
    return false;
  }, [dirty]);
  useEffect(() => {
    allowed.current = false;
    if (!dirty) return;
    const unload = (event: BeforeUnloadEvent) => {
      if (allowed.current) return;
      event.preventDefault();
      event.returnValue = "";
    };
    // Navigation API also covers Back/Forward and programmatic navigation.
    // Intercept links before Next starts rendering the destination; history
    // notifications alone may arrive after the current page has unmounted.
    type NavigateEvent = Event & {
      destination: { url: string };
      canIntercept: boolean;
    };
    const navigation = (window as unknown as { navigation?: EventTarget })
      .navigation;
    const navigate = (event: Event) => {
      const e = event as NavigateEvent;
      const target = new URL(e.destination.url);
      if (
        !allowed.current &&
        target.pathname !== location.pathname &&
        e.cancelable &&
        !confirmDiscard()
      )
        e.preventDefault();
    };
    const click = (event: MouseEvent) => {
      if (
        allowed.current ||
        event.defaultPrevented ||
        event.button ||
        event.ctrlKey ||
        event.metaKey ||
        event.shiftKey ||
        event.altKey
      )
        return;
      const link = (event.target as Element).closest<HTMLAnchorElement>(
        "a[href]",
      );
      if (!link || link.target === "_blank" || link.hasAttribute("download"))
        return;
      if (new URL(link.href).pathname !== location.pathname) {
        if (!confirmDiscard()) {
          event.preventDefault();
          event.stopPropagation();
        } else allowed.current = true;
      }
    };
    window.addEventListener("beforeunload", unload);
    navigation?.addEventListener("navigate", navigate);
    document.addEventListener("click", click, true);
    return () => {
      window.removeEventListener("beforeunload", unload);
      navigation?.removeEventListener("navigate", navigate);
      document.removeEventListener("click", click, true);
    };
  }, [dirty]);
  return allowLeave;
}

// Popup menus in two halves: useMenu owns the state (open, close, dismissal
// by outside click or Escape) and MenuPanel owns the box (measured placement,
// horizontal clamp, the data attributes the tip layer reads). useContextMenu
// and ContextMenu are the right-click pair, opening at the pointer in a body
// portal. Triggers stay at the call site, where menus differ.
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

/* Dismiss on click outside or Escape. Attach the returned ref to the
   popover's wrapper. */
export function useDismissable(open, onClose) {
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    function onDocumentPointerDown(event) {
      if (ref.current && !ref.current.contains(event.target)) onClose();
    }
    function onKeyDown(event) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("pointerdown", onDocumentPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onDocumentPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, onClose]);
  return ref;
}

/* The state half of a popup menu. `open` may hold a key instead of true for a
   host with several panels; any truthy value arms dismissal. Before the first
   open, the host's data-drop is guessed from where it sits so its tooltip
   already parks on the side the menu will not take. */
export function useMenu(onClose) {
  const [open, setOpen] = useState(false);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const close = useCallback(() => {
    setOpen(false);
    onCloseRef.current?.();
  }, []);
  const ref = useDismissable(!!open, close);
  useEffect(() => {
    const host = ref.current;
    if (host && !host.dataset.drop) {
      const rect = host.getBoundingClientRect();
      host.dataset.drop = rect.bottom > window.innerHeight * 0.75 ? "up" : "down";
    }
  }, [ref]);
  return { open, setOpen, close, ref };
}


/* The box half. Drops down unless the viewport below is tight, and clamps
   horizontally on screen. While open the host carries data-menu-open, which
   mutes its tooltip. Styling is the .menu-panel block in the stylesheet. */
export function MenuPanel({ className, children, ...rest }) {
  const ref = useRef(null);
  useLayoutEffect(() => {
    const element = ref.current;
    const host = element?.parentElement;
    if (!host) return undefined;
    const box = element.getBoundingClientRect();
    const anchor = host.getBoundingClientRect();
    const below = window.innerHeight - anchor.bottom;
    element.dataset.drop = box.height + 8 > below && anchor.top > below ? "up" : "down";
    host.dataset.drop = element.dataset.drop;
    const placed = element.getBoundingClientRect();
    if (placed.right > window.innerWidth - 6) element.dataset.align = "right";
    else if (placed.left < 6) element.dataset.align = "left";
    host.dataset.menuOpen = "";
    return () => {
      delete host.dataset.menuOpen;
    };
  }, []);
  return (
    <span ref={ref} className={"menu-panel" + (className ? ` ${className}` : "")} {...rest}>
      {children}
    </span>
  );
}

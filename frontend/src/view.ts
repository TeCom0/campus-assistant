import { useEffect, useState } from "react";

// The app's two views, switched by the URL's hash: "#about" is the About
// page, anything else the chat. A hash needs no server routing (the server
// always sends the same index.html), the back button works, and the About
// page has a link of its own to share.
export type View = "chat" | "about";

export function viewFromHash(hash: string): View {
  return hash === "#about" ? "about" : "chat";
}

export function useView(): View {
  const [view, setView] = useState<View>(() => viewFromHash(window.location.hash));
  useEffect(() => {
    const onChange = () => setView(viewFromHash(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return view;
}

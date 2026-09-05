"use client";

import { useEffect, useState } from "react";

export function MarketHeader({ connected }: { connected: boolean }) {
  const [time, setTime] = useState("");

  useEffect(() => {
    const formatter = new Intl.DateTimeFormat("fr-FR", {
      timeZone: "Europe/Paris",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
    const update = () => setTime(formatter.format(new Date()));
    update();
    const timer = window.setInterval(update, 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <header className="terminal-header">
      <div className="brand-lockup">
        <span className="brand">MARKET TERMINAL</span>
        <span className={`connection ${connected ? "is-live" : ""}`}>
          <i aria-hidden="true" />
          {connected ? "LIVE" : "DISCONNECTED"}
        </span>
      </div>
      <div className="provider-lockup">
        <span>London Strategic Edge</span>
        <time>{time || "--:--:--"}</time>
      </div>
    </header>
  );
}

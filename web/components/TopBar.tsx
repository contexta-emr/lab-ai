"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { WorkspaceInfo } from "@/lib/api";
import { setWorkspace } from "@/lib/workspace";
import type { Workspace } from "@/lib/workspace";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/queue", label: "To check", badge: true },
  { href: "/patients", label: "Patients" },
];

/** Switching reloads the app: every screen re-reads in the new workspace, and
 *  nothing from the old one can linger in a component's state. */
function switchTo(workspace: Workspace) {
  setWorkspace(workspace);
  window.location.href = "/";
}

export function TopBar() {
  const pathname = usePathname();
  const [pending, setPending] = useState<number | null>(null);
  const [ws, setWs] = useState<WorkspaceInfo | null>(null);

  useEffect(() => {
    api.workspace().then(setWs).catch(() => setWs(null));
  }, []);

  // The work waiting for a person, kept fresh while the page is open.
  useEffect(() => {
    let cancelled = false;
    const load = () =>
      api
        .queue()
        .then((q) => {
          if (!cancelled) {
            setPending((q.counts.needs_review ?? 0) + (q.counts.awaiting_confirm ?? 0));
          }
        })
        .catch(() => setPending(null));
    load();
    const timer = setInterval(load, 30_000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [pathname]);

  return (
    <>
      <header className="topbar">
        {/* The real mark and the company name first, so this reads as part of
            the EMR rather than a tool that happens to sit beside it. */}
        <Link href="/" className="brand" aria-label="Contexta Health - Lab reports">
          <Image src="/contexta-icon.png" alt="" width={28} height={28} priority />
          <span className="brand-text">
            Contexta Health
            <small>Lab reports</small>
          </span>
        </Link>

        <nav className="topnav" aria-label="Main">
          {LINKS.map((link) => {
            const active =
              link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            return (
              <Link key={link.href} href={link.href} className={active ? "active" : ""}>
                {link.label}
                {link.badge && pending ? <span className="count">{pending}</span> : null}
              </Link>
            );
          })}
        </nav>

        {ws?.sample_available && (
          <div className="ws-switch" role="group" aria-label="Workspace">
            <button
              type="button"
              aria-pressed={ws.workspace === "team"}
              onClick={() => ws.workspace !== "team" && switchTo("team")}
            >
              Team
            </button>
            <button
              type="button"
              aria-pressed={ws.workspace === "sample"}
              onClick={() => ws.workspace !== "sample" && switchTo("sample")}
            >
              Sample data
            </button>
          </div>
        )}
      </header>

      {ws?.read_only && (
        <div className="sample-banner" role="status">
          You&rsquo;re looking at sample data: 20 made-up patients and five years of their
          reports. Uploading is off here.
          <button type="button" onClick={() => switchTo("team")}>
            Back to your team&rsquo;s reports
          </button>
        </div>
      )}
    </>
  );
}

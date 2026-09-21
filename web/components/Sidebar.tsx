"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api, getToken } from "@/lib/api";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/upload", label: "Upload" },
  { href: "/review", label: "Review queue", badge: true },
  { href: "/patients", label: "Patients" },
];

export function Sidebar() {
  const pathname = usePathname();
  const [pending, setPending] = useState<number | null>(null);

  // The queue count is the one number a reviewer wants visible at all times:
  // it is the work waiting for a human.
  useEffect(() => {
    if (!getToken()) return;
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
    <aside className="sidebar">
      <div className="brand">
        Contexta Lab IDP
        <small>Attachment Intelligence</small>
      </div>

      <nav className="nav">
        {LINKS.map((link) => {
          const active =
            link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
          return (
            <Link key={link.href} href={link.href} className={active ? "active" : ""}>
              <span>{link.label}</span>
              {link.badge && pending ? <span className="count">{pending}</span> : null}
            </Link>
          );
        })}
      </nav>

      <div style={{ position: "absolute", bottom: 18, left: 14, right: 14 }}>
        <p className="faint" style={{ margin: 0, lineHeight: 1.45 }}>
          Results become clinical fact only after a human verifies them.
        </p>
      </div>
    </aside>
  );
}

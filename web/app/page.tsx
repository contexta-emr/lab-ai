"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { DocumentSummary, WorkspaceInfo } from "@/lib/api";
import { DropZone } from "@/components/DropZone";
import { LiveCard, ReportCard } from "@/components/ReportCard";
import type { Live } from "@/components/ReportCard";

/** The file types the server accepts (ALLOWED in api/app/routers/documents.py). */
const ACCEPTED = [".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif"];
/** Reads at once. OpenParser rate-limits; four keeps a stack moving without tripping it. */
const READERS = 4;
const READING = new Set(["received", "parsing"]);
const NEEDS_CHECK = new Set(["parsed", "needs_review"]);

type Tab = "all" | "check" | "checked";
const TAB_LABEL: Record<Tab, string> = { all: "All", check: "Needs checking", checked: "Checked" };

function problemWith(file: File, limitMb: number): string | null {
  const dot = file.name.lastIndexOf(".");
  const ext = dot >= 0 ? file.name.slice(dot).toLowerCase() : "";
  if (!ACCEPTED.includes(ext)) return "This isn't a PDF or a photo, so it can't be read.";
  if (file.size === 0) return "This file is empty.";
  if (file.size > limitMb * 1024 * 1024) {
    return `This file is ${(file.size / 1048576).toFixed(1)} MB; the limit is ${limitMb} MB. A smaller photo works just as well.`;
  }
  return null;
}

/**
 * Home: drop reports, watch them read, find them again.
 *
 * Every step a card shows comes from the server as it happens - POST
 * /documents/read-next streams them - so nothing here is timed to look busy.
 */
export default function Home() {
  const [ws, setWs] = useState<WorkspaceInfo | null>(null);
  const [docs, setDocs] = useState<DocumentSummary[] | null>(null);
  const [live, setLive] = useState<Live[]>([]);
  const [tab, setTab] = useState<Tab>("all");
  const [notice, setNotice] = useState<string | null>(null);
  const [slow, setSlow] = useState(false);
  const readers = useRef(0);
  // Which live card a document id belongs to. A ref: reader callbacks outlive renders.
  const cardFor = useRef(new Map<string, string>());

  const refresh = useCallback(async () => {
    try {
      setDocs(await api.documents({ limit: 100 }));
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Couldn't load your reports.");
    }
  }, []);

  const patch = useCallback(
    (key: string, change: Partial<Live>) =>
      setLive((cards) => cards.map((c) => (c.key === key ? { ...c, ...change } : c))),
    [],
  );

  /** One reader: read waiting reports until none are left, each step to its card. */
  const runReader = useCallback(async () => {
    readers.current += 1;
    try {
      for (;;) {
        let current: string | null = null;
        const last = await api.readNext((s) => {
          if (s.step === "reading") current = s.document_id;
          const key = current ? cardFor.current.get(current) : undefined;
          if (!key) return; // a report from an earlier visit: the list shows it
          if (s.step === "reading") patch(key, { phase: "reading", retrying: false });
          else if (s.step === "found") patch(key, { tests: s.tests });
          else if (s.step === "second_look") patch(key, { secondLook: true });
          else if (s.step === "done") patch(key, { phase: "done", result: s });
          else if (s.step === "failed") {
            patch(
              key,
              s.state === "failed"
                ? { phase: "failed" }
                : { phase: "waiting", retrying: true, tests: undefined },
            );
          }
        });
        void refresh();
        if (!last || last.step === "idle" || last.step === "error") break;
      }
    } catch (e) {
      // The reports are saved either way and wait in line. Say so; don't pretend.
      setNotice(
        e instanceof ApiError && e.status === 503
          ? "Your reports are saved. Reading isn't switched on here yet, so they'll wait."
          : "Lost the connection while reading. Your reports are saved and will finish.",
      );
    } finally {
      readers.current -= 1;
    }
  }, [patch, refresh]);

  const startReader = useCallback(() => {
    if (readers.current < READERS) void runReader();
  }, [runReader]);

  useEffect(() => {
    api.workspace().then(setWs).catch(() => setWs(null));
    void refresh();
    // Vercel and Neon both sleep when nobody has visited for a while.
    const timer = setTimeout(() => setSlow(true), 2000);
    return () => clearTimeout(timer);
  }, [refresh]);

  // A report left waiting - a tab closed mid-read - is picked up by whoever opens Home next.
  useEffect(() => {
    if (
      ws &&
      !ws.read_only &&
      readers.current === 0 &&
      docs?.some((d) => d.status === "received")
    ) {
      startReader();
    }
  }, [ws, docs, startReader]);

  // While anything is in flight, keep the list fresh: a report another tab or
  // the worker is reading still needs to land here.
  const busy =
    live.some((c) => ["uploading", "waiting", "reading"].includes(c.phase)) ||
    (docs ?? []).some((d) => READING.has(d.status));
  useEffect(() => {
    if (!busy) return;
    const timer = setInterval(() => void refresh(), 4000);
    return () => clearInterval(timer);
  }, [busy, refresh]);

  // A live card whose document was read elsewhere has nothing more to show: the list has it.
  useEffect(() => {
    if (!docs) return;
    const present = new Set(docs.map((d) => d.id));
    setLive((cards) =>
      cards.filter(
        (c) => !(c.docId && !c.result && !present.has(c.docId) && c.phase !== "failed"),
      ),
    );
  }, [docs]);

  const add = useCallback(
    (files: File[]) => {
      const limit = ws?.max_upload_mb ?? 4;
      const fresh: Live[] = files.map((file, i) => {
        const problem = problemWith(file, limit);
        return {
          key: `${Date.now()}-${i}-${file.name}`,
          name: file.name,
          phase: problem ? "rejected" : "uploading",
          progress: 0,
          message: problem ?? undefined,
        };
      });
      setLive((cards) => [...fresh, ...cards]);
      fresh.forEach((card, i) => {
        if (card.phase !== "uploading") return;
        api
          .uploadWithProgress(files[i], (p) => patch(card.key, { progress: p }))
          .then((doc) => {
            cardFor.current.set(doc.id, card.key);
            if (READING.has(doc.status)) {
              patch(card.key, { phase: "waiting", docId: doc.id, progress: 1 });
              startReader(); // each upload starts reading as soon as it lands
              return;
            }
            // The same file again: the server hands back the first copy.
            patch(card.key, {
              phase: "done",
              docId: doc.id,
              progress: 1,
              message: "Already uploaded. This is the earlier copy.",
              result: {
                step: "done",
                document_id: doc.id,
                replaced: doc.id,
                status: doc.status,
                patient_id: doc.patient_id,
                patient_name: doc.patient_name,
                tests: doc.result_count,
              },
            });
          })
          .catch((e: unknown) =>
            patch(card.key, {
              phase: "failed",
              message: e instanceof Error ? e.message : "Upload failed.",
            }),
          );
      });
    },
    [ws, patch, startReader],
  );

  const counts = useMemo(
    () => ({
      all: docs?.length ?? 0,
      check: docs?.filter((d) => NEEDS_CHECK.has(d.status)).length ?? 0,
      checked: docs?.filter((d) => d.status === "verified").length ?? 0,
    }),
    [docs],
  );

  // The tab's reports, less the ones already on a "Just now" card above, so
  // nothing shows twice. `aboveOnly` says the tab is empty only for that
  // reason - its count still includes them, and "No reports yet" under
  // "All 1" would contradict it.
  const { shown, aboveOnly } = useMemo(() => {
    const onLiveCards = new Set(
      live
        .flatMap((c) => [c.docId, c.result?.document_id])
        .filter((id): id is string => Boolean(id)),
    );
    const inTab = (docs ?? []).filter((d) =>
      tab === "all" ? true : tab === "check" ? NEEDS_CHECK.has(d.status) : d.status === "verified",
    );
    const rest = inTab.filter((d) => !onLiveCards.has(d.id));
    return { shown: rest, aboveOnly: rest.length === 0 && inTab.length > 0 };
  }, [docs, live, tab]);

  const readOnly = ws?.read_only ?? false;

  return (
    <div className="home">
      <section className="hero">
        <div className="hero-text">
          <p className="eyebrow">{readOnly ? "Sample data" : (ws?.practice_name ?? " ")}</p>
          <h1>{readOnly ? "Five years of lab reports, read" : "Lab reports, read for you"}</h1>
          <p>
            {readOnly
              ? "Twenty made-up patients and their reports, to show what reading looks like. Open any report, or a patient's trends."
              : "Drop a PDF or a photo of a report. Every test is read, matched to the patient by the UHID on the page, and lined up with their history. You just check it."}
          </p>
        </div>
        {!readOnly && (
          <DropZone accept={ACCEPTED.join(",")} maxMb={ws?.max_upload_mb ?? 4} onFiles={add} />
        )}
      </section>

      {notice && (
        <div className="notice" role="status">
          {notice}
        </div>
      )}

      {live.length > 0 && (
        <section aria-live="polite">
          <div className="list-head">
            <h2>Just now</h2>
          </div>
          <div className="report-grid">
            {live.map((c) => (
              <LiveCard key={c.key} card={c} />
            ))}
          </div>
        </section>
      )}

      <section>
        <div className="list-head">
          <h2>{readOnly ? "Reports" : "Your reports"}</h2>
          <div className="tabs" role="tablist" aria-label="Show">
            {(Object.keys(TAB_LABEL) as Tab[]).map((t) => (
              <button
                key={t}
                type="button"
                role="tab"
                aria-selected={tab === t}
                className={tab === t ? "on" : ""}
                onClick={() => setTab(t)}
              >
                {TAB_LABEL[t]}
                <span className="n">{counts[t]}</span>
              </button>
            ))}
          </div>
        </div>

        {docs === null ? (
          <>
            {slow && (
              <p className="waking">
                Waking up. The first visit after a quiet spell takes a few seconds.
              </p>
            )}
            <div className="report-grid" aria-busy>
              {Array.from({ length: 6 }, (_, i) => (
                <div key={i} className="skeleton-card" />
              ))}
            </div>
          </>
        ) : aboveOnly ? (
          <p className="waking">Everything here is in &ldquo;Just now&rdquo;, above.</p>
        ) : shown.length === 0 ? (
          <div className="empty-state">
            <svg viewBox="0 0 64 64" fill="none" aria-hidden>
              <rect x="14" y="8" width="36" height="48" rx="6" stroke="currentColor" strokeWidth="3" />
              <path
                d="M23 22h18M23 31h18M23 40h10"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
              />
            </svg>
            <p>
              {tab === "all"
                ? readOnly
                  ? "No sample reports here."
                  : "No reports yet. Drop your first one above; it takes about a minute to read."
                : tab === "check"
                  ? "Nothing waiting for you. Everything read has been checked."
                  : "Nothing checked yet."}
            </p>
          </div>
        ) : (
          <div className="report-grid">
            {shown.map((d) => (
              <ReportCard key={d.id} doc={d} onDeleted={readOnly ? undefined : () => void refresh()} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

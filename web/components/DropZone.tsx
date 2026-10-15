"use client";

import { useRef, useState } from "react";

/** The one big thing on Home. Drag a stack onto it, or choose files - on a
 *  phone, choosing offers the camera, because images are accepted. */
export function DropZone({
  accept,
  maxMb,
  onFiles,
}: {
  accept: string;
  maxMb: number;
  onFiles: (files: File[]) => void;
}) {
  const [over, setOver] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const take = (list: FileList | null) => {
    if (list && list.length) onFiles(Array.from(list));
  };

  return (
    <div
      className={`drop${over ? " over" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        take(e.dataTransfer.files);
      }}
    >
      <svg className="drop-icon" viewBox="0 0 48 48" fill="none" aria-hidden>
        <rect x="9" y="5" width="24" height="32" rx="4" stroke="currentColor" strokeWidth="2.4" />
        <path
          d="M15 14h12M15 20h12M15 26h7"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
        />
        <circle cx="35" cy="35" r="9" fill="var(--coral)" />
        <path
          d="M35 39.5v-9m-4 4 4-4 4 4"
          stroke="#fff"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <p className="drop-title">Drop lab reports here</p>
      <p className="drop-sub">PDF or a photo, up to {maxMb} MB each. As many as you like.</p>
      <button type="button" className="cta" onClick={() => input.current?.click()}>
        Choose files
      </button>
      <input
        ref={input}
        type="file"
        multiple
        hidden
        accept={accept}
        onChange={(e) => {
          take(e.target.files);
          e.target.value = ""; // choosing the same file again still fires
        }}
      />
    </div>
  );
}

/**
 * Which workspace this browser is looking at: the team's own reports, or the
 * read-only sample. Only a NAME - the server decides what it means, and asking
 * for anything but "sample" gets the team.
 */
export type Workspace = "team" | "sample";

const KEY = "contexta.lab.workspace";

export function getWorkspace(): Workspace {
  if (typeof window === "undefined") return "team";
  try {
    return window.localStorage.getItem(KEY) === "sample" ? "sample" : "team";
  } catch {
    return "team"; // storage blocked: a private window stays on the team
  }
}

export function setWorkspace(workspace: Workspace): void {
  try {
    window.localStorage.setItem(KEY, workspace);
  } catch {
    /* storage blocked: the switch lasts this page only */
  }
}

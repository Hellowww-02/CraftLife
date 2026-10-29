/**
 * M02 — shellState.ts.
 *
 * This module owns the Learning page layout AND the migration of three
 * historical preference formats stored in users' localStorage. A migration
 * mistake is invisible in review and shows up as a user's panels suddenly
 * collapsing, or their saved widths being silently discarded.
 *
 * migrateShellState() is the interesting part: v2 (pixels), v1 (named presets
 * from A07/A15) and a legacy {src, stu} shape must all land on the same v2
 * structure, and corrupt input must degrade to safe defaults rather than
 * throwing during render.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  LS_KEY,
  LS_LEGACY_KEY,
  SRC_MIN,
  SRC_MAX,
  SRC_DEFAULT,
  STU_MIN,
  STU_MAX,
  STU_DEFAULT,
  CHAT_MIN,
  defaultShellState,
  clampPanel,
  clampSrcPx,
  clampStuPx,
  migrateShellState,
  loadShellState,
  saveShellState,
} from "../shellState";

/** Minimal in-memory localStorage — enough for these two functions. */
function stubLocalStorage() {
  const store = new Map<string, string>();
  return {
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    setItem: (k: string, v: string) => void store.set(k, String(v)),
    removeItem: (k: string) => void store.delete(k),
    clear: () => store.clear(),
    _store: store,
  };
}

beforeEach(() => {
  (globalThis as unknown as { localStorage: unknown }).localStorage = stubLocalStorage();
});

describe("defaultShellState", () => {
  it("is the documented v2 shape with both panels open", () => {
    expect(defaultShellState()).toEqual({
      v: 2,
      srcPx: SRC_DEFAULT,
      stuPx: STU_DEFAULT,
      srcOpen: true,
      stuOpen: true,
      railExpanded: false,
    });
  });

  it("returns a fresh object each call (callers must not share state)", () => {
    const a = defaultShellState();
    a.srcPx = 999;
    expect(defaultShellState().srcPx).toBe(SRC_DEFAULT);
  });
});

describe("clampPanel", () => {
  it("clamps to the given bounds", () => {
    expect(clampPanel(1000, 220, 480)).toBe(480);
    expect(clampPanel(10, 220, 480)).toBe(220);
    expect(clampPanel(300, 220, 480)).toBe(300);
  });

  it("rounds fractional pixel values", () => {
    expect(clampPanel(300.4, 220, 480)).toBe(300);
    expect(clampPanel(300.6, 220, 480)).toBe(301);
  });

  it("leaves the upper bound alone when no shell width is known", () => {
    expect(clampPanel(480, 220, 480, 0)).toBe(480);
  });

  it("shrinks the upper bound so the chat column keeps its minimum", () => {
    // total 1200, opposite panel 400 -> chat gets 1200-400-CHAT_MIN-32 = 468.
    expect(clampPanel(480, 220, 480, 1200, 400)).toBe(468);
  });

  it("never lets the reserved chat minimum squeeze the panel below its own min", () => {
    // A narrow window must still leave a usable panel, not a zero-width one.
    expect(clampPanel(480, 220, 480, 700, 300)).toBe(220);
  });

  it("exposes the documented per-panel bounds", () => {
    expect(clampSrcPx(SRC_MAX + 500)).toBe(SRC_MAX);
    expect(clampSrcPx(0)).toBe(SRC_MIN);
    expect(clampStuPx(STU_MAX + 500)).toBe(STU_MAX);
    expect(clampStuPx(0)).toBe(STU_MIN);
    expect(CHAT_MIN).toBeGreaterThan(0);
  });
});

describe("migrateShellState — v2", () => {
  it("reads a valid v2 payload", () => {
    const raw = JSON.stringify({ v: 2, srcPx: 260, stuPx: 500, srcOpen: true, stuOpen: false, railExpanded: true });
    expect(migrateShellState(raw, null)).toEqual({
      v: 2, srcPx: 260, stuPx: 500, srcOpen: true, stuOpen: false, railExpanded: true,
    });
  });

  it("clamps out-of-range widths instead of trusting stored values", () => {
    const raw = JSON.stringify({ v: 2, srcPx: 5000, stuPx: -20 });
    const out = migrateShellState(raw, null);
    expect(out.srcPx).toBe(SRC_MAX);
    expect(out.stuPx).toBe(STU_MIN);
  });

  it("substitutes defaults for missing or non-numeric widths", () => {
    const out = migrateShellState(JSON.stringify({ v: 2, srcPx: "abc" }), null);
    expect(out.srcPx).toBe(SRC_DEFAULT);
    expect(out.stuPx).toBe(STU_DEFAULT);
  });

  it("treats only an explicit false as closed", () => {
    expect(migrateShellState(JSON.stringify({ v: 2, srcOpen: false }), null).srcOpen).toBe(false);
    expect(migrateShellState(JSON.stringify({ v: 2 }), null).srcOpen).toBe(true);
    expect(migrateShellState(JSON.stringify({ v: 2, srcOpen: null }), null).srcOpen).toBe(true);
  });

  it("treats only an explicit true as an expanded rail", () => {
    expect(migrateShellState(JSON.stringify({ v: 2, railExpanded: true }), null).railExpanded).toBe(true);
    expect(migrateShellState(JSON.stringify({ v: 2, railExpanded: "yes" }), null).railExpanded).toBe(false);
  });
});

describe("migrateShellState — v1 presets (A07/A15)", () => {
  it.each([
    ["narrow", 320],
    ["medium", 420],
    ["wide", 560],
  ])("maps the %s preset to its original pixel width", (preset, px) => {
    const out = migrateShellState(JSON.stringify({ studioWidth: preset }), null);
    expect(out.stuPx).toBe(px);
    // The Sources panel did not exist in v1, so it takes the default.
    expect(out.srcPx).toBe(SRC_DEFAULT);
  });

  it("falls back to the default for an unrecognised preset", () => {
    const out = migrateShellState(JSON.stringify({ studioWidth: "ultrawide" }), null);
    expect(out.stuPx).toBe(STU_DEFAULT);
  });

  it("carries over open/collapsed flags from v1", () => {
    const out = migrateShellState(
      JSON.stringify({ studioWidth: "wide", studioOpen: false, railExpanded: true }), null,
    );
    expect(out.stuOpen).toBe(false);
    expect(out.railExpanded).toBe(true);
  });

  it("handles a v1 payload with flags but no width", () => {
    const out = migrateShellState(JSON.stringify({ studioOpen: false }), null);
    expect(out.stuPx).toBe(STU_DEFAULT);
    expect(out.stuOpen).toBe(false);
  });
});

describe("migrateShellState — legacy pixel format", () => {
  it("reads the old {src, stu} key when no v2/v1 value exists", () => {
    const out = migrateShellState(null, JSON.stringify({ src: 250, stu: 480 }));
    expect(out.srcPx).toBe(250);
    expect(out.stuPx).toBe(480);
  });

  it("clamps legacy values that fall outside today's bounds", () => {
    const out = migrateShellState(null, JSON.stringify({ src: 9999, stu: 1 }));
    expect(out.srcPx).toBe(SRC_MAX);
    expect(out.stuPx).toBe(STU_MIN);
  });

  it("ignores a legacy entry that is not a finite number", () => {
    const out = migrateShellState(null, JSON.stringify({ src: "wide", stu: 500 }));
    expect(out.srcPx).toBe(SRC_DEFAULT);
    expect(out.stuPx).toBe(500);
  });

  it("prefers the v2 key over the legacy key", () => {
    const out = migrateShellState(
      JSON.stringify({ v: 2, srcPx: 240, stuPx: 300 }),
      JSON.stringify({ src: 400, stu: 600 }),
    );
    expect(out.srcPx).toBe(240);
    expect(out.stuPx).toBe(300);
  });
});

describe("migrateShellState — corrupt input", () => {
  it("degrades to safe defaults rather than throwing", () => {
    // A throw here would break the Learning page during render.
    expect(migrateShellState("{not json", null)).toEqual(defaultShellState());
    expect(migrateShellState("", null)).toEqual(defaultShellState());
    expect(migrateShellState(null, null)).toEqual(defaultShellState());
    expect(migrateShellState("null", "also{broken")).toEqual(defaultShellState());
  });

  it("survives a JSON array or scalar where an object was expected", () => {
    expect(migrateShellState("[1,2,3]", null)).toEqual(defaultShellState());
    expect(migrateShellState("42", null)).toEqual(defaultShellState());
  });
});

describe("loadShellState / saveShellState", () => {
  it("round-trips through localStorage", () => {
    const state = { ...defaultShellState(), srcPx: 275, stuOpen: false };
    saveShellState(state);
    expect(loadShellState()).toEqual(state);
  });

  it("returns defaults when nothing has been saved", () => {
    expect(loadShellState()).toEqual(defaultShellState());
  });

  it("writes under the versioned key, not the legacy one", () => {
    saveShellState(defaultShellState());
    const ls = (globalThis as unknown as { localStorage: { _store: Map<string, string> } }).localStorage;
    expect(ls._store.has(LS_KEY)).toBe(true);
    expect(ls._store.has(LS_LEGACY_KEY)).toBe(false);
  });

  it("survives a localStorage that throws (private mode / quota)", () => {
    const throwing = {
      getItem: () => { throw new Error("denied"); },
      setItem: () => { throw new Error("quota"); },
    };
    (globalThis as unknown as { localStorage: unknown }).localStorage = throwing;
    expect(loadShellState()).toEqual(defaultShellState());
    expect(() => saveShellState(defaultShellState())).not.toThrow();
  });

  it("recovers by migrating a legacy-only installation", () => {
    const ls = (globalThis as unknown as { localStorage: { _store: Map<string, string> } }).localStorage;
    ls._store.set(LS_LEGACY_KEY, JSON.stringify({ src: 240, stu: 460 }));
    const out = loadShellState();
    expect(out.srcPx).toBe(240);
    expect(out.stuPx).toBe(460);
    expect(out.v).toBe(2);
  });
});

/**
 * M02 — cycleUtils.ts.
 *
 * Pure calendar arithmetic behind the cycle tracker: cycle length, averages,
 * prediction confidence, the fertile window and form validation. It is
 * computed in UTC on purpose so results do not shift with the user's timezone,
 * and several of these numbers are shown to the user as health information —
 * an off-by-one here is not cosmetic.
 */
import { describe, it, expect } from "vitest";
import {
  toIso,
  dayDiff,
  addDays,
  cycleLength,
  cycleStats,
  predictionConfidence,
  fertileWindow,
  effectiveCycleLength,
  lengthLabel,
  cycleRows,
  validateCycleForm,
  type CycleRow,
} from "../cycleUtils";

const cycle = (startDate: string, endDate?: string, extra: Partial<CycleRow> = {}): CycleRow => ({
  startDate,
  ...(endDate ? { endDate } : {}),
  ...extra,
});

/** Newest first, as the server returns them. */
const history = (...rows: CycleRow[]) => rows;

describe("toIso", () => {
  it("accepts a plain date and truncates a timestamp", () => {
    expect(toIso("2026-10-06")).toBe("2026-10-06");
    expect(toIso("2026-10-06T14:32:00Z")).toBe("2026-10-06");
    expect(toIso("2026-10-06 14:32")).toBe("2026-10-06");
  });

  it("rejects anything that is not YYYY-MM-DD", () => {
    expect(toIso("")).toBe("");
    expect(toIso(null)).toBe("");
    expect(toIso(undefined)).toBe("");
    expect(toIso("06/10/2026")).toBe("");
    expect(toIso("not a date")).toBe("");
    expect(toIso("2026-1-6")).toBe("");
  });
});

describe("dayDiff", () => {
  it("counts whole days between two dates", () => {
    expect(dayDiff("2026-10-01", "2026-10-06")).toBe(5);
    expect(dayDiff("2026-10-06", "2026-10-01")).toBe(-5);
    expect(dayDiff("2026-10-06", "2026-10-06")).toBe(0);
  });

  it("crosses month and year boundaries", () => {
    expect(dayDiff("2026-01-30", "2026-02-02")).toBe(3);
    expect(dayDiff("2025-12-30", "2026-01-02")).toBe(3);
  });

  it("accounts for leap years", () => {
    expect(dayDiff("2024-02-28", "2024-03-01")).toBe(2); // 2024 is a leap year
    expect(dayDiff("2025-02-28", "2025-03-01")).toBe(1);
  });

  it("returns null when either side is unusable", () => {
    expect(dayDiff("", "2026-10-06")).toBeNull();
    expect(dayDiff("2026-10-06", "garbage")).toBeNull();
  });
});

describe("addDays", () => {
  it("adds and subtracts days", () => {
    expect(addDays("2026-10-06", 5)).toBe("2026-10-11");
    expect(addDays("2026-10-06", -5)).toBe("2026-10-01");
    expect(addDays("2026-10-06", 0)).toBe("2026-10-06");
  });

  it("rolls over month and year ends", () => {
    expect(addDays("2026-10-31", 1)).toBe("2026-11-01");
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
    expect(addDays("2026-03-01", -1)).toBe("2026-02-28");
  });

  it("returns empty string for an invalid input date", () => {
    expect(addDays("", 3)).toBe("");
    expect(addDays("nonsense", 3)).toBe("");
  });
});

describe("cycleLength", () => {
  it("counts inclusively: 1 Oct to 28 Oct is a 28-day cycle", () => {
    expect(cycleLength(cycle("2026-10-01", "2026-10-28"))).toBe(28);
  });

  it("treats a same-day cycle as one day, not zero", () => {
    expect(cycleLength(cycle("2026-10-01", "2026-10-01"))).toBe(1);
  });

  it("prefers an explicit lengthDays when it is positive", () => {
    expect(cycleLength(cycle("2026-10-01", "2026-10-28", { lengthDays: 30 }))).toBe(30);
  });

  it("ignores a non-positive lengthDays and falls back to the dates", () => {
    expect(cycleLength(cycle("2026-10-01", "2026-10-28", { lengthDays: 0 }))).toBe(28);
    expect(cycleLength(cycle("2026-10-01", "2026-10-28", { lengthDays: null }))).toBe(28);
  });

  it("returns null for a cycle still in progress", () => {
    expect(cycleLength(cycle("2026-10-01"))).toBeNull();
  });

  it("rejects an end date before the start date", () => {
    expect(cycleLength(cycle("2026-10-10", "2026-10-05"))).toBeNull();
  });

  it("returns null when dates are missing or malformed", () => {
    expect(cycleLength(cycle(""))).toBeNull();
    expect(cycleLength(cycle("2026-10-01", "bad"))).toBeNull();
  });
});

describe("cycleStats", () => {
  it("reports an empty history without dividing by zero", () => {
    const s = cycleStats([]);
    expect(s).toEqual({
      count: 0, logged: 0, avgLength: 0, lastStart: "", lastLength: null,
      shortest: null, longest: null, spread: 0, running: false,
    });
  });

  it("averages logged lengths to one decimal place", () => {
    // 28, 29, 30 -> 29 ; plus one still-running cycle that is not counted.
    const s = cycleStats(history(
      cycle("2026-10-01"),
      cycle("2026-09-01", "2026-09-30"), // 30
      cycle("2026-08-01", "2026-08-29"), // 29
      cycle("2026-07-01", "2026-07-28"), // 28
    ));
    expect(s.count).toBe(4);
    expect(s.logged).toBe(3);
    expect(s.avgLength).toBe(29);
    expect(s.shortest).toBe(28);
    expect(s.longest).toBe(30);
    expect(s.spread).toBe(2);
  });

  it("rounds a non-integer average to one decimal", () => {
    const s = cycleStats(history(
      cycle("2026-09-01", "2026-09-28"), // 28
      cycle("2026-08-01", "2026-08-29"), // 29
      cycle("2026-07-01", "2026-07-29"), // 29
    ));
    expect(s.avgLength).toBeCloseTo(28.7, 5);
  });

  it("identifies the most recent cycle and whether it is running", () => {
    const rows = history(cycle("2026-10-01"), cycle("2026-09-01", "2026-09-28"));
    expect(cycleStats(rows, "2026-10-06").running).toBe(true);
    expect(cycleStats(rows, "2026-10-06").lastStart).toBe("2026-10-01");
    expect(cycleStats(rows, "2026-10-06").lastLength).toBeNull();
  });

  it("stops reporting running once the cycle is more than 10 days old", () => {
    const rows = history(cycle("2026-10-01"));
    expect(cycleStats(rows, "2026-10-11").running).toBe(true);  // exactly 10 days
    expect(cycleStats(rows, "2026-10-12").running).toBe(false); // 11 days
  });

  it("does not call a closed cycle running", () => {
    const rows = history(cycle("2026-10-01", "2026-10-05"));
    expect(cycleStats(rows, "2026-10-06").running).toBe(false);
  });

  it("is not running when no today is supplied", () => {
    expect(cycleStats(history(cycle("2026-10-01"))).running).toBe(false);
  });

  it("skips rows without a usable start date", () => {
    const s = cycleStats(history(cycle(""), cycle("2026-09-01", "2026-09-28")));
    expect(s.count).toBe(1);
    expect(s.logged).toBe(1);
  });

  it("does not mutate the caller's array", () => {
    const rows = history(cycle("2026-10-01"), cycle("2026-09-01", "2026-09-28"));
    const copy = [...rows];
    cycleStats(rows);
    expect(rows).toEqual(copy);
  });
});

describe("predictionConfidence", () => {
  it("is high with three or more consistent cycles", () => {
    const c = predictionConfidence(history(
      cycle("2026-09-01", "2026-09-28"),
      cycle("2026-08-01", "2026-08-29"),
      cycle("2026-07-01", "2026-07-28"),
    ));
    expect(c.level).toBe("high");
    expect(c.samples).toBe(3);
    expect(c.spread).toBe(1);
  });

  it("drops to medium when the spread widens past three days", () => {
    const c = predictionConfidence(history(
      cycle("2026-09-01", "2026-09-28"), // 28
      cycle("2026-08-01", "2026-08-30"), // 30
      cycle("2026-07-01", "2026-07-29"), // 29
      cycle("2026-06-01", "2026-06-30"), // 30... spread 2
      cycle("2026-05-01", "2026-06-04"), // 35 -> spread 7
    ));
    expect(c.level).toBe("medium");
  });

  it("is low with fewer than two logged cycles", () => {
    expect(predictionConfidence([]).level).toBe("low");
    expect(predictionConfidence(history(cycle("2026-09-01", "2026-09-28"))).level).toBe("low");
  });

  it("is low when cycles are wildly inconsistent", () => {
    const c = predictionConfidence(history(
      cycle("2026-09-01", "2026-09-22"), // 22
      cycle("2026-08-01", "2026-08-31"), // 31
      cycle("2026-07-01", "2026-07-28"), // 28
    ));
    expect(c.spread).toBe(9);
    expect(c.level).toBe("low");
  });

  it("does not count in-progress cycles as samples", () => {
    const c = predictionConfidence(history(
      cycle("2026-10-01"),
      cycle("2026-09-01", "2026-09-28"),
      cycle("2026-08-01", "2026-08-29"),
    ));
    expect(c.samples).toBe(2);
    expect(c.level).toBe("medium");
  });
});

describe("fertileWindow", () => {
  it("places ovulation 14 days before the predicted next period", () => {
    const w = fertileWindow("2026-10-28");
    expect(w).not.toBeNull();
    expect(w!.ovulation).toBe("2026-10-14");
  });

  it("spans two days either side of ovulation", () => {
    const w = fertileWindow("2026-10-28")!;
    expect(w.start).toBe("2026-10-12");
    expect(w.end).toBe("2026-10-16");
    expect(dayDiff(w.start, w.end)).toBe(4);
  });

  it("returns null without a predicted start date", () => {
    expect(fertileWindow(undefined)).toBeNull();
    expect(fertileWindow("")).toBeNull();
    expect(fertileWindow("garbage")).toBeNull();
  });

  it("is unaffected by the cycle length argument (kept for the caller's clamping)", () => {
    // The window is derived from the predicted start, so length only clamps.
    expect(fertileWindow("2026-10-28", 21)!.ovulation).toBe("2026-10-14");
    expect(fertileWindow("2026-10-28", 90)!.ovulation).toBe("2026-10-14");
  });
});

describe("effectiveCycleLength", () => {
  it("uses the historical average when it is plausible", () => {
    const rows = history(
      cycle("2026-09-01", "2026-09-30"), // 30
      cycle("2026-08-01", "2026-08-30"), // 30
    );
    expect(effectiveCycleLength(rows)).toBe(30);
  });

  it("falls back to the setting when there is no history", () => {
    expect(effectiveCycleLength([])).toBe(28);
    expect(effectiveCycleLength([], 32)).toBe(32);
  });

  it("clamps an implausible fallback into the 20-45 range", () => {
    expect(effectiveCycleLength([], 5)).toBe(20);
    expect(effectiveCycleLength([], 999)).toBe(45);
    expect(effectiveCycleLength([], Number.NaN)).toBe(28);
  });

  it("rejects an out-of-range historical average and uses the fallback", () => {
    const rows = history(cycle("2026-09-01", "2026-09-05")); // 5 days — implausible
    expect(effectiveCycleLength(rows, 30)).toBe(30);
  });
});

describe("lengthLabel", () => {
  const t = (_key: string, fallback: string) => fallback;

  it("renders the day count through the translator", () => {
    expect(lengthLabel(history(cycle("2026-09-01", "2026-09-28")), 0, t)).toBe("28 hari");
  });

  it("says the cycle is still running when there is no end date", () => {
    expect(lengthLabel(history(cycle("2026-10-01")), 0, t)).toBe("Berjalan");
  });

  it("handles an out-of-range index", () => {
    expect(lengthLabel(history(cycle("2026-09-01", "2026-09-28")), 5, t)).toBe("Berjalan");
  });

  it("works without a translator", () => {
    expect(lengthLabel(history(cycle("2026-09-01", "2026-09-28")), 0)).toBe("28");
    expect(lengthLabel([], 0)).toBe("—");
  });
});

describe("cycleRows", () => {
  it("normalises dates and attaches the computed length", () => {
    const rows = cycleRows(history(cycle("2026-09-01T09:00:00Z", "2026-09-28T22:00:00Z")));
    expect(rows).toHaveLength(1);
    expect(rows[0].startDate).toBe("2026-09-01");
    expect(rows[0].endDate).toBe("2026-09-28");
    expect(rows[0].length).toBe(28);
    expect(rows[0].lengthText).toBe("28");
  });

  it("drops rows with no usable start date", () => {
    expect(cycleRows(history(cycle(""), cycle("2026-09-01", "2026-09-28")))).toHaveLength(1);
  });

  it("leaves a running cycle with an empty length text", () => {
    const rows = cycleRows(history(cycle("2026-10-01")));
    expect(rows[0].length).toBeNull();
    expect(rows[0].lengthText).toBe("");
  });

  it("preserves the server's newest-first ordering", () => {
    const rows = cycleRows(history(
      cycle("2026-10-01"),
      cycle("2026-09-01", "2026-09-28"),
      cycle("2026-08-01", "2026-08-29"),
    ));
    expect(rows.map((r) => r.startDate)).toEqual(["2026-10-01", "2026-09-01", "2026-08-01"]);
  });

  it("keeps the other fields of each row", () => {
    const rows = cycleRows(history(cycle("2026-09-01", "2026-09-28", { notes: "ringan", id: "42" })));
    expect(rows[0].notes).toBe("ringan");
    expect(rows[0].id).toBe("42");
  });
});

describe("validateCycleForm", () => {
  it("accepts a valid closed cycle", () => {
    expect(validateCycleForm({ startDate: "2026-09-01", endDate: "2026-09-28" })).toBeNull();
  });

  it("accepts an open-ended cycle", () => {
    expect(validateCycleForm({ startDate: "2026-10-01" })).toBeNull();
  });

  it("accepts a same-day cycle", () => {
    expect(validateCycleForm({ startDate: "2026-10-01", endDate: "2026-10-01" })).toBeNull();
  });

  it("requires a start date", () => {
    expect(validateCycleForm({})).toBe("love_cycle_date_required");
    expect(validateCycleForm({ startDate: "" })).toBe("love_cycle_date_required");
    expect(validateCycleForm({ startDate: "06/10/2026" })).toBe("love_cycle_date_required");
  });

  it("rejects a malformed end date", () => {
    expect(validateCycleForm({ startDate: "2026-09-01", endDate: "soon" }))
      .toBe("love_cycle_date_invalid");
  });

  it("rejects an end date before the start date", () => {
    expect(validateCycleForm({ startDate: "2026-09-28", endDate: "2026-09-01" }))
      .toBe("love_cycle_range_invalid");
  });
});

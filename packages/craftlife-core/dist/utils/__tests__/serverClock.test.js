/**
 * M02 — serverClock.ts.
 *
 * computeDateKey() decides WHICH DAY it is for every daily reset: quests,
 * habit streaks, daily rewards, shop restock. Getting it wrong means a user
 * in WIB gets their dailies reset at 07:00 instead of midnight.
 *
 * The invariant under test: the key must follow the APP's wall clock
 * (server epoch + tz offset + elapsed local time), never raw UTC.
 */
import { describe, it, expect } from "vitest";
import { computeDateKey } from "../serverClock";
/** WIB — the app's primary audience. */
const WIB = 420;
/** New York, winter (UTC-5) — proves negative offsets work too. */
const NY = -300;
const utc = (y, m, d, h, mi, s = 0) => Date.UTC(y, m - 1, d, h, mi, s) / 1000;
describe("computeDateKey", () => {
    it("returns YYYY-MM-DD", () => {
        const epoch = utc(2026, 10, 6, 4, 0);
        expect(computeDateKey(epoch, 0, WIB, 0)).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });
    it("applies the app timezone instead of UTC", () => {
        // 20:00 UTC on 5 Oct is already 03:00 on 6 Oct in WIB.
        const epoch = utc(2026, 10, 5, 20, 0);
        expect(computeDateKey(epoch, 0, WIB, 0)).toBe("2026-10-06");
        // Same instant, zero offset → still the 5th. This is the bug being prevented.
        expect(computeDateKey(epoch, 0, 0, 0)).toBe("2026-10-05");
    });
    it("rolls over exactly at local midnight in WIB", () => {
        // WIB midnight = 17:00 UTC the previous day.
        expect(computeDateKey(utc(2026, 10, 5, 16, 59, 59), 0, WIB, 0)).toBe("2026-10-05");
        expect(computeDateKey(utc(2026, 10, 5, 17, 0, 0), 0, WIB, 0)).toBe("2026-10-06");
    });
    it("handles negative offsets", () => {
        // 03:00 UTC on 6 Oct is still 22:00 on 5 Oct in UTC-5.
        const epoch = utc(2026, 10, 6, 3, 0);
        expect(computeDateKey(epoch, 0, NY, 0)).toBe("2026-10-05");
        expect(computeDateKey(epoch, 0, 0, 0)).toBe("2026-10-06");
    });
    it("advances with elapsed local time after the response", () => {
        // Response received at 23:30 WIB; the app has been open 1h → next day.
        const epoch = utc(2026, 10, 5, 16, 30); // 23:30 WIB, 5 Oct
        const receivedAt = 0;
        expect(computeDateKey(epoch, receivedAt, WIB, 0)).toBe("2026-10-05");
        const oneHourMs = 60 * 60 * 1000;
        expect(computeDateKey(epoch, receivedAt, WIB, oneHourMs)).toBe("2026-10-06");
    });
    it("is unaffected by a large but equal receivedAt/nowMs pair", () => {
        // Only the DELTA matters; a realistic Date.now() must not shift the day.
        const epoch = utc(2026, 10, 6, 4, 0);
        const realNow = Date.UTC(2026, 9, 6, 5, 0);
        expect(computeDateKey(epoch, realNow, WIB, realNow)).toBe("2026-10-06");
    });
    it("is deterministic (pure — no ref/state reads)", () => {
        const args = [utc(2026, 10, 6, 4, 0), 1000, WIB, 2000];
        expect(computeDateKey(...args)).toBe(computeDateKey(...args));
    });
    it("returns empty string for non-finite or missing input", () => {
        // Callers treat "" as "clock not ready yet" and must not reset dailies.
        expect(computeDateKey(Number.NaN, 0, WIB, 0)).toBe("");
        expect(computeDateKey(Number.POSITIVE_INFINITY, 0, WIB, 0)).toBe("");
        // @ts-expect-error deliberately wrong type: guards the Python-side contract
        expect(computeDateKey(undefined, 0, WIB, 0)).toBe("");
        // @ts-expect-error deliberately wrong type
        expect(computeDateKey(utc(2026, 10, 6, 4, 0), 0, null, 0)).toBe("");
    });
});
//# sourceMappingURL=serverClock.test.js.map
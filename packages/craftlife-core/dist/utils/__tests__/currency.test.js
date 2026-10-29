/**
 * M02 — currency.ts.
 *
 * These are the money rules the whole app must agree on (UPDATE_RULES P2).
 * They are parity-checked against the PyQt formatters in `database.py`,
 * so a change here silently breaks desktop/web agreement.
 *
 * Pure functions only — ensureCurrencyRates() needs the network and is
 * deliberately not exercised here.
 */
import { describe, it, expect } from "vitest";
import { currencySymbol, fromIdr, formatMoney, parseAmount, parseMoneyInput, maskMoney, getCurrencyRates, } from "../currency";
describe("currencySymbol", () => {
    it("maps the built-in currencies", () => {
        expect(currencySymbol("IDR")).toBe("Rp");
        expect(currencySymbol("USD")).toBe("$");
        expect(currencySymbol("EUR")).toBe("€");
        expect(currencySymbol("JPY")).toBe("¥");
        expect(currencySymbol("MYR")).toBe("RM");
    });
    it("falls back to the raw code for unknown currencies", () => {
        // Never render "undefined" into a money label.
        expect(currencySymbol("XYZ")).toBe("XYZ");
    });
    it("falls back to Rp when the code is empty", () => {
        expect(currencySymbol("")).toBe("Rp");
    });
});
describe("getCurrencyRates", () => {
    it("exposes the default table before any fetch", () => {
        const rates = getCurrencyRates();
        // Mirrors database.CURRENCY_RATES so offline mode matches the desktop app.
        expect(rates.IDR).toBe(1);
        expect(rates.USD).toBeGreaterThan(0);
        expect(rates.EUR).toBeGreaterThan(0);
    });
});
describe("fromIdr", () => {
    it("passes IDR through untouched", () => {
        expect(fromIdr(1250000, "IDR")).toBe(1250000);
    });
    it("divides by the rate for a foreign currency", () => {
        const rate = getCurrencyRates().USD;
        expect(fromIdr(rate * 1000, "USD")).toBeCloseTo(1000, 6);
    });
    it("treats an unknown currency rate as 1 rather than dividing by undefined", () => {
        expect(fromIdr(1000, "XYZ")).toBe(1000);
    });
});
describe("formatMoney", () => {
    it("renders Rp with thousands separators and no decimals (PyQt parity)", () => {
        expect(formatMoney(1000000, "IDR")).toBe("Rp 1,000,000");
        expect(formatMoney(0, "IDR")).toBe("Rp 0");
    });
    it("rounds down fractional IDR to whole units", () => {
        // PyQt: f"{converted:,.0f}"
        expect(formatMoney(1234.4, "IDR")).toBe("Rp 1,234");
        expect(formatMoney(1234.6, "IDR")).toBe("Rp 1,235");
    });
    it("converts before formatting when the user currency is not IDR", () => {
        const rate = getCurrencyRates().USD;
        expect(formatMoney(rate, "USD")).toBe("$ 1");
        expect(formatMoney(rate * 2500, "USD")).toBe("$ 2,500");
    });
    it("coerces junk input to zero instead of NaN", () => {
        expect(formatMoney(Number.NaN, "IDR")).toBe("Rp 0");
        // @ts-expect-error deliberately wrong type: the app reads this off DB rows
        expect(formatMoney(undefined, "IDR")).toBe("Rp 0");
    });
});
describe("parseAmount", () => {
    it("accepts plain and decimal amounts", () => {
        expect(parseAmount("1000")).toBe(1000);
        expect(parseAmount("1000.5")).toBe(1000.5);
        expect(parseAmount("  250  ")).toBe(250);
    });
    it("treats a comma as a decimal separator (PyQt parity)", () => {
        expect(parseAmount("12,5")).toBe(12.5);
    });
    it("rejects empty, non-numeric, zero and negative input", () => {
        expect(parseAmount("")).toBeNull();
        expect(parseAmount("   ")).toBeNull();
        expect(parseAmount("abc")).toBeNull();
        expect(parseAmount("0")).toBeNull();
        expect(parseAmount("-5")).toBeNull();
    });
});
describe("parseMoneyInput (P30 dual-locale)", () => {
    it("reads English grouping", () => {
        expect(parseMoneyInput("1,234,567.89")).toBeCloseTo(1234567.89, 2);
    });
    it("reads Indonesian grouping", () => {
        expect(parseMoneyInput("1.234.567,89")).toBeCloseTo(1234567.89, 2);
    });
    it("treats a trailing 1-2 digit group as decimals", () => {
        expect(parseMoneyInput("12,5")).toBe(12.5);
        expect(parseMoneyInput("12,50")).toBe(12.5);
    });
    it("treats a 3-digit group as thousands, not decimals", () => {
        expect(parseMoneyInput("1,234")).toBe(1234);
        expect(parseMoneyInput("1.234")).toBe(1234);
    });
    it("strips currency noise the user may have pasted", () => {
        expect(parseMoneyInput("Rp 1.000")).toBe(1000);
        expect(parseMoneyInput("$25")).toBe(25);
    });
    it("rejects separators with no digits", () => {
        expect(parseMoneyInput("")).toBeNull();
        expect(parseMoneyInput("-")).toBeNull();
        expect(parseMoneyInput(".")).toBeNull();
        expect(parseMoneyInput(",")).toBeNull();
        expect(parseMoneyInput("abc")).toBeNull();
    });
    it("keeps negatives so a debt can be typed", () => {
        expect(parseMoneyInput("-500")).toBe(-500);
    });
});
describe("maskMoney", () => {
    it("returns empty string for nullish values (keeps the input blank)", () => {
        expect(maskMoney(null)).toBe("");
        expect(maskMoney(undefined)).toBe("");
        expect(maskMoney("")).toBe("");
    });
    it("formats numbers with up to 2 decimals", () => {
        expect(maskMoney(1000)).toBe("1,000");
        expect(maskMoney(1234.5)).toBe("1,234.5");
        expect(maskMoney(1234.567)).toBe("1,234.57");
    });
    it("normalises a typed string", () => {
        expect(maskMoney("1.234.567,89")).toBe("1,234,567.89");
    });
    it("returns empty string for unparsable strings", () => {
        expect(maskMoney("abc")).toBe("");
    });
});
//# sourceMappingURL=currency.test.js.map
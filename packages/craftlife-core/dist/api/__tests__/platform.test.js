/**
 * M07 — adapter platform.
 *
 * Tes kedua di bawah ini yang penting. Klaimnya bukan cuma "adapter dipakai",
 * tapi "kode DOM tidak pernah disentuh kalau adapter terpasang" — karena di
 * React Native `window.location` tidak ada, dan versi lama `apiBase()`
 * membacanya di baris PERTAMA. Kalau urutannya salah, aplikasi Android akan
 * crash saat dinyalakan meskipun adapter sudah dipasang dengan benar.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiBase, authToken } from "../client";
import { resetApiPlatformAdapter, setApiPlatformAdapter } from "../platform";
afterEach(() => {
    resetApiPlatformAdapter();
    vi.unstubAllGlobals();
});
describe("tanpa adapter — perilaku web tidak berubah", () => {
    it("apiBase membaca VITE_API_BASE lalu query string", () => {
        vi.stubGlobal("window", { location: { search: "?api=https://contoh.test/" } });
        expect(apiBase()).toBe("https://contoh.test");
    });
    it("apiBase mengembalikan string kosong kalau tidak ada petunjuk", () => {
        vi.stubGlobal("window", { location: { search: "" } });
        expect(apiBase()).toBe("");
    });
    it("authToken membaca sessionStorage", () => {
        const store = new Map([["craftlife_token", "tok-web"]]);
        vi.stubGlobal("sessionStorage", {
            getItem: (k) => store.get(k) ?? null,
        });
        expect(authToken()).toBe("tok-web");
    });
    it("authToken tidak melempar kalau sessionStorage tidak ada", () => {
        vi.stubGlobal("sessionStorage", undefined);
        expect(authToken()).toBeNull();
    });
});
describe("dengan adapter — jalur native", () => {
    it("nilai adapter menang atas env dan query string", () => {
        vi.stubGlobal("window", { location: { search: "?api=https://salah.test" } });
        setApiPlatformAdapter({ apiBase: () => "https://android.test/", authToken: () => null });
        expect(apiBase()).toBe("https://android.test");
    });
    it("token dari adapter dipakai, sessionStorage tidak dibaca", () => {
        const getItem = vi.fn(() => "tok-web");
        vi.stubGlobal("sessionStorage", { getItem });
        setApiPlatformAdapter({ apiBase: () => "", authToken: () => "tok-android" });
        expect(authToken()).toBe("tok-android");
        expect(getItem).not.toHaveBeenCalled();
    });
    it("window.location TIDAK disentuh saat adapter terpasang", () => {
        // Simulasi React Native: window ada, tapi location tidak. Membacanya harus
        // melempar — jadi kalau tes ini lulus, urutan pemeriksaannya benar.
        vi.stubGlobal("window", {});
        setApiPlatformAdapter({ apiBase: () => "https://android.test", authToken: () => null });
        expect(() => apiBase()).not.toThrow();
        expect(apiBase()).toBe("https://android.test");
    });
    it("adapter yang mengembalikan null membuat authToken null, bukan jatuh ke DOM", () => {
        const getItem = vi.fn(() => "tok-web");
        vi.stubGlobal("sessionStorage", { getItem });
        setApiPlatformAdapter({ apiBase: () => "", authToken: () => null });
        expect(authToken()).toBeNull();
        expect(getItem).not.toHaveBeenCalled();
    });
    it("reset mengembalikan perilaku web", () => {
        setApiPlatformAdapter({ apiBase: () => "https://android.test", authToken: () => "x" });
        resetApiPlatformAdapter();
        vi.stubGlobal("window", { location: { search: "?api=https://web.test" } });
        expect(apiBase()).toBe("https://web.test");
    });
});
//# sourceMappingURL=platform.test.js.map
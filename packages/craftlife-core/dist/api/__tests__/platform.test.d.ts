/**
 * M07 — adapter platform.
 *
 * Tes kedua di bawah ini yang penting. Klaimnya bukan cuma "adapter dipakai",
 * tapi "kode DOM tidak pernah disentuh kalau adapter terpasang" — karena di
 * React Native `window.location` tidak ada, dan versi lama `apiBase()`
 * membacanya di baris PERTAMA. Kalau urutannya salah, aplikasi Android akan
 * crash saat dinyalakan meskipun adapter sudah dipasang dengan benar.
 */
export {};
//# sourceMappingURL=platform.test.d.ts.map
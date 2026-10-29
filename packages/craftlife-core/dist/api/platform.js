/**
 * M07 — adapter platform untuk API client.
 *
 * `client.ts` lahir untuk browser: `apiBase()` membaca `window.location.search`
 * dan `import.meta.env`, `authToken()` membaca `sessionStorage`. Tidak satu pun
 * ada di React Native.
 *
 * Yang TIDAK dilakukan: menyalin `client.ts` menjadi versi Android. Dua salinan
 * berarti setiap perubahan kontrak API harus dilakukan dua kali, dan suatu hari
 * salah satunya terlewat (P2).
 *
 * Yang dilakukan: titik suntik tunggal. Perilakunya:
 *
 *   adapter belum dipasang -> jalur DOM yang lama, byte-for-byte sama seperti
 *                             sebelumnya, jadi web tidak berubah sama sekali
 *   adapter terpasang      -> nilai dari adapter dipakai, kode DOM tidak
 *                             pernah disentuh (ini penting: `window.location`
 *                             dibaca LEBIH DULU di versi lama, dan di RN itu
 *                             melempar TypeError sebelum sempat fallback)
 *
 * Karena itu pemeriksaan adapter harus terjadi sebelum akses DOM apa pun.
 */
let currentAdapter = null;
/** Pasang adapter platform. Dipanggil sekali saat aplikasi native dinyalakan. */
export function setApiPlatformAdapter(adapter) {
    currentAdapter = adapter;
}
export function getApiPlatformAdapter() {
    return currentAdapter;
}
/** Untuk tes: memastikan tidak ada adapter yang bocor antar kasus. */
export function resetApiPlatformAdapter() {
    currentAdapter = null;
}
//# sourceMappingURL=platform.js.map
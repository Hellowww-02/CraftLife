/** C08: kunci tanggal wall-clock server (YYYY-MM-DD) dari base jam + tz offset.
 *  Murni (tanpa ref/state) agar bisa di-unit-test; dipakai GameContext.serverDateKey.
 *  @param epoch detik epoch server saat respons diterima
 *  @param receivedAt Date.now() saat respons diterima
 *  @param tzOffsetMin offset zona app dalam menit (mis. WIB = +420)
 *  @param nowMs Date.now() saat ini
 */
export declare function computeDateKey(epoch: number, receivedAt: number, tzOffsetMin: number, nowMs: number): string;
//# sourceMappingURL=serverClock.d.ts.map
/** C08: kunci tanggal wall-clock server (YYYY-MM-DD) dari base jam + tz offset.
 *  Murni (tanpa ref/state) agar bisa di-unit-test; dipakai GameContext.serverDateKey.
 *  @param epoch detik epoch server saat respons diterima
 *  @param receivedAt Date.now() saat respons diterima
 *  @param tzOffsetMin offset zona app dalam menit (mis. WIB = +420)
 *  @param nowMs Date.now() saat ini
 */
export function computeDateKey(epoch: number, receivedAt: number, tzOffsetMin: number, nowMs: number): string {
  if (![epoch, receivedAt, tzOffsetMin, nowMs].every((n) => typeof n === 'number' && Number.isFinite(n))) {
    return '';
  }
  const ms = epoch * 1000 + (nowMs - receivedAt) + tzOffsetMin * 60000;
  try {
    return new Date(ms).toISOString().slice(0, 10);
  } catch {
    return '';
  }
}

const UNITS = ["B", "KiB", "MiB", "GiB", "TiB"];

export function humanSize(bytes: number): string {
  let v = bytes;
  let u = 0;
  while (v >= 1024 && u < UNITS.length - 1) {
    v /= 1024;
    u += 1;
  }
  return `${u === 0 ? v : v.toFixed(1)} ${UNITS[u]}`;
}

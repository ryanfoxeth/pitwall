export const escapeHTML = value => String(value ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const seconds = value => {
  if (Array.isArray(value)) return value.map(seconds).join(' / ');
  if (value == null || !Number.isFinite(Number(value))) return value == null ? '—' : String(value);
  const n = Number(value); return n >= 60 ? `${Math.floor(n / 60)}:${(n % 60).toFixed(3).padStart(6, '0')}` : n.toFixed(3);
};
export const latest = rows => [...rows].sort((a, b) => (Date.parse(a.date) || 0) - (Date.parse(b.date) || 0)).at(-1);
export function timingRows(feeds, { useResults = true } = {}) {
  const rows = topic => feeds[topic]?.data ?? [];
  return rows('drivers').map(driver => {
    const own = topic => rows(topic).filter(r => r.driver_number === driver.driver_number);
    const laps = own('laps').sort((a,b) => a.lap_number - b.lap_number);
    const completed = laps.filter(l => Number.isFinite(l.lap_duration) && l.lap_duration > 0);
    const lap = completed.at(-1), currentLap = laps.at(-1);
    const stint = own('stints').sort((a,b) => a.stint_number - b.stint_number).at(-1);
    const result = useResults ? own('session_result')[0] : null;
    return { ...driver, position: result?.position ?? latest(own('position'))?.position, interval: latest(own('intervals')), lap, currentLap, best: completed.length ? Math.min(...completed.map(l => l.lap_duration)) : null, stint, tireAge: stint && stint.tyre_age_at_start != null && stint.lap_start != null ? stint.tyre_age_at_start + Math.max(0, (stint.lap_end ?? lap?.lap_number ?? stint.lap_start - 1) - stint.lap_start + 1) : null, result };
  }).sort((a,b) => (a.position ?? 999) - (b.position ?? 999));
}
export function mergeUpdate(topic, rows, row) {
  const key = r => topic === 'laps' ? `${r.driver_number}:${r.lap_number}` : topic === 'stints' ? `${r.driver_number}:${r.stint_number}` : ['drivers','session_result','starting_grid','championship_drivers'].includes(topic) ? r.driver_number : topic === 'championship_teams' ? r.team_name : r._key ?? `${r.date}:${r.driver_number}:${r.message ?? ''}`;
  const i = rows.findIndex(r => key(r) === key(row));
  if (i < 0) rows.push(row);
  else if (!(rows[i]._id > row._id)) rows[i] = { ...rows[i], ...row };
  if (rows.length > 25000) rows.splice(0, rows.length - 25000);
  return rows;
}

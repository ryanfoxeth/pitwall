import { EventEmitter } from 'node:events';
import { connect } from 'mqtt';

export const TOPICS = ['car_data', 'championship_drivers', 'championship_teams', 'drivers', 'intervals', 'laps', 'location', 'meetings', 'overtakes', 'pit', 'position', 'race_control', 'sessions', 'session_result', 'starting_grid', 'stints', 'team_radio', 'weather'];
export class FeedError extends Error {
  constructor(message, status = 503) { super(message); this.status = status; }
}
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const iso = ms => new Date(ms).toISOString();
export function sessionMode(session, now = Date.now()) {
  if (!session || !Number.isFinite(Date.parse(session.date_end))) return 'unknown';
  if (now < Date.parse(session.date_start) - 1800000) return 'upcoming';
  if (now <= Date.parse(session.date_end) + 1800000) return 'live-window';
  return 'historical';
}
export function recordKey(topic, row) {
  // REST and MQTT must use the same identity, including revised laps/stints.
  const prefix = `${row.session_key ?? row.meeting_key ?? ''}:`;
  if (topic === 'laps') return prefix + `${row.driver_number}:${row.lap_number}`;
  if (topic === 'stints') return prefix + `${row.driver_number}:${row.stint_number}`;
  if (['drivers', 'championship_drivers', 'session_result', 'starting_grid'].includes(topic)) return prefix + row.driver_number;
  if (topic === 'championship_teams') return prefix + row.team_name;
  if (topic === 'sessions') return String(row.session_key);
  if (topic === 'meetings') return String(row.meeting_key);
  return prefix + `${row.driver_number ?? ''}:${row.date}:${topic === 'race_control' ? row.message : topic === 'overtakes' ? `${row.overtaking_driver_number}:${row.overtaken_driver_number}` : ''}`;
}
export function mergeRows(topic, oldRows, updates, limit = 25000) {
  const rows = new Map(oldRows.map(row => [recordKey(topic, row), row]));
  for (const row of updates) {
    const key = recordKey(topic, row), previous = rows.get(key);
    if (previous?._id != null && row._id != null && previous._id > row._id) continue;
    rows.set(key, { ...previous, ...row });
  }
  return [...rows.values()].sort((a, b) => (Date.parse(a.date ?? a.date_start) || 0) - (Date.parse(b.date ?? b.date_start) || 0)).slice(-limit);
}

export class PitwallService extends EventEmitter {
  constructor({ fetchImpl = globalThis.fetch, now = Date.now, wait = sleep, env = process.env, mqttConnect = connect } = {}) {
    super(); Object.assign(this, { fetchImpl, now, wait, env, mqttConnect });
    this.cache = new Map(); this.pending = new Map(); this.queue = Promise.resolve(); this.nextRequest = 0;
    this.token = null; this.tokenExpiry = 0; this.liveRows = new Map(); this.connection = 'disabled'; this.lastMessageAt = null; this.sessionReceived = new Map();
  }
  get configured() { return Boolean(this.env.OPENF1_USERNAME && this.env.OPENF1_PASSWORD); }
  status(sessionKey) { const received = this.sessionReceived.get(String(sessionKey)); return { session_last_message_at: received ?? null, session_stale: !received || this.now() - Date.parse(received) > 30000, configured: this.configured, enabled: this.env.OPENF1_LIVE_ENABLED === 'true', connection: this.connection, last_message_at: this.lastMessageAt, stale: !this.lastMessageAt || this.now() - Date.parse(this.lastMessageAt) > 30000 }; }
  async accessToken() {
    if (!this.configured) return null;
    if (this.token && this.tokenExpiry > this.now() + 60000) return this.token;
    if (this.tokenPending) return this.tokenPending;
    this.tokenPending = (async () => {
      const response = await this.fetchImpl('https://api.openf1.org/token', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ username: this.env.OPENF1_USERNAME, password: this.env.OPENF1_PASSWORD }), signal: AbortSignal.timeout(15000) });
      if (!response.ok) throw new FeedError('OpenF1 authentication failed. Check the server subscription credentials.', 503);
      const data = await response.json();
      if (!data.access_token) throw new FeedError('OpenF1 did not return an access token.');
      this.token = data.access_token; this.tokenExpiry = this.now() + (Number(data.expires_in) || 3600) * 1000;
      return this.token;
    })().finally(() => { this.tokenPending = null; });
    return this.tokenPending;
  }
  async request(url, { source = 'OpenF1', ttl = 3600000 } = {}) {
    const cached = this.cache.get(url);
    if (cached && this.now() < cached.expires) return { ...cached.payload, cached: true };
    if (this.pending.has(url)) return this.pending.get(url);
    if (this.pending.size >= 80) throw new FeedError('Pitwall is busy loading data. Try again shortly.', 429);
    const job = this.queue.catch(() => {}).then(async () => {
      try {
        for (let attempt = 0; attempt < 3; attempt++) {
          await this.wait(Math.max(0, this.nextRequest - this.now()));
          this.nextRequest = this.now() + 2100; // Below free OpenF1 30/min and Jolpica burst limits.
          const token = source === 'OpenF1' ? await this.accessToken() : null;
          const response = await this.fetchImpl(url, { headers: token ? { Authorization: `Bearer ${token}` } : {}, signal: AbortSignal.timeout(20000) });
          if (response.status === 401 && token && attempt === 0) { this.token = null; continue; }
          if (response.status === 429 && attempt < 2) {
            const retry = response.headers.get('retry-after');
            const delay = Number(retry) * 1000 || Date.parse(retry) - this.now() || 10000;
            this.nextRequest = this.now() + Math.min(60000, Math.max(2100, delay)); continue;
          }
          if (response.status === 404 && source === 'OpenF1') {
            const payload = { source, fetched_at: iso(this.now()), stale: false, cached: false, data: [], availability: 'not_published', note: 'OpenF1 has not published records for this query.' };
            this.cache.set(url, { expires: this.now() + Math.min(ttl, 60000), payload });
            while (this.cache.size > 100) this.cache.delete(this.cache.keys().next().value);
            return payload;
          }
          if (!response.ok) throw new FeedError([401, 403].includes(response.status) ? 'OpenF1 requires authentication right now. During live sessions this can include historical data. Configure your subscription on the server.' : `${source} returned HTTP ${response.status}.`, response.status === 404 ? 404 : 503);
          const data = await response.json();
          if (source === 'OpenF1' && !Array.isArray(data)) throw new FeedError('Unexpected OpenF1 response.');
          const payload = { source, fetched_at: iso(this.now()), stale: false, cached: false, data };
          this.cache.delete(url); this.cache.set(url, { expires: this.now() + ttl, payload });
          while (this.cache.size > 100) this.cache.delete(this.cache.keys().next().value);
          return payload;
        }
      } catch (error) {
        if (cached) return { ...cached.payload, stale: true, cached: true, warning: 'Provider unavailable; showing last fetched data.' };
        if (error instanceof FeedError) throw error;
        throw new FeedError(`${source} is temporarily unavailable.`);
      }
    });
    this.queue = job;
    const pending = job.finally(() => this.pending.delete(url)); this.pending.set(url, pending);
    return pending;
  }
  open(topic, query, ttl) { return this.request(`https://api.openf1.org/v1/${topic}?${new URLSearchParams(query)}`, { ttl }); }
  async season(year) {
    const results = await Promise.allSettled(['', '/driverStandings', '/constructorStandings'].map(path => this.request(`https://api.jolpi.ca/ergast/f1/${year}${path}.json?limit=100`, { source: 'Jolpica', ttl: 3600000 })));
    return Object.fromEntries(results.map((r, i) => [['calendar', 'drivers', 'constructors'][i], r.status === 'fulfilled' ? r.value : { source: 'Jolpica', data: null, stale: true, error: r.reason.message }]));
  }
  async data(topic, query) {
    const ttl = ['meetings', 'sessions'].includes(topic) ? 300000 : ['car_data', 'location'].includes(topic) ? 3600000 : 60000;
    const payload = await this.open(topic, query, ttl);
    const streamed = this.liveRows.get(`${query.session_key}:${topic}`) ?? [];
    // Only unfiltered session requests receive the live overlay.
    if (Object.keys(query).length === 1 && query.session_key && streamed.length) return { ...payload, data: mergeRows(topic, payload.data, streamed), stream_updated_at: this.lastMessageAt };
    return payload;
  }
  ingest(topic, rows) {
    if (!TOPICS.includes(topic)) return;
    for (const row of Array.isArray(rows) ? rows : [rows]) {
      if (!row || typeof row !== 'object' || !row.session_key) continue;
      const key = `${row.session_key}:${topic}`;
      if (['location', 'car_data'].includes(topic)) {
        const previous = this.liveRows.get(key) ?? [];
        const old = previous.find(r => r.driver_number === row.driver_number);
        if (!old || Date.parse(row.date) >= Date.parse(old.date)) this.liveRows.set(key, [...previous.filter(r => r.driver_number !== row.driver_number), row]);
      } else this.liveRows.set(key, mergeRows(topic, this.liveRows.get(key) ?? [], [row]));
      while (this.liveRows.size > 54) this.liveRows.delete(this.liveRows.keys().next().value);
      this.lastMessageAt = iso(this.now());
      this.sessionReceived.set(String(row.session_key), this.lastMessageAt);
      while (this.sessionReceived.size > 10) this.sessionReceived.delete(this.sessionReceived.keys().next().value);
      this.emit('data', { topic, data: row, received_at: this.lastMessageAt });
    }
  }
  async startLive() {
    if (!this.configured || this.env.OPENF1_LIVE_ENABLED !== 'true' || this.client || this.starting) return;
    this.starting = true; this.connection = 'connecting';
    try {
      const token = await this.accessToken();
      this.client = this.mqttConnect('mqtts://mqtt.openf1.org:8883', { username: this.env.OPENF1_USERNAME, password: token, reconnectPeriod: 5000, connectTimeout: 15000 });
      this.client.on('connect', () => { this.connection = 'connected'; this.client.subscribe(TOPICS.map(t => `v1/${t}`), error => { if (error) this.connection = 'error'; }); });
      this.client.on('message', (topic, payload) => { try { this.ingest(topic.replace('v1/', ''), JSON.parse(payload.toString())); } catch { /* malformed provider packet */ } });
      this.client.on('error', () => { this.connection = 'error'; });
      this.client.on('offline', () => { this.connection = 'reconnecting'; });
      // Recreate the socket before token expiry; bootstrap REST remains available on reconnect.
      this.refreshTimer = setTimeout(() => { this.stopLive(); this.startLive(); }, Math.max(1000, this.tokenExpiry - this.now() - 90000));
      this.refreshTimer.unref?.();
    } catch { this.connection = 'authentication-error'; }
    finally { this.starting = false; }
  }
  stopLive() { clearTimeout(this.refreshTimer); this.client?.end(true); this.client = null; this.connection = 'disabled'; }
}

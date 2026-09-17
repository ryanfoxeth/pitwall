import { deviceFeed } from '../lib/pitwall-device.js';
import express from 'express';
import { timingSafeEqual } from 'node:crypto';
import { PitwallService, TOPICS, FeedError } from '../lib/pitwall.js';
export function matchesKey(value, expected) {
  if (!value || !expected || typeof value !== 'string') return false;
  const a = Buffer.from(value), b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}
export function authorizePitwall(req, key = process.env.PITWALL_KEY, masterKey = undefined) {
  return (req.session?.pitwallUntil > Date.now()) || (matchesKey(req.get('x-api-key'), key) || matchesKey(req.get('x-api-key'), masterKey));
}
export function validateQuery(topic, input) {
  if (!TOPICS.includes(topic)) throw new FeedError('Unknown data feed.', 404);
  const out = {};
  const numeric = ['session_key', 'meeting_key', 'driver_number', 'year', 'lap_number'];
  for (const [key, value] of Object.entries(input)) {
    if (typeof value !== 'string') throw new FeedError('Use one value per filter.', 400);
    if (numeric.includes(key) && /^\d{1,6}$/.test(value)) out[key] = value;
    else if (['date>', 'date<'].includes(key) && /^\d{4}-\d{2}-\d{2}T/.test(value) && Number.isFinite(Date.parse(value))) out[key] = new Date(value).toISOString();
    else throw new FeedError(`Unsupported filter: ${key}`, 400);
  }
  if (['meetings', 'sessions'].includes(topic)) {
    if (!out.year && !out.meeting_key && !out.session_key) throw new FeedError('Choose a year, meeting or session.', 400);
  } else if (!out.session_key) throw new FeedError('A numeric session_key is required.', 400);
  if (['car_data', 'location', 'intervals', 'position'].includes(topic)) {
    const start = Date.parse(out['date>']), end = Date.parse(out['date<']);
    const max = ['car_data', 'location'].includes(topic) ? 300000 : 14400000;
    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start || end - start > max) throw new FeedError(`Choose a time window of at most ${max / 60000} minutes.`, 400);
    if (topic === 'car_data' && !out.driver_number) throw new FeedError('Choose a driver for telemetry.', 400);
  }
  return out;
}
export default function makePitwallRouter({ service = new PitwallService(), key = process.env.PITWALL_KEY } = {}) {
  const router = express.Router();
  router.use((_req, res, next) => { res.set('Cache-Control', 'private, no-store'); next(); });
  const snapshot = deviceFeed(service);
  router.get('/device', async (req,res,next)=>{
    const deviceKey=req.get('Authorization')?.replace(/^Bearer /,'');
    if(!authorizePitwall(req,key)&&!matchesKey(deviceKey,process.env.PITWALL_DEVICE_KEY))return res.status(401).json({error:'Device pairing required.'});
    if(req.query.session_key&&!/^\d{1,6}$/.test(req.query.session_key))return res.status(400).json({error:'Invalid session.'});
    try{const data=await snapshot(req.query.session_key);if(req.query.compact==='1')delete data.feeds;res.json(data);}catch(e){next(e);}
  });
  router.post('/auth' , express.json({ limit: '2kb' }), (req, res) => {
    if (!matchesKey(req.body?.key, key)) return res.status(401).json({ error: 'That server access key was not accepted.' });
    if (!req.session) return res.status(503).json({ error: 'Session storage unavailable.' });
    req.session.regenerate(error => {
      if (error) return res.status(503).json({ error: 'Session storage unavailable.' });
      req.session.pitwallUntil = Date.now() + 43200000;
      req.session.save(error => error ? res.status(503).json({ error: 'Session storage unavailable.' }) : res.json({ authenticated: true }));
    });
  });
  router.use((req, res, next) => authorizePitwall(req, key) ? next() : res.status(401).json({ error: 'Unlock Pitwall with your server access key.' }));
  router.post('/logout', (req, res) => { if (req.session) delete req.session.pitwallUntil; res.json({ authenticated: false }); });
  const handle = fn => async (req, res, next) => { try { await fn(req, res); } catch (e) { next(e); } };
  router.get('/status', (_req, res) => res.json({ name: 'Pitwall', version: 1, feeds: TOPICS, live: service.status() }));
  router.get('/season/:year', handle(async (req, res) => {
    const year = Number(req.params.year);
    if (!Number.isInteger(year) || year < 1950 || year > new Date().getFullYear() + 1) throw new FeedError('Invalid season.', 400);
    res.json(await service.season(year));
  }));
  router.get('/data/:topic', handle(async (req, res) => res.json(await service.data(req.params.topic, validateQuery(req.params.topic, req.query)))));
  router.get('/stream', handle(async (req, res) => {
    if (!/^\d{1,6}$/.test(req.query.session_key ?? '')) throw new FeedError('Choose a numeric session_key.', 400);
    if (service.listenerCount('data') >= 10) throw new FeedError('Too many live viewers.', 429);
    await service.startLive();
    res.set({ 'Content-Type': 'text/event-stream', 'Connection': 'keep-alive', 'X-Accel-Buffering': 'no' }); res.flushHeaders();
    const send = (event, data) => { if (!res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`)) res.end(); };
    send('status', service.status(req.query.session_key));
    const listener = event => { if (String(event.data.session_key) === req.query.session_key) send('update', event); };
    service.on('data', listener);
    const timer = setInterval(() => send('status', service.status(req.query.session_key)), 15000);
    req.on('close', () => { clearInterval(timer); service.off('data', listener); });
  }));
  router.use((error, _req, res, _next) => res.status(error.status || 503).json({ error: error instanceof FeedError ? error.message : 'Pitwall could not complete that request.' }));
  return router;
}

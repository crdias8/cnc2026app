/* Service worker — Programação CNC 2026
   Estratégia: a página sempre busca primeiro a versão mais nova na internet;
   só usa a cópia salva quando não há conexão (ou a rede demora demais).
   VERSION é trocada a cada publicação (preenchida pelo build). */
const VERSION = 'e1c2269604';
const KILL = false; // true = remove o modo offline dos aparelhos na próxima abertura com internet
const CACHE = 'cnc2026-' + VERSION;
const CORE = ['./', './index.html', './manifest.webmanifest',
  './assets/icon-192.png', './assets/icon-512.png', './assets/apple-touch-icon.png', './assets/favicon-32.png'];

self.addEventListener('install', e => {
  self.skipWaiting();
  if (KILL) return;
  e.waitUntil(caches.open(CACHE).then(async c => { await c.addAll(CORE.map(u => new Request(u, { cache: 'reload' }))); await c.put('./__saved_at', new Response(String(Date.now()))); }).catch(() => {}));
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k.startsWith('cnc2026-') && (KILL || k !== CACHE)).map(k => caches.delete(k)));
    if (KILL) { await self.registration.unregister(); return; }
    await self.clients.claim();
  })());
});

function timeout(ms) { return new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), ms)); }

self.addEventListener('fetch', e => {
  if (KILL) return;
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const base = new URL(self.registration.scope);
  // Só a página do app (raiz do escopo) — nunca PDFs, a pasta /teste/ ou outros endereços
  const isAppPage = url.origin === base.origin && (url.pathname === base.pathname || url.pathname === base.pathname + 'index.html');

  // Página do app: rede primeiro (até 6 s), depois cópia salva
  if (isAppPage) {
    e.respondWith((async () => {
      try {
        const fresh = await Promise.race([fetch(req, { cache: 'no-store' }), timeout(6000)]);
        if (fresh && fresh.ok) {
          const c = await caches.open(CACHE);
          c.put('./index.html', fresh.clone());
          c.put('./__saved_at', new Response(String(Date.now()), { headers: { 'Content-Type': 'text/plain' } }));
          return fresh;
        }
        throw new Error('bad response');
      } catch (err) {
        const cached = await caches.match('./index.html') || await caches.match('./');
        return cached || new Response('<h1>Sem conexão</h1><p>Abra o app uma vez com internet para guardar a programação.</p>', { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
      }
    })());
    return;
  }

  // Ícones e arquivos do próprio app, e fontes do Google: usa a cópia e atualiza em segundo plano
  if (req.mode === 'navigate') return; // outras páginas/arquivos abrem normalmente, sem passar pelo modo offline
  const sameOrigin = url.origin === base.origin && (url.pathname.startsWith(base.pathname + 'assets/') || url.pathname === base.pathname + 'manifest.webmanifest');
  const fonts = url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com';
  if (sameOrigin || fonts) {
    e.respondWith((async () => {
      const c = await caches.open(CACHE);
      const cached = await c.match(req);
      const net = fetch(req).then(r => { if (r && (r.ok || r.type === 'opaque')) c.put(req, r.clone()); return r; }).catch(() => null);
      return cached || (await net) || new Response('', { status: 504 });
    })());
  }
});

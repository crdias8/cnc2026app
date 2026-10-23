"""Busca as estatísticas anônimas do GoatCounter (cnc2026) e grava painel/stats.json.
Roda no GitHub Actions a cada 30 min. A chave fica no segredo GOATCOUNTER_TOKEN (nunca no site)."""
import json, os, sys, time, subprocess, urllib.request, urllib.error, urllib.parse, datetime as dt

SITE = 'https://cnc2026.goatcounter.com/api/v0'
START = '2026-10-23T00:00:00Z'          # início da contagem
OUT = os.path.join(os.path.dirname(__file__), '..', 'painel', 'stats.json')
TOKEN = os.environ.get('GOATCOUNTER_TOKEN', '').strip()
DEBUG = []

def now_iso():
    n = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0) + dt.timedelta(hours=1)
    return n.strftime('%Y-%m-%dT%H:%M:%SZ')

def get(path, **params):
    q = []
    for k, v in params.items():
        if isinstance(v, (list, tuple)):
            q += [(k, str(x)) for x in v]
        elif v is not None:
            q.append((k, str(v)))
    url = SITE + path + ('?' + urllib.parse.urlencode(q) if q else '')
    # usa o curl (mais tolerante a quedas de conexão) com novas tentativas automáticas
    hdr = os.path.join(os.environ.get('RUNNER_TEMP', '/tmp'), 'gc_headers.txt')
    with open(hdr, 'w') as f:
        f.write('Authorization: Bearer ' + TOKEN + '\nAccept: application/json\nUser-Agent: cnc2026-painel/1.0\n')
    time.sleep(0.3)  # limite da API: 4 pedidos por segundo
    r = subprocess.run(['curl', '-sS', '--http1.1', '--retry', '5', '--retry-all-errors', '--retry-delay', '4', '--max-time', '40',
                        '-H', '@' + hdr, '-w', '\n%{http_code}', url], capture_output=True, text=True)
    body, _, code = r.stdout.rpartition('\n')
    code = int(code) if code.isdigit() else 0
    if r.returncode != 0 or code >= 400 or code == 0:
        DEBUG.append({'path': path, 'code': code, 'curl': r.returncode, 'err': r.stderr[-200:], 'body': body[:200]})
        print('falha', path, code, r.returncode, r.stderr[-200:], body[:200])
        raise RuntimeError('http-%d' % code if code else 'conexao')
    return json.loads(body)

def main():
    out = {'fetched_at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'start': START}
    if not TOKEN:
        out['error'] = 'sem-chave'
    else:
        try:
            end = now_iso()
            out['end'] = end
            tot = get('/stats/total', start=START, end=end)
            out['total'] = {'total': tot.get('total'), 'events': tot.get('total_events'),
                            'days': [{'day': s.get('day'), 'hourly': s.get('hourly') or [], 'daily': s.get('daily')} for s in tot.get('stats') or []]}
            hits, seen, ok = [], [], False
            for lim in (100, 25, 10):
                try:
                    hits, seen = [], []
                    for _ in range(40):
                        h = get('/stats/hits', start=START, end=end, limit=lim, exclude_paths=seen or None)
                        for x in h.get('hits') or []:
                            seen.append(x.get('path_id'))
                            hits.append({'path': x.get('path'), 'title': x.get('title'), 'event': bool(x.get('event')), 'count': x.get('count'),
                                         'days': [{'day': s.get('day'), 'daily': s.get('daily'), 'hourly': s.get('hourly') or []} for s in x.get('stats') or []]})
                        if not h.get('more'): break
                    ok = True; break
                except Exception as e:
                    print('hits falhou com limit', lim, e)
            if ok:
                out['hits'] = hits
            else:
                old = {}
                try: old = json.load(open(OUT))
                except Exception: pass
                out['hits'] = old.get('hits', [])
                out['hits_stale'] = True
            for page in ('browsers', 'systems', 'locations', 'sizes', 'toprefs'):
                try:
                    s = get('/stats/' + page, start=START, end=end, limit=25)
                    out[page] = [{'id': x.get('id'), 'name': x.get('name'), 'count': x.get('count')} for x in s.get('stats') or []]
                except Exception as e:
                    out[page] = []
            br = next((x for x in out.get('locations', []) if (x.get('id') or '').upper() == 'BR'), None)
            if br:
                try:
                    s = get('/stats/locations/BR', start=START, end=end, limit=30)
                    out['regions_br'] = [{'id': x.get('id'), 'name': x.get('name'), 'count': x.get('count')} for x in s.get('stats') or []]
                except Exception:
                    out['regions_br'] = []
        except urllib.error.HTTPError as e:
            out['error'] = 'http-%d' % e.code
            out['debug'] = DEBUG
        except Exception as e:
            out['error'] = 'falha: ' + str(e)
            out['debug'] = DEBUG
    # mantém os últimos dados bons se esta busca falhar
    if out.get('error') and os.path.exists(OUT):
        try:
            old = json.load(open(OUT))
            if not old.get('error'):
                old['last_error'] = out['error']; old['last_try'] = out['fetched_at']; old['last_debug'] = out.get('debug')
                out = old
        except Exception:
            pass
    json.dump(out, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
    print('ok' if not out.get('error') else out['error'], len(out.get('hits', [])), 'caminhos')

if __name__ == '__main__':
    main()

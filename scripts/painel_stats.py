"""Busca as estatísticas anônimas do GoatCounter (cnc2026) e grava painel/stats.json.
Roda no GitHub Actions a cada 30 min. A chave fica no segredo GOATCOUNTER_TOKEN (nunca no site)."""
import json, os, sys, urllib.request, urllib.error, urllib.parse, datetime as dt

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
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read()[:300].decode('utf-8', 'replace')
        DEBUG.append({'path': path, 'code': e.code, 'body': body})
        print('HTTP', e.code, path, body)
        raise

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
            hits, seen = [], []
            for _ in range(15):
                h = get('/stats/hits', start=START, end=end, limit=100, exclude_paths=seen or None)
                for x in h.get('hits') or []:
                    seen.append(x.get('path_id'))
                    hits.append({'path': x.get('path'), 'title': x.get('title'), 'event': bool(x.get('event')), 'count': x.get('count'),
                                 'days': [{'day': s.get('day'), 'daily': s.get('daily'), 'hourly': s.get('hourly') or []} for s in x.get('stats') or []]})
                if not h.get('more'): break
            out['hits'] = hits
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
                    out['regions_br'] = [{'name': x.get('name'), 'count': x.get('count')} for x in s.get('stats') or []]
                except Exception:
                    out['regions_br'] = []
        except urllib.error.HTTPError as e:
            out['error'] = 'http-%d' % e.code
            out['debug'] = DEBUG
        except Exception as e:
            out['error'] = 'falha: ' + type(e).__name__
    # mantém os últimos dados bons se esta busca falhar
    if out.get('error') and os.path.exists(OUT):
        try:
            old = json.load(open(OUT))
            if not old.get('error'):
                old['last_error'] = out['error']; old['last_try'] = out['fetched_at']
                out = old
        except Exception:
            pass
    json.dump(out, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
    print('ok' if not out.get('error') else out['error'], len(out.get('hits', [])), 'caminhos')

if __name__ == '__main__':
    main()

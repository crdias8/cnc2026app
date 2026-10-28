"""PDF da programação de um dia, sem pôsteres, no formato aprovado em 28/10/2026.
uso: python3 /home/claude/cnc/pdf_dia/gerar_pdf_dia.py <dia>   (ex.: 29)
Gera /home/claude/cnc/Programacao_CNC2026_<dia>-10_sem_posteres.pdf a partir da programação atual
(rode antes o build.py se data.js tiver mudado). Etiquetas: as mesmas do app (tagHTML), fonte Oswald."""
import json,re,sys,html,base64,subprocess,datetime,os
D=os.path.dirname(os.path.abspath(__file__)); dia=int(sys.argv[1])
WD={27:'terça-feira',28:'quarta-feira',29:'quinta-feira',30:'sexta-feira'}
tmp=f'/tmp/pdfdia_{dia}'; os.makedirs(tmp,exist_ok=True)
subprocess.run(['node',D+'/dump.js',str(dia),tmp+'/ev.json'],check=True)
J=json.load(open(tmp+'/ev.json')); d=J['ev']; ORDER=J['order']
logo=open(D+'/logo.txt').read().strip()
osw=base64.b64encode(open(D+'/Oswald.ttf','rb').read()).decode()
def fmt(t):
    t=html.escape(t)
    t=re.sub(r'\[\[(.+?)\|(.+?)\]\]',lambda m:f'<a href="{m.group(2)}">{m.group(1)}</a>',t)
    return re.sub(r'\*(.+?)\*',r'<i>\1</i>',t)
d.sort(key=lambda e:(e['s'],ORDER.index(e['room']) if e['room'] in ORDER else 99))
rows=[];cur=None
for e in d:
    if e['type']=='B':
        rows.append(f'<tr class="brk"><td class="h">{e["s"]}–{e["e"]}</td><td colspan="2">{fmt(e["title"])}</td></tr>'); cur=None; continue
    if e['s']!=cur:
        cur=e['s']; rows.append(f'<tr class="slot"><td colspan="3">{e["s"]}</td></tr>')
    hora=f'a partir das {e["s"]}' if 'o' in e['flags'] else f'{e["s"]}–{e["e"]}'
    tt='<br>'.join(f'<b>{fmt(x)}</b>' for x in e['title'].split(';;'))
    tags=[e['tl']]
    if 'r' in e['flags']: tags.append('participação remota')
    if 'l' in e['flags']: tags.append('com legendas')
    if 'n' in e['flags']: tags.append('levar notebook')
    ppl=' · '.join(fmt(p) for p in e['people'] if p)
    rows.append(f'<tr><td class="h">{hora}</td><td><div class="tg">{e["tag"]}<span class="ty">{" · ".join(tags)}</span></div>{tt}'+(f'<div class="ppl">{ppl}</div>' if ppl else '')+f'</td><td class="loc">{html.escape(e["rn"])}</td></tr>')
n=sum(1 for e in d if e['type']!='B')
agora=(datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(hours=3)).strftime('%d/%m/%Y às %H:%M')
css=open(D+'/estilo.css').read()
H=f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>
@font-face{{font-family:"Oswald";src:url(data:font/ttf;base64,{osw}) format("truetype");font-weight:200 700}}
{css}</style></head><body>
<div class="top"><img src="{logo}"><div class="t">XXVIII Congresso Nacional de Criminalística<br>27 a 30 de outubro de 2026 · Gramado/RS</div></div>
<h1>Programação de {WD[dia]}, {dia}/10</h1>
<p class="sub">Programação completa do dia, sem as sessões de pôsteres ({n} atividades). Versão do app de {agora}.</p>
<table><thead><tr><th style="width:13%">Horário</th><th>Atividade</th><th>Local</th></tr></thead><tbody>{"".join(rows)}</tbody></table>
<p class="foot">Fonte: app da programação do CNC 2026 (crdias8.github.io/cnc2026app). Horários de Brasília; sujeitos a alteração.</p>
</body></html>'''
open(tmp+'/dia.html','w').write(H)
out=f'/home/claude/cnc/Programacao_CNC2026_{dia}-10_sem_posteres.pdf'
subprocess.run(['node',D+'/pdf.js',tmp+'/dia.html',out,str(dia)],check=True); print(out, n)

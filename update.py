#!/usr/bin/env python3
"""One-shot daily update: run the 3 existing market pipelines (they still push their own repos),
then copy 儀表板 data + strategy signals into asia-breadth and push. Prints a Cantonese summary.
Usage: python3 update.py [--no-refresh] [--no-push] [--only hk,jp,au]"""
import subprocess, sys, json, re, csv, time, pathlib, datetime
W = pathlib.Path('/workspace'); HERE = pathlib.Path(__file__).resolve().parent
MK = {  # repo, refresh cmd, signal script, column map
 'hk': ('hk-breadth', ['bash','scripts/update_all.sh'], 'scripts/t2108_signal.py', {'hsi':'idx','hsi_chg_pct':'idx_chg_pct','tracker_etf':'etf','tracker_etf_chg_pct':'etf_chg_pct'}, '港股', '恒指'),
 'jp': ('jp-breadth', ['bash','scripts/update_all.sh'], 'scripts/t2108_signal.py', {'nikkei225':'idx','nikkei225_chg_pct':'idx_chg_pct','topix_etf':'etf','topix_etf_chg_pct':'etf_chg_pct'}, '日股', '日經'),
 'au': ('au-breadth', ['bash','run_daily.sh'], 'scripts/strategy_signal.py', {'asx200':'idx','asx200_chg_pct':'idx_chg_pct','asx200_etf':'etf','asx200_etf_chg_pct':'etf_chg_pct'}, '澳股', 'ASX200'),
}
args = sys.argv[1:]
only = args[args.index('--only')+1].split(',') if '--only' in args else list(MK)
t0 = time.time(); status = {}
for m in only:
    repo, cmd = MK[m][0], MK[m][1]
    if '--no-refresh' in args: break
    t = time.time(); print(f'== refresh {m}', flush=True)
    r = subprocess.run(cmd, cwd=W/repo, stdin=subprocess.DEVNULL)
    status[m] = f'exit {r.returncode} in {time.time()-t:.0f}s'; print(status[m], flush=True)

def signal(m):
    repo, _, script = MK[m][:3]
    out = subprocess.run([str(W/repo/'.venv/bin/python'), script], cwd=W/repo, capture_output=True, text=True).stdout
    if m == 'au':
        ev = re.search(r'Signal today: (\w+)', out).group(1)
        if 'HOLDING' in out:
            g = re.search(r'since (\S+) .*P/L ([+-][\d.]+)%; sell when T2108 > (\d+)', out)
            st, tx = '持倉', f'{g[1]} 買入，ASX200 {g[2]}%；T2108 > {g[3]} 賣出'
        elif 'armed' in out:
            g = re.search(r'low ([\d.]+)\); buy when T2108 >= ([\d.]+)', out); st, tx = '準備', f'低位 {g[1]}，T2108 ≥ {g[2]} 買入'
        else: st, tx = '觀望', '等 T2108 < 30'
    else:
        ev = 'BUY' if 'EVENT=BUY' in out else 'SELL' if 'EVENT=SELL' in out else 'none'
        st0 = re.search(r'state=(\w+)', out).group(1)
        if st0 == 'HOLD':
            g = re.search(r'holding since (\S+).*?_ret=([+-][\d.]+)%', out); sell = '60' if m == 'hk' else '70'
            st, tx = '持倉', f'{g[1]} 買入，{MK[m][5]} {g[2]}%；T2108 > {sell} 賣出'
        elif st0 == 'ARMED':
            if m == 'hk': g = re.search(r'low=([\d.]+)', out); st, tx = '準備', f'低位 {g[1]}，T2108 重上 20 買入'
            else: g = re.search(r'low=([\d.]+) buy_trigger>=([\d.]+)', out); st, tx = '準備', f'低位 {g[1]}，T2108 ≥ {g[2]} 買入'
        else: st, tx = '觀望', '等 T2108 < ' + ('20' if m == 'hk' else '30')
    if ev != 'none': st = ('今日買入' if ev == 'BUY' else '今日賣出'); 
    return {'state': st, 'text': tx, 'event': ev, 'raw': out.strip()}

sig, summ = {}, []
for m in MK:
    repo, colmap = MK[m][0], MK[m][3]
    rows = list(csv.reader(open(W/repo/'data/breadth.csv')))
    hdr = [colmap.get(h, h) for h in rows[0]]
    with open(HERE/'data'/f'{m}.csv', 'w', newline='') as f: csv.writer(f).writerows([hdr] + rows[1:])
    last = dict(zip(hdr, rows[-1])); s = signal(m); s['date'] = last['Date']; sig[m] = s
    f2 = lambda k, d: f"{float(last[k]):,.{d}f}"
    summ.append(f"{MK[m][4]}（{last['Date']}）：升4% {last['up4']}／跌4% {last['down4']}｜5日比 {f2('ratio5',2)}｜10日比 {f2('ratio10',2)}｜T2108 {f2('t2108',1)}｜{MK[m][5]} {f2('idx',1 if m=='au' else 0)}（{float(last['idx_chg_pct']):+.2f}%）。策略：{s['state']}，{s['text']}")
sig['updated'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M HKT')
json.dump(sig, open(HERE/'data/signals.json', 'w'), ensure_ascii=False, indent=1)
subprocess.run([sys.executable, 'build_page.py'], cwd=HERE, check=True)
if '--no-push' not in args:
    subprocess.run(['git', 'add', '-A', 'index.html', 'data', 'build_page.py', 'update.py', 'README.md'], cwd=HERE)
    if subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=HERE).returncode:
        subprocess.run(['git', 'commit', '-qm', 'update ' + sig['updated']], cwd=HERE, check=True)
        subprocess.run(['git', 'push', '-q', 'origin', 'HEAD:main'], cwd=HERE, check=True)
print('\n'.join(['== SUMMARY'] + summ + [f'頁面：https://nick-l-wh.github.io/asia-breadth/', f'refresh: {status}', f'total {time.time()-t0:.0f}s']))

# Builds index.html from jp-breadth/index.html template (儀表板 only, no 52-week highs)
import re,pathlib
src=pathlib.Path('/workspace/jp-breadth/index.html').read_text()
s=src.replace('<title>日本市場廣度監測</title>','<title>亞洲市場廣度儀表板（港／日／澳）</title>')
s=s.replace('<nav class="nav" aria-label="頁面"><a href="./" aria-current="page">市場廣度</a><a href="highs.html">52 週新高</a></nav>',
 '<nav class="nav" aria-label="市場" id="mk"><a href="#hk" data-m="hk">港股</a><a href="#jp" data-m="jp">日股</a><a href="#au" data-m="au">澳股</a></nav>')
s=s.replace('<h1>日本市場廣度監測</h1>','<h1 id="ttl">市場廣度儀表板</h1>')
s=re.sub(r'<p>股票池：.*?</p>','<p id="uni"></p>',s,count=1)
s=s.replace('若直接雙擊開啟檔案，瀏覽器會擋住讀取；請用 GitHub Pages 網址，或在專案資料夾執行 view_local.bat。','請用 GitHub Pages 網址開啟。')
s=s.replace('["nikkei225", "日經225", 0], ["nikkei225_chg_pct", "日經%", 2], ["topix_etf_chg_pct", "TOPIX%", 2]','["idx", M().short, 0], ["idx_chg_pct", M().short + "%", 2], ["etf_chg_pct", M().etf + "%", 2]')
s=s.replace('"nikkei225_chg_pct","topix_etf","topix_etf_chg_pct"','"idx_chg_pct","etf","etf_chg_pct"').replace('"nikkei225"','"idx"')
s=s.replace('k: "nikkei225"','k: "idx"').replace('!== "nikkei225"','!== "idx"')
s=s.replace('["nikkei225", "日經225", 0], ["nikkei225_chg_pct", "日經%", 2], ["topix_etf_chg_pct", "TOPIX%", 2]',
 '["idx", M().short, 0], ["idx_chg_pct", M().short + "%", 2], ["etf_chg_pct", M().etf + "%", 2]')
s=s.replace('{ title: "日經 225（對照）", kind: "line", yfmt: v => fmt(v), series: [{ k: "idx", label: "日經 225", c: "--text2" }] },',
 '{ title: "IDX（對照）", kind: "line", yfmt: v => fmt(v), series: [{ k: "idx", label: "IDX", c: "--text2" }] },')
s=s.replace('fetch("data/breadth.csv?v="','fetch("data/" + MK + ".csv?v="').replace('無法讀取 data/breadth.csv','無法讀取資料')
s=s.replace('" 隻（20 日均成交金額 ≥ ¥1,000 萬）　｜　共 "','" 隻（" + M().liq + "）　｜　共 "')
s=s.replace('["T2108（高於 40 日線 %）", fmt(a.t2108, 1), `前日 ${fmt(b.t2108, 1)}`],',
 '''["T2108（高於 40 日線 %）", fmt(a.t2108, 1), `前日 ${fmt(b.t2108, 1)}`],
    [M().name + "收市", fmt(a.idx, M().dp), `<span class="${a.idx_chg_pct >= 0 ? "u" : "d"}">${a.idx_chg_pct >= 0 ? "+" : ""}${fmt(a.idx_chg_pct, 2)}%</span>`],
    ["T2108 策略", (SIG[MK] || {}).state || "–", (SIG[MK] || {}).text || ""],''')
s=s.replace('.tile .v .u { color: var(--up); }','.tile .v .u, .tile .p .u { color: var(--up); } .tile .p .d { color: var(--down); }')
cfg='''
const MKS = {
  hk: { ttl: "香港市場廣度儀表板", name: "恒指", short: "恒指", etf: "盈富", dp: 0, liq: "20 日均成交金額 ≥ HK$50 萬",
        uni: "股票池：港交所主板及 GEM 普通股（港幣櫃台），排除 ETF、槓桿反向產品、REIT、牛熊證、窩輪、債券、優先股及人民幣櫃台；再以 20 日平均成交金額 ≥ 50 萬港元過濾。策略：T2108 跌穿 20 後重上 20 買入，T2108 > 60 賣出。" },
  jp: { ttl: "日本市場廣度儀表板", name: "日經", short: "日經225", etf: "TOPIX", dp: 0, liq: "20 日均成交金額 ≥ ¥1,000 萬",
        uni: "股票池：東證 Prime、Standard、Growth 內國普通股，排除 ETF、REIT、PRO Market；再以 20 日平均成交金額 ≥ 1,000 萬日圓過濾。策略：T2108 < 30 後由低位回升 3 點買入（須 < 70），T2108 > 70 賣出。" },
  au: { ttl: "澳洲市場廣度儀表板", name: "ASX200", short: "ASX200", etf: "STW", dp: 1, liq: "收市價 ≥ A$0.40 且 20 日均成交金額 ≥ A$10 萬",
        uni: "股票池：ASX 上市普通股（排除 ETF、基金、信託、混合證券與權證），收市價 ≥ A$0.40 且 20 日平均成交金額 ≥ A$10 萬。策略：T2108 < 30 後由低位回升 3 點買入，T2108 > 70 賣出。" },
};
let MK = (location.hash || "#hk").slice(1); if (!MKS[MK]) MK = "hk";
const M = () => MKS[MK];
let SIG = {};
async function loadSig() { try { SIG = await (await fetch("data/signals.json?v=" + Date.now())).json(); } catch (e) {} }
function setMk(m) {
  MK = m; history.replaceState(null, "", "#" + m);
  document.querySelectorAll("#mk a").forEach(a => a.setAttribute("aria-current", a.dataset.m === m ? "page" : "false"));
  $("#ttl").textContent = M().ttl; $("#uni").textContent = M().uni;
  CH[CH.length - 1].title = M().name + "（對照）"; CH[CH.length - 1].series[0].label = M().name;
  $("#err").style.display = "none"; load();
}
document.querySelectorAll("#mk a").forEach(a => a.onclick = e => { e.preventDefault(); setMk(a.dataset.m); });
'''
s=s.replace('let D = [];',cfg+'let D = [];',1)
s=s.replace('\nload();\n','\nloadSig().then(() => setMk(MK));\n')
pathlib.Path('index.html').write_text(s)
for k in ['nikkei','highs.html','topix']: assert k not in s, k

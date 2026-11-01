// BUNKER 2.0 README art — hero, terminal, seal diagram. Dark + light. Fonts are Geist (SIL OFL 1.1) subsets embedded as woff2.
import fs from 'node:fs';
import { execFileSync } from 'node:child_process';

const OUT = '..';   // run from docs/readme/source: npm i geist@1.3.1 && pip install fonttools brotli && node gen.mjs
const FD = 'node_modules/geist/dist/fonts';
const P = {
  dark:  { bg:'#080B13', card:'#0C111D', ink:'#F1F3F7', dim:'#A9B1C0', faint:'#6E7787', line:'#1C2333', steel:'#141B2A', steel2:'#1D2638', accent:'#F0B44C', glow:'#FFF4DC' },
  light: { bg:'#F5F6F9', card:'#FFFFFF', ink:'#0B0F17', dim:'#4A5466', faint:'#8A93A3', line:'#D8DDE6', steel:'#E7EAF0', steel2:'#D6DBE4', accent:'#B57A12', glow:'#0B0F17' },
};

const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

function subset(file, text) {
  fs.writeFileSync('/tmp/glyphs.txt', text + ' ');
  execFileSync('pyftsubset', [file, '--text-file=/tmp/glyphs.txt', '--flavor=woff2', '--output-file=/tmp/sub.woff2', '--name-IDs=*', '--name-legacy', '--layout-features=kern']);
  return fs.readFileSync('/tmp/sub.woff2').toString('base64');
}
function fontCSS(fam, file, text) { return `@font-face{font-family:'${fam}';src:url(data:font/woff2;base64,${subset(file, text)}) format('woff2');}`; }

/* ---------------- HERO: the login-screen bunker, redrawn in vector ---------------- */
function hero(m) {
  const c = P[m], W = 1280, H = 540, G = 336;   // G = ground line
  const dark = m === 'dark';
  const S = dark
    ? { far:'#111827', farEdge:'#1E2838', near:'#0D1320', nearEdge:'#1A2333', snow:'#D3D9E2', con:'#1A2232', con2:'#232D40', conEdge:'#2E3A50', red:'#E5534B', beam:'#FFE7B0' }
    : { far:'#DCE1EA', farEdge:'#C6CDD9', near:'#CBD2DE', nearEdge:'#B3BCCB', snow:'#FFFFFF', con:'#B9C1CE', con2:'#A9B2C1', conEdge:'#8E99AB', red:'#C93A31', beam:'#B57A12' };
  const tag = 'YOUR DIGITAL FORTRESS  ·  TERMINAL EDITION';
  const sub = 'Offline password & notes vault  ·  AES-256-GCM  ·  Argon2id  ·  no account  ·  no cloud';
  const css = fontCSS('BkSans', `${FD}/geist-sans/Geist-Medium.woff2`, 'BUNKER2.0' + tag) +
              fontCSS('BkMono', `${FD}/geist-mono/GeistMono-Regular.woff2`, sub + 'B-022PROPERTYOFZEROMARKS LLCKEEP OUT!');
  const stars = [[150,60],[232,118],[300,44],[388,96],[452,30],[470,150],[640,40],[690,96],[760,52],[820,120],[905,38],[960,92],[1040,140],[1110,58],[1180,110],[1215,30],[118,170],[1150,190],[260,200],[700,140],[996,30],[350,160]]
    .map(([x, y], i) => `<circle class="tw" style="animation-delay:${(i * 0.37 % 3.6).toFixed(2)}s" cx="${x}" cy="${y}" r="${i % 4 ? 1.1 : 1.8}" fill="${c.dim}"/>`).join('');
  const dots = Array.from({ length: 117 }, (_, i) => `<circle cx="${118 + i * 9}" cy="${G + 7}" r="2.2" fill="none" stroke="${c.faint}" stroke-width="1"/>`).join('');
  const ribs = Array.from({ length: 22 }, (_, i) => `<line x1="${490 + i * 7}" y1="${G - 34}" x2="${490 + i * 7}" y2="${G - 2}" stroke="${S.conEdge}" stroke-width="1.4"/>`).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="BUNKER 2.0 — a concrete bunker marked B-022 dug into the mountains under a crescent moon, a watchtower sweeping a searchlight, and a sign reading Property of ZeroMarks LLC, Keep Out.">
<title>BUNKER 2.0 — Your Digital Fortress (Terminal Edition)</title>
<defs><style>${css}
.tw{animation:tw 3.6s ease-in-out infinite}@keyframes tw{0%,100%{opacity:.9}50%{opacity:.2}}
.up{transform-box:fill-box;animation:up .9s cubic-bezier(.33,.33,.55,1) both}@keyframes up{from{transform:translateY(28px);opacity:0}to{transform:none;opacity:1}}
.fade{animation:fade .9s both}@keyframes fade{from{opacity:0}to{opacity:1}}
.beam{transform-origin:850px 196px;animation:sweep 7s ease-in-out 1.6s infinite alternate}@keyframes sweep{from{transform:rotate(-14deg)}to{transform:rotate(16deg)}}
.lamp{animation:lamp 2.6s steps(1,end) infinite}@keyframes lamp{0%,72%{opacity:1}73%,100%{opacity:.3}}
.rise{animation:rise .72s 1.5s cubic-bezier(.33,.33,.55,1) both}@keyframes rise{from{transform:translateY(10px);opacity:0}to{transform:none;opacity:1}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
</style>
<radialGradient id="glow" cx="560" cy="86" r="230" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${c.accent}" stop-opacity="${dark ? .2 : .14}"/><stop offset="1" stop-color="${c.accent}" stop-opacity="0"/></radialGradient>
<linearGradient id="beamg" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="${S.beam}" stop-opacity="${dark ? .32 : .22}"/><stop offset="1" stop-color="${S.beam}" stop-opacity="0"/></linearGradient>
<linearGradient id="door" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${c.accent}" stop-opacity=".95"/><stop offset="1" stop-color="${c.accent}" stop-opacity=".35"/></linearGradient>
<mask id="crescent"><rect width="${W}" height="${H}" fill="#fff"/><circle cx="572" cy="78" r="25" fill="#000"/></mask>
</defs>
<rect width="${W}" height="${H}" fill="${c.bg}"/>
<rect width="${W}" height="${G + 20}" fill="url(#glow)"/>
${stars}
<g class="fade" style="animation-delay:.2s"><circle cx="560" cy="86" r="28" fill="${dark ? c.glow : c.accent}" mask="url(#crescent)"/></g>
<g class="up" style="animation-delay:.15s">
  <path d="M300 ${G} L420 200 L470 236 L560 122 L640 212 L700 170 L790 262 L880 ${G} Z" fill="${S.far}" stroke="${S.farEdge}" stroke-width="1.5" stroke-linejoin="round"/>
  <path d="M560 122 L586 154 L572 149 L561 162 L549 147 L535 153 Z M420 200 L438 220 L426 217 L418 226 L404 216 Z M700 170 L722 197 L708 193 L699 203 L688 192 L681 194 Z" fill="${S.snow}" opacity="${dark ? .85 : 1}"/>
</g>
<g class="beam" style="opacity:.95"><path d="M850 196 L120 120 L120 205 Z" fill="url(#beamg)"/></g>
<g class="up" style="animation-delay:.35s">
  <path d="M120 ${G} L245 226 L292 262 L346 216 L430 296 L470 ${G} Z" fill="${S.near}" stroke="${S.nearEdge}" stroke-width="1.5" stroke-linejoin="round"/>
  <path d="M245 226 L263 244 L251 241 L244 250 L231 239 Z M346 216 L364 233 L352 230 L345 239 L331 230 Z" fill="${S.snow}" opacity="${dark ? .8 : 1}"/>
  <path d="M772 ${G} L806 284 L834 302 L858 ${G} Z" fill="${S.near}" stroke="${S.nearEdge}" stroke-width="1.5" stroke-linejoin="round"/>
</g>
<g class="up" style="animation-delay:.6s">
  <path d="M466 ${G - 36} L500 264 L740 264 L770 ${G - 36} Z" fill="${S.con2}" stroke="${S.conEdge}" stroke-width="1.5" stroke-linejoin="round"/>
  <rect x="660" y="252" width="34" height="14" rx="2" fill="${S.con2}" stroke="${S.conEdge}" stroke-width="1.5"/>
  <rect x="476" y="${G - 36}" width="286" height="36" fill="${S.con}" stroke="${S.conEdge}" stroke-width="1.5"/>
  ${ribs}
  <rect x="649" y="${G - 30}" width="44" height="30" rx="3" fill="${dark ? '#05080E' : '#6B7587'}" stroke="${S.conEdge}" stroke-width="1.5"/>
  <rect class="lamp" x="657" y="${G - 26}" width="28" height="3" rx="1.5" fill="url(#door)"/>
  <rect x="535" y="${G - 27}" width="62" height="20" rx="3" fill="${c.bg}" stroke="${S.conEdge}"/>
  <text x="566" y="${G - 12.5}" text-anchor="middle" style="font-family:BkMono;font-size:13px;letter-spacing:1px" fill="${c.accent}">B-022</text>
</g>
<g class="up" style="animation-delay:.85s" fill="none" stroke="${c.dim}" stroke-width="2" stroke-linecap="round">
  <path d="M836 206 L812 ${G} M864 206 L888 ${G} M832 230 L879 ${G - 50} M868 230 L821 ${G - 50} M826 ${G - 50} L874 ${G - 50} M819 ${G - 50} L884 ${G}"/>
  <path d="M822 180 L850 160 L878 180 Z" fill="${S.con2}" stroke="${c.dim}"/>
  <rect x="826" y="180" width="48" height="26" rx="2" fill="${S.con}" stroke="${c.dim}"/>
  <rect class="lamp" x="844" y="186" width="12" height="12" rx="2" fill="${c.accent}" stroke="none" style="animation-delay:1.1s"/>
</g>
<g class="up" style="animation-delay:1.05s">
  <path d="M962 266 L962 ${G} M1068 266 L1068 ${G}" stroke="${c.dim}" stroke-width="3"/>
  <rect x="930" y="186" width="170" height="84" rx="4" fill="${c.card}" stroke="${c.dim}" stroke-width="1.5"/>
  <g text-anchor="middle" style="font-family:BkMono;font-size:12.5px;letter-spacing:1.5px">
    <text x="1015" y="208" fill="${c.ink}">PROPERTY</text><text x="1015" y="225" fill="${c.dim}">OF</text>
    <text x="1015" y="242" fill="${c.accent}">ZEROMARKS LLC</text><text x="1015" y="261" fill="${S.red}" style="font-size:14px;letter-spacing:2px">KEEP OUT!</text>
  </g>
</g>
<line x1="100" y1="${G}" x2="1180" y2="${G}" stroke="${c.line}" stroke-width="1.5"/>
<g class="fade" style="animation-delay:1.2s">${dots}</g>
<g class="rise" text-anchor="middle">
<text x="${W / 2}" y="432" style="font-family:BkSans;font-size:60px;letter-spacing:13px" fill="${c.ink}">BUNKER<tspan fill="${c.accent}" dx="10">2.0</tspan></text>
<text x="${W / 2}" y="468" style="font-family:BkSans;font-size:14px;letter-spacing:4.2px" fill="${c.dim}">${esc(tag)}</text>
<text x="${W / 2}" y="500" style="font-family:BkMono;font-size:13px" fill="${c.faint}">${esc(sub)}</text>
</g>
</svg>`;
}

/* ---------------- TERMINAL ---------------- */
function terminal(m, alt) {
  const c = P[m], W = 1280;
  const lines = alt || [
    ['cmd', 'git clone https://github.com/ZeroMarks/BUNKER2.0 && cd BUNKER2.0'],
    ['cmd', 'pip install -r requirements.txt'],
    ['out', 'argon2-cffi  cryptography  psutil  pyperclip  requests'],
    ['gap'],
    ['cmd', 'python3 -m unittest discover -s tests -t .'],
    ['out', 'OK', 'ok'],
    ['gap'],
    ['cmd', 'python3 BUNKER.py'],
    ['out', '# first run walks you through creating your vault', 'faint'],
  ];
  const top = 58, lh = 30;
  let y = top + 34, t = 0.3, body = '';
  for (const [k, s, tone] of lines) {
    if (k === 'gap') { y += 12; continue; }
    if (k === 'cmd') {
      const dur = Math.min(1.4, 0.25 + s.length * 0.018);
      body += `<g class="ln" style="animation-delay:${t.toFixed(2)}s"><text x="40" y="${y}" fill="${c.accent}">$</text><text x="${40+2*10.21}" y="${y}" fill="${c.ink}" class="type" style="--w:${s.length}ch;animation-delay:${t.toFixed(2)}s;animation-duration:${dur.toFixed(2)}s">${esc(s)}</text></g>`;
      t += dur + 0.35;
    } else {
      body += `<text class="ln" style="animation-delay:${t.toFixed(2)}s" x="40" y="${y}" fill="${tone === 'ok' ? c.accent : tone === 'faint' ? c.faint : c.dim}">${esc(s)}</text>`;
      t += 0.3;
    }
    y += lh;
  }
  const H = y + 18;
  const glyphs = lines.map(l => l[1] || '').join('') + '$ bunker — install#' ;
  const css = fontCSS('BkMono', `${FD}/geist-mono/GeistMono-Regular.woff2`, glyphs);
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Install in a terminal: clone the repo, pip install -r requirements.txt, run the tests, then python3 BUNKER.py to create your vault.">
<title>Install: clone, pip install -r requirements.txt, run the tests, python3 BUNKER.py</title>
<defs><style>${css}
text{font-family:BkMono;font-size:17px;white-space:pre}
.ln{animation:in .2s both}@keyframes in{from{opacity:0}to{opacity:1}}
.type{clip-path:inset(0 100% 0 0);animation:type steps(40,end) both}@keyframes type{to{clip-path:inset(0 0 0 0)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;clip-path:none!important}}
</style></defs>
<rect x="1" y="1" width="${W - 2}" height="${H - 2}" rx="14" fill="${c.card}" stroke="${c.line}"/>
<line x1="1" y1="${top - 14}" x2="${W - 1}" y2="${top - 14}" stroke="${c.line}"/>
${[0, 1, 2].map(i => `<circle cx="${26 + i * 18}" cy="23" r="5" fill="${c.line}"/>`).join('')}
<text x="${W / 2}" y="28" text-anchor="middle" fill="${c.faint}" style="font-size:13px">bunker — install</text>
${body}
</svg>`;
}

/* ---------------- SEAL (security model) ---------------- */
function seal(m) {
  const c = P[m], W = 1280, H = 284;
  const steps = [
    ['Master password', 'never stored', 'ink'],
    ['Argon2id', '100 MiB · 3 passes'],
    ['PBKDF2-SHA3-256', '110,000 rounds'],
    ['256-bit key', 'in memory only'],
    ['AES-256-GCM', 'per field, fresh nonce'],
    ['Bunker.mmf', 'on your disk only', 'accent'],
  ];
  const bw = 172, gap = (W - 80 - bw * steps.length) / (steps.length - 1), y = 96, bh = 104;
  let g = '';
  steps.forEach(([a, b, tone], i) => {
    const x = 40 + i * (bw + gap);
    const stroke = tone === 'accent' ? c.accent : c.line;
    g += `<g class="st" style="animation-delay:${(0.2 + i * 0.22).toFixed(2)}s"><rect x="${x}" y="${y}" width="${bw}" height="${bh}" rx="12" fill="${c.card}" stroke="${stroke}" stroke-width="${tone === 'accent' ? 1.6 : 1}"/>
<text x="${x + bw / 2}" y="${y + 44}" text-anchor="middle" class="h" fill="${tone === 'accent' ? c.accent : c.ink}">${esc(a)}</text>
<text x="${x + bw / 2}" y="${y + 72}" text-anchor="middle" class="s" fill="${c.dim}">${esc(b)}</text></g>`;
    if (i < steps.length - 1) {
      const x1 = x + bw + 6, x2 = x + bw + gap - 6, yy = y + bh / 2;
      g += `<g class="st" style="animation-delay:${(0.3 + i * 0.22).toFixed(2)}s"><line x1="${x1}" y1="${yy}" x2="${x2 - 4}" y2="${yy}" stroke="${c.faint}" stroke-width="1.5"/><path d="M${x2 - 8} ${yy - 5} L${x2} ${yy} L${x2 - 8} ${yy + 5}" fill="none" stroke="${c.faint}" stroke-width="1.5"/></g>`;
    }
  });
  const head = 'HOW YOUR VAULT IS SEALED';
  const foot = 'No server, no account, no sync. Forget the master password and nobody can open the vault, including us.';
  const css = fontCSS('BkSans', `${FD}/geist-sans/Geist-Medium.woff2`, head + steps.map(s => s[0]).join('')) +
              fontCSS('BkMono', `${FD}/geist-mono/GeistMono-Regular.woff2`, steps.map(s => s[1]).join('') + foot);
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="How your vault is sealed: master password (never stored), Argon2id (100 MiB, 3 passes, 32-byte salt), PBKDF2-SHA3-256 (110,000 iterations), a 256-bit key held in memory only while the vault is open, AES-256-GCM on every field with a fresh nonce, saved to Bunker.mmf on your disk.">
<title>How your vault is sealed</title>
<defs><style>${css}
.h{font-family:BkSans;font-size:18px}.s{font-family:BkMono;font-size:12.5px}
.st{animation:in .5s both}@keyframes in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
</style></defs>
<rect x="1" y="1" width="${W - 2}" height="${H - 2}" rx="14" fill="${c.bg}" stroke="${c.line}"/>
<text x="40" y="58" font-family="BkSans" font-size="14" letter-spacing="4" fill="${c.dim}">${head}</text>
${g}
<text x="40" y="250" font-family="BkMono" font-size="13" fill="${c.faint}">${esc(foot)}</text>
</svg>`;
}


/* ---------------- ARCHIVE: hero as the in-app ASCII art (display_bunker) ---------------- */
const ANSI = {
  dark:  { RESET:'#D3D9E2', MUSTARD:'#D9A93A', DBLUE:'#3BA3B0', BUNKER:'#727C8A', CYAN:'#5FD7E0', FBLUE:'#3A9BFF', GOLD:'#F4CF62', RED:'#FF6B6B', VINTAGE:'#D0463B' },
  light: { RESET:'#2B323C', MUSTARD:'#9A6700', DBLUE:'#1C7F8A', BUNKER:'#5A6470', CYAN:'#0B7F8A', FBLUE:'#0969DA', GOLD:'#B07D00', RED:'#CF222E', VINTAGE:'#A40E26' },
};
function parseArt() {
  const raw = fs.readFileSync('art.txt', 'utf8').replace(/\n$/, '').split('\n').map(l => l.replace(/·/g, ' ').replace('{ipv4_string}', ''));
  let colour = 'RESET';
  const rows = raw.map(line => { const cells = []; let i = 0;
    while (i < line.length) { const m = line.slice(i).match(/^\{([A-Z]+)\}/); if (m) { colour = m[1]; i += m[0].length; continue; } cells.push([line[i], colour]); i++; }
    return cells; });
  const lead = Math.min(...rows.filter(r => r.some(c => c[0] !== ' ')).map(r => r.findIndex(c => c[0] !== ' ')));
  return rows.map(r => r.slice(lead));
}
function heroAscii(m) {
  const c = P[m], A = ANSI[m], W = 1280, H = 560, fs_ = 14, cw = fs_ * 0.6, lh = 19;
  const rows = parseArt(); const cols = Math.max(...rows.map(r => r.length));
  const x0 = Math.round((W - cols * cw) / 2), y0 = 54; let body = '', glyphs = '';
  rows.forEach((r, li) => { const y = y0 + li * lh; let runs = [], cur = null;
    r.forEach(([ch, col], ci) => { glyphs += ch; if (ch === ' ') { cur = null; return; }
      const solo = (ch === '*' || ch === '.') && col === 'RESET', light = ch === 'o' && (col === 'FBLUE' || col === 'DBLUE');
      if (solo || light) { runs.push({ x: ci, t: ch, col, cls: solo ? 'tw' : 'lamp' }); cur = null; return; }
      if (cur && cur.col === col && cur.end === ci) { cur.t += ch; cur.end++; } else { cur = { x: ci, t: ch, col, end: ci + 1 }; runs.push(cur); } });
    body += `<g class="row" style="animation-delay:${(0.15 + li * 0.06).toFixed(2)}s">` + runs.map(u => { const d = u.cls ? ` class="${u.cls}" style="animation-delay:${((li * 7 + u.x) % 23 / 7).toFixed(2)}s"` : '';
      return `<text x="${(x0 + u.x * cw).toFixed(1)}" y="${y}" fill="${A[u.col]}"${d}>${esc(u.t)}</text>`; }).join('') + '</g>'; });
  const tag = 'YOUR DIGITAL FORTRESS  ·  TERMINAL EDITION', sub = 'Offline password & notes vault  ·  AES-256-GCM  ·  Argon2id  ·  no account  ·  no cloud';
  const css = fontCSS('BkMono', `${FD}/geist-mono/GeistMono-Regular.woff2`, glyphs + sub) + fontCSS('BkSans', `${FD}/geist-sans/Geist-Medium.woff2`, 'BUNKER2.0' + tag);
  const ty = y0 + rows.length * lh + 70;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="BUNKER 2.0 — the bunker art from the app's login screen."><title>BUNKER 2.0</title>
<defs><style>${css}
text{font-family:BkMono;font-size:${fs_}px;white-space:pre}
.row{animation:boot .18s steps(2,end) both}@keyframes boot{from{opacity:0}to{opacity:1}}
.tw{animation:tw 3.6s ease-in-out infinite}@keyframes tw{0%,100%{opacity:1}50%{opacity:.25}}
.lamp{animation:lamp 2.4s steps(1,end) infinite}@keyframes lamp{0%,70%{opacity:1}71%,100%{opacity:.35}}
.rise{animation:rise .72s 1.4s cubic-bezier(.33,.33,.55,1) both}@keyframes rise{from{transform:translateY(10px);opacity:0}to{transform:none;opacity:1}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}</style></defs>
<rect width="${W}" height="${H}" fill="${c.bg}"/>${body}
<g class="rise" text-anchor="middle"><text x="${W / 2}" y="${ty}" style="font-family:BkSans;font-size:58px;letter-spacing:13px" fill="${c.ink}">BUNKER<tspan fill="${c.accent}" dx="10">2.0</tspan></text>
<text x="${W / 2}" y="${ty + 36}" style="font-family:BkSans;font-size:14px;letter-spacing:4.2px" fill="${c.dim}">${esc(tag)}</text>
<text x="${W / 2}" y="${ty + 66}" style="font-size:13px" fill="${c.faint}">${esc(sub)}</text></g></svg>`;
}

/* ---------------- PILLS (link row, profile style) ---------------- */
function pill(m, label, icon) {
  const c = P[m], h = 34, w = Math.round(label.length * 7.3 + 52);
  const css = fontCSS('BkSans', `${FD}/geist-sans/Geist-Medium.woff2`, label);
  const ico = icon === 'mark'
    ? `<mask id="cm"><rect width="40" height="40" fill="#fff"/><circle cx="25" cy="15" r="6.2" fill="#000"/></mask><circle cx="22" cy="17" r="7" fill="${c.ink}" mask="url(#cm)"/>`
    : `<circle cx="21" cy="17" r="3.6" fill="${c.accent}"/>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(label)}"><title>${esc(label)}</title><defs><style>${css}</style></defs>
<rect x=".75" y=".75" width="${w - 1.5}" height="${h - 1.5}" rx="${(h - 1.5) / 2}" fill="${c.card}" stroke="${c.line}" stroke-width="1.5"/>${ico}
<text x="36" y="21.5" style="font-family:BkSans;font-size:13px" fill="${c.ink}">${esc(label)}</text></svg>`;
}

/* ---------------- FOOTER (setting crescent) ---------------- */
function footer(m) {
  const c = P[m], W = 1280, H = 170, line = 'Nothing left to read. Nothing left behind.', site = 'ZEROMARKS.NET';
  const css = fontCSS('BkMono', `${FD}/geist-mono/GeistMono-Regular.woff2`, line) + fontCSS('BkSans', `${FD}/geist-sans/Geist-Medium.woff2`, site);
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${line} — zeromarks.net"><title>${line}</title>
<defs><style>${css}.set{animation:set 2.4s .3s cubic-bezier(.33,.33,.55,1) both}@keyframes set{from{transform:translateY(-14px);opacity:0}to{transform:none;opacity:1}}@media (prefers-reduced-motion:reduce){*{animation:none!important}}</style>
<mask id="fm"><rect width="${W}" height="${H}" fill="#fff"/><circle cx="${W / 2 + 9}" cy="40" r="15" fill="#000"/></mask><clipPath id="hz"><rect width="${W}" height="62"/></clipPath></defs>
<g clip-path="url(#hz)"><g class="set"><circle cx="${W / 2}" cy="46" r="17" fill="${m === 'dark' ? c.glow : c.accent}" mask="url(#fm)"/></g></g>
<line x1="${W / 2 - 220}" y1="62" x2="${W / 2 + 220}" y2="62" stroke="${c.line}" stroke-width="1.5"/>
<text x="${W / 2}" y="104" text-anchor="middle" style="font-family:BkMono;font-size:15px" fill="${c.dim}">${line}</text>
<text x="${W / 2}" y="138" text-anchor="middle" style="font-family:BkSans;font-size:12px;letter-spacing:4px" fill="${c.faint}">${site}</text></svg>`;
}

const MAIN_LINES = [
  ['cmd', 'git clone https://github.com/ZeroMarks/BUNKER2.0 && cd BUNKER2.0'],
  ['cmd', 'pip install inputimeout keyboard cryptography pyperclip psutil requests argon2-cffi'],
  ['gap'],
  ['cmd', 'python3 BUNKER.py'],
  ['out', '# the included demo vault opens with the password: rootroot', 'faint'],
  ['out', '# delete Bunker.mmf first to create your own vault', 'faint'],
];
const PILLS = [['demo', 'Demo video', 'dot'], ['install', 'Install', 'dot'], ['security', 'Security model', 'dot'], ['threat', 'Threat model', 'dot'], ['site', 'zeromarks.net', 'mark']];
for (const m of ['dark', 'light']) {
  fs.writeFileSync(`${OUT}/footer-${m}.svg`, footer(m));
  fs.writeFileSync(`${OUT}/install-main-${m}.svg`, terminal(m, MAIN_LINES));
  for (const [id, label, icon] of PILLS) fs.writeFileSync(`${OUT}/pill-${id}-${m}.svg`, pill(m, label, icon));
  fs.writeFileSync(`${OUT}/hero-${m}.svg`, hero(m));
  fs.writeFileSync(`${OUT}/install-${m}.svg`, terminal(m));
  fs.writeFileSync(`${OUT}/sealed-${m}.svg`, seal(m));
}
console.log(fs.readdirSync(OUT).map(f => f + ' ' + fs.statSync(`${OUT}/${f}`).size).join('\n'));

# C4 Rendering Engine — Reference Implementation

## Usage

Copy this code **verbatim** into the `<script>` section of the generated HTML file. Only the `C4` data object, NFR panel HTML, design decision HTML, component SVGs and component tabs are generated per-architecture.

## Complete Engine Code

```javascript
// ===== State =====
let currentLevel = 'context';
let dragState = null;
let undoStack = []; // [{levelKey, id, x, y}]
const MAX_UNDO = 50;
let initialPositions = {}; // {levelKey: {id: {x,y}}}
let panState = null; // {svg, startX, startY, viewBox}
let zoomLevels = {}; // {svgId: {x, y, w, h}} — current viewBox

// ===== Utility: SVG coordinate conversion =====
function svgPoint(svg, clientX, clientY) {
  const pt = svg.createSVGPoint();
  pt.x = clientX; pt.y = clientY;
  return pt.matrixTransform(svg.getScreenCTM().inverse());
}

// ===== Layout: Calculate initial positions from position hints =====
function calculateInitialPositions(levelKey, elements) {
  const config = {
    context:   { vw: 1100, vh: 700, zones: { top: 40, center: 250, bottom: 500 }, hGap: 200, vGap: 40, padL: 60 },
    container: { vw: 1500, vh: 1100, zones: { top: 30, center: 220, bottom: 600 }, hGap: 150, vGap: 50, padL: 60 },
    component: { vw: 1200, vh: 800, zones: { top: 30, center: 200, bottom: 500 }, hGap: 140, vGap: 40, padL: 60 }
  };
  const defaults = {
    person: [120,155], external_person: [120,155], system: [240,100], external_system: [180,80],
    gateway: [180,90], webapp: [180,90], api: [180,90], service: [180,90],
    database: [160,80], cache: [160,75], cdn: [160,75], scheduler: [160,75],
    message_broker: [180,75], queue: [180,75], external_service: [160,75], adapter: [160,75],
    controller: [170,70], service_class: [170,70], repository: [170,70],
    event_handler: [170,70], background_worker: [170,70],
    validator: [150,65], factory: [150,65], facade: [150,65]
  };
  const cfg = config[levelKey] || config.component;
  elements.forEach(el => {
    if (el.x !== undefined && el.y !== undefined) return; // already positioned
    const dim = defaults[el.type] || [170, 70];
    el.w = el.w || dim[0];
    el.h = el.h || dim[1];
    const pos = el.position || { zone: 'center', row: 0, col: 0 };
    const zoneY = cfg.zones[pos.zone] || cfg.zones.center;
    el.x = cfg.padL + (pos.col || 0) * (el.w + cfg.hGap);
    el.y = zoneY + (pos.row || 0) * (el.h + cfg.vGap);
  });
  // Overlap resolution
  for (let i = 0; i < elements.length; i++) {
    for (let j = i + 1; j < elements.length; j++) {
      const a = elements[i], b = elements[j];
      if (a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y) {
        b.x = a.x + a.w + cfg.hGap;
      }
    }
  }
}

// ===== Connection Point Algorithm =====
function getConnectionPoint(el, tx, ty) {
  const cx = el.x + el.w / 2, cy = el.y + el.h / 2;
  const dx = tx - cx, dy = ty - cy;
  if (dx === 0 && dy === 0) return { x: cx, y: el.y };
  const absDx = Math.abs(dx), absDy = Math.abs(dy);
  const scaleX = (el.w / 2) / (absDx || 1), scaleY = (el.h / 2) / (absDy || 1);
  const scale = Math.min(scaleX, scaleY);
  return { x: cx + dx * scale, y: cy + dy * scale };
}

// ===== SVG Shape Rendering =====
function svgShape(el, colors) {
  const c = colors[el.type] || { fill: '#999', stroke: '#888', text: '#fff' };
  const textColor = c.text || '#fff';

  if (el.type === 'person' || el.type === 'external_person') {
    return `<g class="c4-element" data-id="${el.id}" tabindex="0" transform="translate(${el.x},${el.y})">
      <circle cx="60" cy="20" r="16" fill="${c.fill}" stroke="${c.stroke}" stroke-width="2"/>
      <line x1="60" y1="36" x2="60" y2="75" stroke="${c.stroke}" stroke-width="2"/>
      <line x1="30" y1="55" x2="90" y2="55" stroke="${c.stroke}" stroke-width="2"/>
      <line x1="60" y1="75" x2="35" y2="105" stroke="${c.stroke}" stroke-width="2"/>
      <line x1="60" y1="75" x2="85" y2="105" stroke="${c.stroke}" stroke-width="2"/>
      <rect x="0" y="110" width="120" height="45" rx="8" fill="${c.fill}" stroke="${c.stroke}" stroke-width="2" filter="url(#ds)"/>
      <text x="60" y="128" text-anchor="middle" fill="${textColor}" font-size="12" font-weight="600">${esc(el.name)}</text>
      <text x="60" y="145" text-anchor="middle" fill="${textColor}" font-size="9" opacity="0.85">${truncate(el.desc, 22)}</text>
    </g>`;
  }

  if (el.type === 'database') {
    const ry = 12;
    return `<g class="c4-element" data-id="${el.id}" tabindex="0" transform="translate(${el.x},${el.y})">
      <rect x="0" y="${ry}" width="${el.w}" height="${el.h - ry}" fill="${c.fill}" stroke="${c.stroke}" stroke-width="2"/>
      <ellipse cx="${el.w/2}" cy="${ry}" rx="${el.w/2}" ry="${ry}" fill="${c.fill}" stroke="${c.stroke}" stroke-width="2"/>
      <ellipse cx="${el.w/2}" cy="${el.h}" rx="${el.w/2}" ry="${ry}" fill="${c.fill}" stroke="${c.stroke}" stroke-width="2"/>
      <text x="${el.w/2}" y="${el.h/2 + 4}" text-anchor="middle" fill="${textColor}" font-size="13" font-weight="600">${esc(el.name)}</text>
      <text x="${el.w/2}" y="${el.h/2 + 20}" text-anchor="middle" fill="${textColor}" font-size="10" font-style="italic" opacity="0.8">${esc(el.tech || '')}</text>
    </g>`;
  }

  if (el.type === 'gateway') {
    const hw = el.w/2, hh = el.h/2, inset = 20;
    const pts = `${hw},0 ${el.w - inset},${hh * 0.4} ${el.w - inset},${hh * 1.6} ${hw},${el.h} ${inset},${hh * 1.6} ${inset},${hh * 0.4}`;
    return `<g class="c4-element" data-id="${el.id}" tabindex="0" transform="translate(${el.x},${el.y})">
      <polygon points="${pts}" fill="${c.fill}" stroke="${c.stroke}" stroke-width="2" filter="url(#ds)"/>
      <text x="${hw}" y="${hh - 4}" text-anchor="middle" fill="${textColor}" font-size="13" font-weight="600">${esc(el.name)}</text>
      <text x="${hw}" y="${hh + 12}" text-anchor="middle" fill="${textColor}" font-size="10" opacity="0.85">${truncate(el.desc, 28)}</text>
      <text x="${hw}" y="${hh + 26}" text-anchor="middle" fill="${textColor}" font-size="9" font-style="italic" opacity="0.7">${esc(el.tech || '')}</text>
    </g>`;
  }

  // Default: rounded rectangle (service, cache, webapp, api, scheduler, etc.)
  const dashAttr = (el.type === 'message_broker' || el.type === 'queue') ? ' stroke-dasharray="6,3"' : '';
  const rx = (el.type.startsWith('cmp') || ['controller','service_class','repository','event_handler','background_worker','validator','factory','facade','adapter'].includes(el.type)) ? 4 : 8;
  const sw = rx === 4 ? 1.5 : 2;
  return `<g class="c4-element" data-id="${el.id}" tabindex="0" transform="translate(${el.x},${el.y})">
    <rect width="${el.w}" height="${el.h}" rx="${rx}" fill="${c.fill}" stroke="${c.stroke}" stroke-width="${sw}"${dashAttr} filter="url(#ds)"/>
    <text x="${el.w/2}" y="${el.h/2 - 6}" text-anchor="middle" fill="${textColor}" font-size="13" font-weight="600">${esc(el.name)}</text>
    <text x="${el.w/2}" y="${el.h/2 + 10}" text-anchor="middle" fill="${textColor}" font-size="10" opacity="0.85">${truncate(el.desc, 30)}</text>
    <text x="${el.w/2}" y="${el.h/2 + 24}" text-anchor="middle" fill="${textColor}" font-size="9" font-style="italic" opacity="0.7">${esc(el.tech || '')}</text>
  </g>`;
}

function esc(s) { return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function truncate(s, max) { s = s || ''; return s.length > max ? esc(s.slice(0, max - 1)) + '...' : esc(s); }

// ===== Arrow Rendering =====
function renderArrows(svgId, levelData) {
  const svg = document.getElementById(svgId);
  const layer = svg.querySelector('.arrows-layer');
  layer.innerHTML = '';
  const markerId = svg.querySelector('marker')?.id || 'af';
  const els = {};
  levelData.elements.forEach(e => els[e.id] = e);

  (levelData.relationships || []).forEach((rel, idx) => {
    const src = els[rel.from], tgt = els[rel.to];
    if (!src || !tgt) return;
    const srcC = { x: src.x + src.w/2, y: src.y + src.h/2 };
    const tgtC = { x: tgt.x + tgt.w/2, y: tgt.y + tgt.h/2 };
    const p1 = getConnectionPoint(src, tgtC.x, tgtC.y);
    const p2 = getConnectionPoint(tgt, srcC.x, srcC.y);
    const dash = rel.async ? ' stroke-dasharray="8,4"' : '';
    const mx = (p1.x + p2.x) / 2, my = (p1.y + p2.y) / 2;
    const lbl = rel.label || '';
    const lw = lbl.length * 5.5 + 8;

    const markerStart = rel.bidirectional ? ` marker-start="url(#${markerId})"` : '';
    let html = `<line x1="${p1.x}" y1="${p1.y}" x2="${p2.x}" y2="${p2.y}" stroke-width="1.5"${dash} marker-end="url(#${markerId})"${markerStart} data-rel-index="${idx}" class="arrow-line"/>`;
    if (lbl) {
      html += `<rect x="${mx - lw/2}" y="${my - 8}" width="${lw}" height="16" rx="3" stroke-width="0.5" data-rel-index="${idx}" class="arrow-label-bg"/>`;
      html += `<text x="${mx}" y="${my + 3}" text-anchor="middle" font-size="10" data-rel-index="${idx}" class="arrow-label-text" pointer-events="none">${esc(lbl)}</text>`;
    }
    layer.innerHTML += html;
  });
}

// ===== Group Rendering =====
function renderGroups(svgId, levelData) {
  const svg = document.getElementById(svgId);
  const layer = svg.querySelector('.groups-layer');
  if (!layer) return;
  layer.innerHTML = '';
  const els = {};
  levelData.elements.forEach(e => els[e.id] = e);

  (levelData.groups || []).forEach(grp => {
    const members = (grp.ids || grp.elementIds || []).map(id => els[id]).filter(Boolean);
    if (!members.length) return;
    const pad = 30;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    members.forEach(m => {
      minX = Math.min(minX, m.x); minY = Math.min(minY, m.y);
      maxX = Math.max(maxX, m.x + m.w); maxY = Math.max(maxY, m.y + m.h);
    });
    const gx = minX - pad, gy = minY - pad - 18;
    const gw = maxX - minX + pad * 2, gh = maxY - minY + pad * 2 + 18;
    const c = grp.color || (C4.colors[members[0].type] || { fill: '#999' }).fill;
    layer.innerHTML += `<rect x="${gx}" y="${gy}" width="${gw}" height="${gh}" rx="8" fill="${c}" fill-opacity="0.05" stroke="${c}" stroke-opacity="0.3" stroke-dasharray="8,4" stroke-width="1.5"/>`;
    layer.innerHTML += `<text x="${gx + 10}" y="${gy + 16}" font-size="13" font-weight="600" fill="${c}" opacity="0.6">${esc(grp.name)}</text>`;
  });
}

// ===== Render Level =====
function renderLevel(levelKey) {
  let svgId, levelData;
  if (levelKey === 'context') {
    svgId = 'svg-context'; levelData = C4.levels.context;
  } else if (levelKey === 'container') {
    // Legacy: redirect to first container view
    const keys = Object.keys(C4.levels.containers || {});
    if (keys.length) { renderLevel('container:' + keys[0]); return; }
    else return;
  } else if (levelKey.startsWith('container:')) {
    const sysId = levelKey.split(':')[1];
    svgId = 'svg-container-' + sysId;
    levelData = (C4.levels.containers || {})[sysId];
  } else if (levelKey.startsWith('component:')) {
    const containerId = levelKey.split(':')[1];
    svgId = 'svg-component-' + containerId;
    levelData = (C4.levels.components || {})[containerId];
  } else if (levelKey === 'code') {
    renderCodeLevel(); return;
  }
  if (!levelData) return;

  const svg = document.getElementById(svgId);
  if (!svg) return;
  const elLayer = svg.querySelector('.elements-layer');
  elLayer.innerHTML = '';
  levelData.elements.forEach(el => {
    elLayer.innerHTML += svgShape(el, C4.colors);
  });
  renderGroups(svgId, levelData);
  renderArrows(svgId, levelData);
}

// ===== Code Level =====
function renderCodeLevel() {
  const svg = document.getElementById('svg-code');
  const layer = svg.querySelector('.elements-layer');
  layer.innerHTML = '';
  const cols = 3, gap = 24, padX = 14, padY = 10;
  const charW = 6.6; // approximate monospace char width at 11px
  const lineH = 16.5; // 11px * 1.5 line-height
  const minCardW = 300, minCardH = 120;
  const whyH = 24; // height reserved for why-line below header
  const headerH = 36 + whyH; // header bar + why subtitle
  const snippets = C4.code.snippets || [];
  if (!snippets.length) return;

  // Phase 1: Measure each snippet's natural dimensions
  const measured = snippets.map(sn => {
    const lines = (sn.code || '').split('\n');
    const maxLineLen = Math.max(...lines.map(l => l.length), 20);
    const w = Math.max(Math.ceil(maxLineLen * charW) + padX * 2, minCardW);
    const h = Math.max(Math.ceil(lines.length * lineH) + headerH + padY * 2, minCardH);
    return { sn, w, h };
  });

  // Phase 2: Calculate uniform column widths and row heights for clean grid
  const numRows = Math.ceil(snippets.length / cols);
  const colWidths = [];
  for (let c = 0; c < cols; c++) {
    let maxW = minCardW;
    for (let r = 0; r < numRows; r++) {
      const idx = r * cols + c;
      if (idx < measured.length) maxW = Math.max(maxW, measured[idx].w);
    }
    colWidths.push(maxW);
  }
  const rowHeights = [];
  for (let r = 0; r < numRows; r++) {
    let maxH = minCardH;
    for (let c = 0; c < cols; c++) {
      const idx = r * cols + c;
      if (idx < measured.length) maxH = Math.max(maxH, measured[idx].h);
    }
    rowHeights.push(maxH);
  }

  // Phase 3: Calculate total viewBox
  const totalW = colWidths.reduce((a, b) => a + b, 0) + (cols + 1) * gap;
  const totalH = rowHeights.reduce((a, b) => a + b, 0) + (numRows + 1) * gap;
  svg.setAttribute('viewBox', `0 0 ${totalW} ${totalH}`);

  // Phase 4: Render cards at calculated positions
  snippets.forEach((sn, i) => {
    const col = i % cols, row = Math.floor(i / cols);
    // X offset: gap + sum of previous column widths + gaps
    let sx = gap;
    for (let c = 0; c < col; c++) sx += colWidths[c] + gap;
    // Y offset: gap + sum of previous row heights + gaps
    let sy = gap;
    for (let r = 0; r < row; r++) sy += rowHeights[r] + gap;
    const cardW = colWidths[col], cardH = rowHeights[row];
    const codeHtml = highlightCode(sn.code || '', sn.lang || 'text');
    const whyText = sn.why ? truncate(sn.why, 60) : '';
    layer.innerHTML += `<g transform="translate(${sx},${sy})" class="code-card" data-snippet-id="${sn.id}">
      <rect width="${cardW}" height="${cardH}" rx="8" fill="#1E1E2E" stroke="#313244" stroke-width="1.5"/>
      <rect width="${cardW}" height="32" rx="8" fill="#313244"/>
      <rect y="24" width="${cardW}" height="8" fill="#313244"/>
      <text x="12" y="21" font-size="12" font-weight="600" fill="#CDD6F4">${esc(sn.title)}</text>
      <text x="${cardW - 12}" y="21" text-anchor="end" font-size="10" fill="#6C7086">${esc(sn.lang)}</text>
      ${whyText ? `<text x="12" y="46" font-size="10" font-style="italic" fill="#89B4FA">${whyText}</text>` : ''}
      <foreignObject x="${padX}" y="${headerH}" width="${cardW - padX * 2}" height="${cardH - headerH - padY}">
        <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:'Fira Code','JetBrains Mono','Consolas',monospace;font-size:11px;color:#CDD6F4;white-space:pre;overflow:hidden;height:100%;line-height:1.5">${codeHtml}</div>
      </foreignObject>
    </g>`;
  });
}

// ===== Syntax Highlighting (Catppuccin Mocha) =====
function highlightCode(code, lang) {
  // Tokenize first to prevent overlapping highlights
  const tokens = [];
  let s = code.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

  // Phase 1: Extract comments and strings into placeholders (prevents inner matches)
  const placeholders = [];
  function ph(match, style) {
    const id = `\x00${placeholders.length}\x00`;
    placeholders.push(`<span style="${style}">${match}</span>`);
    return id;
  }
  // Block comments (/* ... */)
  s = s.replace(/\/\*[\s\S]*?\*\//g, m => ph(m, 'color:#6C7086;font-style:italic'));
  // Line comments (// or -- or #)
  s = s.replace(/(\/\/.*|--.*)/g, m => ph(m, 'color:#6C7086;font-style:italic'));
  if (['python','py','yaml','yml','bash','sh','shell'].includes(lang)) {
    s = s.replace(/(#.*)/g, m => ph(m, 'color:#6C7086;font-style:italic'));
  }
  // Double-quoted strings
  s = s.replace(/("(?:[^"\\]|\\.)*")/g, m => ph(m, 'color:#A6E3A1'));
  // Single-quoted strings
  s = s.replace(/('(?:[^'\\]|\\.)*')/g, m => ph(m, 'color:#A6E3A1'));
  // Template literals (backtick strings)
  s = s.replace(/(`(?:[^`\\]|\\.)*`)/g, m => ph(m, 'color:#A6E3A1'));

  // Phase 2: Language-specific keywords
  const norm = (lang || '').toLowerCase();
  if (norm === 'sql') {
    s = s.replace(/\b(CREATE|TABLE|INDEX|UNIQUE|SELECT|UPDATE|INSERT|DELETE|FROM|WHERE|AND|OR|SET|NOT|NULL|CHECK|IN|ON|PRIMARY|KEY|DEFAULT|LIMIT|FOR|SKIP|LOCKED|INTERVAL|BEGIN|COMMIT|ROLLBACK|AS|INTO|VALUES|EXISTS|IF|THEN|ELSE|END|CASE|WHEN|JOIN|LEFT|RIGHT|INNER|OUTER|GROUP|BY|ORDER|HAVING|DISTINCT|ALTER|DROP|CONSTRAINT|REFERENCES|FOREIGN|CASCADE|RETURNING|WITH|RECURSIVE|TRIGGER|FUNCTION|RETURNS|DECLARE|PERFORM|RAISE|EXCEPTION|TYPE|ENUM|BOOLEAN|INTEGER|TEXT|VARCHAR|TIMESTAMP|SERIAL|BIGSERIAL|UUID|JSONB)\b/gi,
      '<span style="color:#CBA6F7">$&</span>');
  } else if (['typescript','javascript','ts','js'].includes(norm)) {
    s = s.replace(/\b(async|await|return|const|let|var|if|else|new|class|function|import|export|try|catch|throw|finally|switch|case|break|default|for|while|do|of|in|yield|from|extends|implements|interface|type|enum|readonly|static|public|private|protected|abstract|get|set|typeof|instanceof|delete|void)\b/g,
      '<span style="color:#CBA6F7">$&</span>');
    s = s.replace(/\b(Promise|string|number|boolean|void|any|never|unknown|null|undefined|Array|Map|Set|Record|Partial|Required|Omit|Pick|Date|Error|RegExp)\b/g,
      '<span style="color:#F9E2AF">$&</span>');
    s = s.replace(/\.(\w+)\(/g, '.<span style="color:#89B4FA">$1</span>(');
    s = s.replace(/\b(function|const|let|var)\s+(\w+)/g, '$1 <span style="color:#89B4FA">$2</span>');
  } else if (['java','kotlin','kt'].includes(norm)) {
    s = s.replace(/\b(public|private|protected|static|final|abstract|class|interface|extends|implements|new|return|if|else|for|while|do|switch|case|break|default|try|catch|finally|throw|throws|import|package|void|this|super|synchronized|volatile|transient|enum|instanceof|assert|continue|native|strictfp)\b/g,
      '<span style="color:#CBA6F7">$&</span>');
    s = s.replace(/\b(String|int|long|double|float|boolean|char|byte|short|Integer|Long|Double|Float|Boolean|List|Map|Set|Optional|Stream|CompletableFuture|Object|void)\b/g,
      '<span style="color:#F9E2AF">$&</span>');
    s = s.replace(/\.(\w+)\(/g, '.<span style="color:#89B4FA">$1</span>(');
  } else if (['go','golang'].includes(norm)) {
    s = s.replace(/\b(func|return|if|else|for|range|switch|case|default|break|continue|go|defer|select|chan|map|struct|interface|type|package|import|var|const|nil|true|false|make|append|len|cap|new|delete|copy|close|panic|recover)\b/g,
      '<span style="color:#CBA6F7">$&</span>');
    s = s.replace(/\b(string|int|int8|int16|int32|int64|uint|float32|float64|bool|byte|rune|error|any|context\.Context)\b/g,
      '<span style="color:#F9E2AF">$&</span>');
    s = s.replace(/\.(\w+)\(/g, '.<span style="color:#89B4FA">$1</span>(');
  } else if (['python','py'].includes(norm)) {
    s = s.replace(/\b(def|class|return|if|elif|else|for|while|in|not|and|or|is|with|as|try|except|finally|raise|import|from|pass|break|continue|yield|lambda|global|nonlocal|assert|del|True|False|None|self|async|await)\b/g,
      '<span style="color:#CBA6F7">$&</span>');
    s = s.replace(/\b(str|int|float|bool|list|dict|set|tuple|Optional|List|Dict|Set|Tuple|Any|Union|Callable)\b/g,
      '<span style="color:#F9E2AF">$&</span>');
    s = s.replace(/\b(def)\s+(\w+)/g, '$1 <span style="color:#89B4FA">$2</span>');
  } else if (['yaml','yml'].includes(norm)) {
    s = s.replace(/^(\s*[\w.-]+)(?=\s*:)/gm, '<span style="color:#89B4FA">$1</span>');
    s = s.replace(/\b(true|false|null|yes|no)\b/gi, '<span style="color:#FAB387">$&</span>');
  } else if (['json'].includes(norm)) {
    s = s.replace(/\b(true|false|null)\b/g, '<span style="color:#FAB387">$&</span>');
  }

  // Phase 3: Numbers (only outside placeholders)
  s = s.replace(/\b(\d+\.?\d*)\b/g, '<span style="color:#FAB387">$1</span>');

  // Phase 4: Restore placeholders
  placeholders.forEach((val, i) => {
    s = s.replace(`\x00${i}\x00`, val);
  });

  return s;
}

// ===== Drag & Drop =====
function initDragAndDrop(svgId, levelData) {
  const svg = document.getElementById(svgId);
  if (!svg) return;
  const els = {};
  levelData.elements.forEach(e => els[e.id] = e);

  svg.addEventListener('mousedown', e => {
    if (e.button === 1) return; // middle-click reserved for pan
    const g = e.target.closest('.c4-element');
    if (!g) return;
    const id = g.dataset.id;
    const el = els[id];
    if (!el) return;
    const pt = svgPoint(svg, e.clientX, e.clientY);
    // Save position for undo before drag starts
    const levelKey = currentLevel;
    undoStack.push({ levelKey, id: el.id, x: el.x, y: el.y });
    if (undoStack.length > MAX_UNDO) undoStack.shift();
    dragState = { el, g, offsetX: pt.x - el.x, offsetY: pt.y - el.y, svgId, levelData };
    g.classList.add('dragging');
    e.preventDefault();
  });

  svg.addEventListener('mousemove', e => {
    if (!dragState || dragState.svgId !== svgId) return;
    const pt = svgPoint(svg, e.clientX, e.clientY);
    dragState.el.x = pt.x - dragState.offsetX;
    dragState.el.y = pt.y - dragState.offsetY;
    dragState.g.setAttribute('transform', `translate(${dragState.el.x},${dragState.el.y})`);
    renderArrows(svgId, dragState.levelData);
    renderGroups(svgId, dragState.levelData);

  });

  const endDrag = () => {
    if (!dragState) return;
    dragState.g.classList.remove('dragging');
    dragState = null;
  };
  svg.addEventListener('mouseup', endDrag);
  svg.addEventListener('mouseleave', endDrag);
}

// ===== Rich Tooltip (Element) =====
function showElementTooltip(el, x, y) {
  const tip = document.querySelector('.tooltip');
  let html = `<strong>${esc(el.name)}</strong>`;
  if (el.tech) html += `<br><em style="color:#AAA">[${esc(el.tech)}]</em>`;
  if (el.desc) html += `<br><span style="font-size:11px">${esc(el.desc)}</span>`;
  if (el.why) html += `<br><span style="color:#89B4FA;font-style:italic">Why: ${esc(el.why)}</span>`;
  if (el.pattern) html += `<br><span style="color:#A6E3A1;font-family:monospace;font-size:10px">Pattern: ${esc(el.pattern)}</span>`;
  if (el.relatedFrs && el.relatedFrs.length) {
    html += '<br>';
    el.relatedFrs.forEach(frId => {
      const fr = (C4.frs || []).find(f => f.id === frId);
      if (fr) html += `<span style="color:#CE93D8;font-size:10px">FR: ${esc(fr.id)} — ${esc(fr.title)}</span><br>`;
    });
  }
  if (el.relatedDecisions && el.relatedDecisions.length) {
    html += '<br>';
    el.relatedDecisions.forEach(ddId => {
      const dd = (C4.designDecisions || []).find(d => d.id === ddId);
      if (dd) html += `<span style="color:#F9E2AF;font-size:10px">→ ${esc(dd.id)}: ${esc(dd.title)}</span><br>`;
    });
  }
  tip.innerHTML = html;
  tip.style.left = (x + 14) + 'px';
  tip.style.top = (y + 18) + 'px';
  tip.style.display = 'block';
}

// ===== Rich Tooltip (Arrow) =====
function showArrowTooltip(rel, x, y) {
  const tip = document.querySelector('.tooltip');
  tip.classList.add('arrow-tooltip');
  let html = `<strong style="font-size:13px">${esc(rel.label)}</strong>`;
  if (rel.detail) html += `<br><span style="font-size:11px">${esc(rel.detail)}</span>`;
  if (rel.payload) html += `<br><div style="background:#1E1E2E;padding:4px 6px;border-radius:4px;margin-top:4px;font-family:monospace;font-size:10px;color:#A6E3A1">${esc(rel.payload)}</div>`;
  if (rel.why) html += `<br><span style="color:#89B4FA;font-style:italic">Why: ${esc(rel.why)}</span>`;
  if (rel.relatedDecision) {
    const dd = (C4.designDecisions || []).find(d => d.id === rel.relatedDecision);
    if (dd) html += `<br><span style="color:#F9E2AF;font-size:10px">→ ${esc(dd.id)}: ${esc(dd.title)}</span>`;
  }
  tip.innerHTML = html;
  tip.style.left = (x + 14) + 'px';
  tip.style.top = (y + 18) + 'px';
  tip.style.display = 'block';
}

function hideTooltip() {
  const tip = document.querySelector('.tooltip');
  tip.style.display = 'none';
  tip.classList.remove('arrow-tooltip');
}

// ===== Hover Event Delegation =====
function initTooltips(svgId, levelData) {
  const svg = document.getElementById(svgId);
  if (!svg) return;
  const els = {};
  levelData.elements.forEach(e => els[e.id] = e);

  svg.addEventListener('mouseover', e => {
    const g = e.target.closest('.c4-element');
    if (g) {
      const el = els[g.dataset.id];
      if (el) showElementTooltip(el, e.clientX, e.clientY);
      return;
    }
    const arrowEl = e.target.closest('[data-rel-index]');
    if (arrowEl) {
      const idx = parseInt(arrowEl.dataset.relIndex);
      const rel = (levelData.relationships || [])[idx];
      if (rel) showArrowTooltip(rel, e.clientX, e.clientY);
    }
  });
  svg.addEventListener('mousemove', e => {
    const tip = document.querySelector('.tooltip');
    if (tip.style.display === 'block') {
      tip.style.left = (e.clientX + 14) + 'px';
      tip.style.top = (e.clientY + 18) + 'px';
    }
  });
  svg.addEventListener('mouseout', e => {
    const g = e.target.closest('.c4-element');
    const arrowEl = e.target.closest('[data-rel-index]');
    if (g || arrowEl) hideTooltip();
  });
}

// ===== Keyboard Navigation for Elements =====
function initKeyboardNav(svgId, levelData) {
  const svg = document.getElementById(svgId);
  if (!svg) return;
  const els = {};
  levelData.elements.forEach(e => els[e.id] = e);

  svg.addEventListener('keydown', e => {
    const g = e.target.closest('.c4-element');
    if (!g) return;
    const el = els[g.dataset.id];
    if (!el) return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      if (e.key === 'Enter' && el.drillDown) {
        switchLevel(el.drillDown);
      } else {
        const rect = g.getBoundingClientRect();
        showElementTooltip(el, rect.left + rect.width / 2, rect.top);
      }
    }
    if (e.key === 'Escape') hideTooltip();
  });
}

// ===== Double-Click Drill-Down =====
function initDrillDown(svgId, levelData) {
  const svg = document.getElementById(svgId);
  if (!svg) return;
  const els = {};
  levelData.elements.forEach(e => els[e.id] = e);

  svg.addEventListener('dblclick', e => {
    const g = e.target.closest('.c4-element');
    if (!g) return;
    const el = els[g.dataset.id];
    if (el && el.drillDown) switchLevel(el.drillDown);
  });
}

// ===== Level Switching =====
function switchLevel(levelKey) {
  // Legacy redirect: bare "container" → first container view
  if (levelKey === 'container') {
    const keys = Object.keys(C4.levels.containers || {});
    if (keys.length) return switchLevel('container:' + keys[0]);
    return;
  }

  currentLevel = levelKey;
  document.querySelectorAll('.canvas-area svg').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => { t.classList.remove('active'); t.setAttribute('aria-selected', 'false'); });

  let svgId, tabSelector;
  // Build breadcrumb segments: [{label, levelKey}]
  const crumbs = [{ label: 'Context', key: 'context' }];

  if (levelKey === 'context') {
    svgId = 'svg-context'; tabSelector = '[data-level="context"]';
  } else if (levelKey.startsWith('container:')) {
    const sId = levelKey.split(':')[1];
    svgId = 'svg-container-' + sId;
    tabSelector = `[data-level="${levelKey}"]`;
    const sysEl = (C4.levels.context.elements || []).find(e => e.id === sId);
    crumbs.push({ label: sysEl ? sysEl.name : sId, key: levelKey });
  } else if (levelKey.startsWith('component:')) {
    const cId = levelKey.split(':')[1];
    svgId = 'svg-component-' + cId;
    tabSelector = `[data-level="${levelKey}"]`;
    // Find parent system
    const parentSysId = findParentSystem(cId);
    if (parentSysId) {
      const sysEl = (C4.levels.context.elements || []).find(e => e.id === parentSysId);
      crumbs.push({ label: sysEl ? sysEl.name : parentSysId, key: 'container:' + parentSysId });
    }
    // Find container name
    let containerName = cId;
    for (const cv of Object.values(C4.levels.containers || {})) {
      const el = (cv.elements || []).find(e => e.id === cId);
      if (el) { containerName = el.name; break; }
    }
    crumbs.push({ label: containerName, key: levelKey });
  } else if (levelKey === 'code') {
    svgId = 'svg-code'; tabSelector = '[data-level="code"]';
    crumbs.push({ label: 'Code', key: 'code' });
  }

  const svg = document.getElementById(svgId);
  if (svg) svg.classList.add('active');
  const tab = document.querySelector(tabSelector);
  if (tab) { tab.classList.add('active'); tab.setAttribute('aria-selected', 'true'); }

  // Render breadcrumb
  document.querySelector('.breadcrumb').innerHTML = crumbs.map((c, i) => {
    if (i < crumbs.length - 1) {
      return `<span class="breadcrumb-link" onclick="switchLevel('${c.key}')">${c.label}</span>`;
    }
    return `<span>${c.label}</span>`;
  }).join(' <span class="breadcrumb-sep">\u2192</span> ');
}


function getLevelData(levelKey) {
  if (levelKey === 'context') return C4.levels.context;
  if (levelKey === 'container') { const keys = Object.keys(C4.levels.containers || {}); return keys.length ? C4.levels.containers[keys[0]] : null; }
  if (levelKey.startsWith('container:')) return (C4.levels.containers || {})[levelKey.split(':')[1]];
  if (levelKey.startsWith('component:')) return (C4.levels.components || {})[levelKey.split(':')[1]];
  return null;
}

function getSvgId(levelKey) {
  if (levelKey === 'context') return 'svg-context';
  if (levelKey === 'container') { const keys = Object.keys(C4.levels.containers || {}); return keys.length ? 'svg-container-' + keys[0] : null; }
  if (levelKey.startsWith('container:')) return 'svg-container-' + levelKey.split(':')[1];
  if (levelKey.startsWith('component:')) return 'svg-component-' + levelKey.split(':')[1];
  if (levelKey === 'code') return 'svg-code';
  return null;
}

function findParentSystem(containerId) {
  for (const [sId, cv] of Object.entries(C4.levels.containers || {})) {
    if ((cv.elements || []).some(e => e.id === containerId)) return sId;
  }
  return null;
}

// ===== NFR Panel: Design Decision Hover Highlighting =====
function initDecisionHighlighting() {
  document.querySelectorAll('.dd-item').forEach(item => {
    const elIds = (item.dataset.elements || '').split(',').filter(Boolean);
    item.addEventListener('mouseenter', () => {
      elIds.forEach(id => {
        document.querySelectorAll(`[data-id="${id}"]`).forEach(g => {
          g.classList.add('dd-highlight');
        });
      });
    });
    item.addEventListener('mouseleave', () => {
      document.querySelectorAll('.dd-highlight').forEach(g => g.classList.remove('dd-highlight'));
    });
  });
}

// ===== Code Overlay =====
function initCodeOverlay() {
  document.addEventListener('click', e => {
    const card = e.target.closest('.code-card');
    if (!card) return;
    const snId = card.dataset.snippetId;
    const sn = (C4.code.snippets || []).find(s => s.id === snId);
    if (!sn) return;
    const overlay = document.querySelector('.code-overlay');
    let titleHtml = esc(sn.title) + (sn.lang ? ` <span style="color:#6C7086">(${esc(sn.lang)})</span>` : '');
    if (sn.why) titleHtml += `<div style="font-size:12px;font-weight:400;color:#89B4FA;font-style:italic;margin-top:4px">${esc(sn.why)}</div>`;
    overlay.querySelector('.code-title').innerHTML = titleHtml;
    // Build code with line annotations
    let codeHtml = highlightCode(sn.code || '', sn.lang || 'text');
    if (sn.annotations && sn.annotations.length) {
      const lines = codeHtml.split('\n');
      sn.annotations.forEach(ann => {
        const idx = (ann.line || 1) - 1;
        if (idx >= 0 && idx < lines.length) {
          lines[idx] += `  <span style="color:#F9E2AF;font-style:italic;background:#2A2A2A;padding:1px 6px;border-radius:3px;font-size:10px">← ${esc(ann.text)}</span>`;
        }
      });
      codeHtml = lines.join('\n');
    }
    overlay.querySelector('.code-content').innerHTML = codeHtml;
    overlay.classList.add('visible');
  });
}

// ===== Zoom & Pan =====
function initZoomPan(svgId) {
  const svg = document.getElementById(svgId);
  if (!svg) return;
  const vb = svg.getAttribute('viewBox').split(' ').map(Number);
  zoomLevels[svgId] = { x: vb[0], y: vb[1], w: vb[2], h: vb[3], origW: vb[2], origH: vb[3] };

  // Wheel zoom
  svg.addEventListener('wheel', e => {
    e.preventDefault();
    const z = zoomLevels[svgId];
    const factor = e.deltaY > 0 ? 1.1 : 0.9;
    // Limit zoom: 30% to 300% of original
    const newW = z.w * factor, newH = z.h * factor;
    if (newW < z.origW * 0.3 || newW > z.origW * 3) return;
    // Zoom toward cursor position
    const pt = svgPoint(svg, e.clientX, e.clientY);
    const dx = (pt.x - z.x) * (1 - factor);
    const dy = (pt.y - z.y) * (1 - factor);
    z.x += dx; z.y += dy; z.w = newW; z.h = newH;
    svg.setAttribute('viewBox', `${z.x} ${z.y} ${z.w} ${z.h}`);
  }, { passive: false });

  // Middle-click pan
  svg.addEventListener('mousedown', e => {
    if (e.button !== 1) return; // only middle button
    e.preventDefault();
    const z = zoomLevels[svgId];
    panState = { svgId, startX: e.clientX, startY: e.clientY, origVBx: z.x, origVBy: z.y };
  });
  svg.addEventListener('mousemove', e => {
    if (!panState || panState.svgId !== svgId) return;
    const z = zoomLevels[svgId];
    // Convert pixel delta to SVG units
    const rect = svg.getBoundingClientRect();
    const scaleX = z.w / rect.width, scaleY = z.h / rect.height;
    z.x = panState.origVBx - (e.clientX - panState.startX) * scaleX;
    z.y = panState.origVBy - (e.clientY - panState.startY) * scaleY;
    svg.setAttribute('viewBox', `${z.x} ${z.y} ${z.w} ${z.h}`);
  });
  const endPan = () => { if (panState && panState.svgId === svgId) panState = null; };
  svg.addEventListener('mouseup', e => { if (e.button === 1) endPan(); });
  svg.addEventListener('mouseleave', endPan);
}

function resetZoom(svgId) {
  const z = zoomLevels[svgId];
  if (!z) return;
  z.x = 0; z.y = 0; z.w = z.origW; z.h = z.origH;
  document.getElementById(svgId)?.setAttribute('viewBox', `0 0 ${z.origW} ${z.origH}`);
}

// ===== Undo (Ctrl+Z) =====
function undoLastDrag() {
  if (!undoStack.length) return;
  const action = undoStack.pop();
  const levelData = getLevelData(action.levelKey);
  if (!levelData) return;
  const el = levelData.elements.find(e => e.id === action.id);
  if (!el) return;
  el.x = action.x; el.y = action.y;
  // Re-render current level
  const svgId = getSvgId(action.levelKey);
  if (svgId) {
    renderLevel(action.levelKey);
    initDragAndDrop(svgId, levelData); // rebind after re-render
  }
}

// ===== Reset All Positions =====
function resetPositions() {
  const levelKey = currentLevel;
  const saved = initialPositions[levelKey];
  if (!saved) return;
  const levelData = getLevelData(levelKey);
  if (!levelData) return;
  levelData.elements.forEach(el => {
    if (saved[el.id]) { el.x = saved[el.id].x; el.y = saved[el.id].y; }
  });
  const svgId = getSvgId(levelKey);
  if (svgId) {
    renderLevel(levelKey);
    initDragAndDrop(svgId, levelData);
    resetZoom(svgId);
  }
}

function saveInitialPositions(levelKey, elements) {
  initialPositions[levelKey] = {};
  elements.forEach(el => {
    initialPositions[levelKey][el.id] = { x: el.x, y: el.y };
  });
}

// ===== Keyboard Shortcuts =====
function initKeyboard() {
  document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.key === 'Escape') {
      document.querySelector('.code-overlay')?.classList.remove('visible');
      hideTooltip();
    }
    // Ctrl+Z = undo last drag
    if (e.key === 'z' && (e.ctrlKey || e.metaKey) && !e.shiftKey) {
      e.preventDefault();
      undoLastDrag();
      return;
    }
    // R = reset zoom, Shift+R = reset positions + zoom
    if (e.key === 'r' && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
      const svgId = getSvgId(currentLevel);
      if (svgId) resetZoom(svgId);
      return;
    }
    if (e.key === 'R' && e.shiftKey && !e.ctrlKey && !e.metaKey) {
      resetPositions();
      return;
    }
    // Build ordered list of all navigable levels: context, container views, component views, code
    const navLevels = ['context'];
    Object.keys(C4.levels.containers || {}).forEach(sId => navLevels.push('container:' + sId));
    Object.keys(C4.levels.components || {}).forEach(cId => navLevels.push('component:' + cId));
    navLevels.push('code');
    const keyNum = parseInt(e.key);
    if (keyNum >= 1 && keyNum <= 9) {
      const idx = keyNum - 1;
      if (idx < navLevels.length) switchLevel(navLevels[idx]);
      else switchLevel('code'); // last key always goes to code
    }
  });
}

// ===== Init =====
function init() {
  // Backward compat: normalize single container → containers dictionary
  if (C4.levels.container && !C4.levels.containers) {
    C4.levels.containers = { _default: C4.levels.container };
  }
  if (!C4.levels.containers) C4.levels.containers = {};
  if (!C4.levels.components) C4.levels.components = {};

  // Calculate positions for all levels
  calculateInitialPositions('context', C4.levels.context.elements);
  Object.keys(C4.levels.containers).forEach(sId => {
    calculateInitialPositions('container', C4.levels.containers[sId].elements);
  });
  Object.keys(C4.levels.components).forEach(cId => {
    calculateInitialPositions('component', C4.levels.components[cId].elements);
  });

  // Save initial positions for reset
  saveInitialPositions('context', C4.levels.context.elements);
  Object.keys(C4.levels.containers).forEach(sId => {
    saveInitialPositions('container:' + sId, C4.levels.containers[sId].elements);
  });
  Object.keys(C4.levels.components).forEach(cId => {
    saveInitialPositions('component:' + cId, C4.levels.components[cId].elements);
  });

  // Render all levels
  renderLevel('context');
  Object.keys(C4.levels.containers).forEach(sId => {
    renderLevel('container:' + sId);
  });
  Object.keys(C4.levels.components).forEach(cId => {
    renderLevel('component:' + cId);
  });
  renderCodeLevel();

  // Init interactions for all diagram levels
  const allLevels = [
    { svgId: 'svg-context', data: C4.levels.context, key: 'context' },
    ...Object.entries(C4.levels.containers).map(([sId, data]) => ({
      svgId: 'svg-container-' + sId, data, key: 'container:' + sId
    })),
    ...Object.entries(C4.levels.components).map(([cId, data]) => ({
      svgId: 'svg-component-' + cId, data, key: 'component:' + cId
    }))
  ];
  allLevels.forEach(({ svgId, data }) => {
    initDragAndDrop(svgId, data);
    initTooltips(svgId, data);
    initDrillDown(svgId, data);
    initKeyboardNav(svgId, data);
    initZoomPan(svgId);
  });

  initCodeOverlay();
  initDecisionHighlighting();
  initKeyboard();

  // Start on context level
  switchLevel('context');
}

init();

// ===== Theme Toggle =====
function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  const next = current === 'light' ? 'dark' : 'light';
  html.setAttribute('data-theme', next);
  // Update marker fill (CSS can't reliably style marker internals)
  document.querySelectorAll('#af polygon').forEach(p => p.setAttribute('fill', getComputedStyle(html).getPropertyValue('--arrow-color').trim()));
  // Re-render arrows to pick up CSS changes
  const svgId = currentLevel.startsWith('component:') ? 'svg-component-' + currentLevel.split(':')[1] : 'svg-' + currentLevel;
  const levelData = currentLevel.startsWith('component:') ? C4.levels.components[currentLevel.split(':')[1]] : C4.levels[currentLevel];
  if (levelData) { renderArrows(svgId, levelData); renderGroups(svgId, levelData); }
  // Persist preference
  try { localStorage.setItem('c4-theme', next); } catch(e) {}
}
// Restore saved theme
try { const saved = localStorage.getItem('c4-theme'); if (saved) document.documentElement.setAttribute('data-theme', saved); } catch(e) {}
```

## CSS to Include

The following CSS must be embedded in the `<style>` tag. This complements the engine above. Dark mode is the default; a light theme is available via `data-theme="light"` on `<html>`.

```css
/* ===== Theme Variables (Dark Default) ===== */
:root {
  --bg: #0d1117;
  --bg-nav: rgba(13, 17, 23, 0.82);
  --bg-panel: rgba(22, 27, 34, 0.78);
  --bg-card: rgba(255, 255, 255, 0.04);
  --border: rgba(255, 255, 255, 0.08);
  --border-hover: rgba(255, 255, 255, 0.18);
  --text: #e6edf3;
  --text-secondary: #8b949e;
  --text-muted: #6e7681;
  --accent: #58a6ff;
  --accent-bg: #1f6feb;
  --arrow-color: #8b949e;
  --arrow-label-bg: rgba(13, 17, 23, 0.88);
  --arrow-label-border: rgba(255, 255, 255, 0.1);
  --arrow-label-text: #c9d1d9;
  --tab-bg: rgba(255, 255, 255, 0.06);
  --tab-hover: rgba(255, 255, 255, 0.1);
  --tooltip-bg: rgba(30, 33, 40, 0.95);
  --tooltip-border: rgba(255, 255, 255, 0.08);
  --legend-bg: rgba(13, 17, 23, 0.8);
  --legend-border: rgba(255, 255, 255, 0.08);
  --legend-color: #8b949e;
  --panel-border: rgba(255, 255, 255, 0.06);
  --fr-border: rgba(206, 147, 216, 0.25);
  --nfr-border: rgba(255, 193, 7, 0.15);
  --dd-border: rgba(255, 193, 7, 0.15);
  --dd-hover-border: #daa520;
  --fr-must-bg: rgba(198, 40, 40, 0.15); --fr-must-text: #ef9a9a;
  --fr-should-bg: rgba(230, 81, 0, 0.15); --fr-should-text: #ffcc80;
  --fr-could-bg: rgba(106, 27, 154, 0.15); --fr-could-text: #ce93d8;
  --fr-wont-bg: rgba(97, 97, 97, 0.15); --fr-wont-text: #9e9e9e;
  --nfr-cat: #58a6ff;
  --nfr-metric: #c9d1d9;
  --nfr-approach: #8b949e;
  --dd-tradeoff: #f48fb1;
  --code-overlay-backdrop: rgba(0, 0, 0, 0.85);
  --highlight-stroke: #ffd700;
  --arrow-hover-stroke: #c9d1d9;
  --drag-hint-bg: rgba(255, 255, 255, 0.08);
  --drag-hint-text: #8b949e;
  --focus-ring: #58a6ff;
  --legend-line: #8b949e;
}

[data-theme="light"] {
  --bg: #ffffff;
  --bg-nav: rgba(250, 250, 250, 0.82);
  --bg-panel: rgba(255, 249, 230, 0.95);
  --bg-card: rgba(0, 0, 0, 0.02);
  --border: rgba(0, 0, 0, 0.1);
  --border-hover: rgba(0, 0, 0, 0.2);
  --text: #1a1a1a;
  --text-secondary: #555555;
  --text-muted: #888888;
  --accent: #1168BD;
  --accent-bg: #1168BD;
  --arrow-color: #555555;
  --arrow-label-bg: rgba(255, 255, 255, 0.92);
  --arrow-label-border: #dddddd;
  --arrow-label-text: #333333;
  --tab-bg: #f5f5f5;
  --tab-hover: #e8e8e8;
  --tooltip-bg: rgba(51, 51, 51, 0.95);
  --tooltip-border: transparent;
  --legend-bg: rgba(255, 255, 255, 0.9);
  --legend-border: #e0e0e0;
  --legend-color: #666666;
  --panel-border: #F0E0A0;
  --fr-border: #E1BEE7;
  --nfr-border: #F0E0A0;
  --dd-border: #F0E0A0;
  --dd-hover-border: #DAA520;
  --fr-must-bg: #FFCDD2; --fr-must-text: #C62828;
  --fr-should-bg: #FFE0B2; --fr-should-text: #E65100;
  --fr-could-bg: #E1BEE7; --fr-could-text: #6A1B9A;
  --fr-wont-bg: #E0E0E0; --fr-wont-text: #616161;
  --nfr-cat: #1168BD;
  --nfr-metric: #333333;
  --nfr-approach: #666666;
  --dd-tradeoff: #C62828;
  --code-overlay-backdrop: rgba(0, 0, 0, 0.8);
  --highlight-stroke: #DAA520;
  --arrow-hover-stroke: #333333;
  --drag-hint-bg: rgba(0, 0, 0, 0.6);
  --drag-hint-text: #ffffff;
  --focus-ring: #1168BD;
  --legend-line: #555555;
}

/* ===== Base ===== */
* { margin: 0; padding: 0; box-sizing: border-box; }
html { color-scheme: dark light; }
body { display: flex; flex-direction: column; height: 100vh; overflow: hidden; font-family: 'Inter','Segoe UI',system-ui,sans-serif; background: var(--bg); color: var(--text); transition: background 0.3s, color 0.3s; }

/* Skip Link */
.skip-link { position: absolute; left: -9999px; top: auto; width: 1px; height: 1px; overflow: hidden; z-index: 1000; background: var(--accent-bg); color: #fff; padding: 8px 16px; font-size: 14px; text-decoration: none; border-radius: 6px; }
.skip-link:focus { position: fixed; left: 16px; top: 16px; width: auto; height: auto; overflow: visible; }

/* Nav Bar — Glassmorphism */
.nav-bar { display: flex; align-items: center; gap: 12px; padding: 8px 16px; background: var(--bg-nav); backdrop-filter: blur(16px) saturate(1.4); -webkit-backdrop-filter: blur(16px) saturate(1.4); border-bottom: 1px solid var(--border); flex-shrink: 0; transition: background 0.3s, border-color 0.3s; }
.project-title { font-size: 16px; font-weight: 700; color: var(--text); letter-spacing: -0.01em; }
.breadcrumb { font-size: 12px; color: var(--text-muted); margin-left: 8px; }
.breadcrumb-link { cursor: pointer; color: var(--accent); }
.breadcrumb-link:hover { text-decoration: underline; }
.breadcrumb-sep { color: var(--text-muted); margin: 0 2px; }
.tabs { display: flex; gap: 4px; margin-left: auto; }
.tab { padding: 6px 14px; border: 1px solid var(--border); border-radius: 8px; background: var(--tab-bg); color: var(--text-secondary); font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.2s ease; }
.tab:hover { background: var(--tab-hover); color: var(--text); border-color: var(--border-hover); }
.tab.active { background: var(--accent-bg); color: #fff; border-color: transparent; box-shadow: 0 1px 8px rgba(88, 166, 255, 0.25); }
.nfr-toggle { padding: 6px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--tab-bg); color: var(--text-secondary); cursor: pointer; font-size: 12px; font-weight: 500; transition: all 0.2s ease; }
.nfr-toggle:hover { background: var(--tab-hover); color: var(--text); }
.theme-toggle { padding: 6px 10px; border: 1px solid var(--border); border-radius: 8px; background: var(--tab-bg); color: var(--text-secondary); cursor: pointer; font-size: 14px; line-height: 1; transition: all 0.2s ease; }
.theme-toggle:hover { background: var(--tab-hover); border-color: var(--border-hover); }

/* FR items */
.fr-item { margin-bottom: 10px; padding: 10px; background: var(--bg-card); border-radius: 8px; border: 1px solid var(--fr-border); transition: border-color 0.2s; }
.fr-item:hover { border-color: var(--border-hover); }
.fr-title { font-size: 13px; font-weight: 600; margin: 2px 0; color: var(--text); }
.fr-desc { font-size: 11px; color: var(--text-secondary); margin-top: 2px; }
.fr-priority { display: inline-block; font-size: 9px; font-weight: 700; text-transform: uppercase; padding: 2px 7px; border-radius: 4px; margin-left: 6px; }
.fr-priority.must { background: var(--fr-must-bg); color: var(--fr-must-text); }
.fr-priority.should { background: var(--fr-should-bg); color: var(--fr-should-text); }
.fr-priority.could { background: var(--fr-could-bg); color: var(--fr-could-text); }
.fr-priority.wont { background: var(--fr-wont-bg); color: var(--fr-wont-text); }
.fr-criteria { font-size: 10px; color: var(--text-muted); margin-top: 4px; padding-left: 12px; }
.fr-criteria li { margin-bottom: 2px; }

/* Canvas — subtle dot grid makes glassmorphism blur visible */
.canvas-area { flex: 1; overflow: auto; padding: 20px; position: relative; background: var(--bg); background-image: radial-gradient(circle, var(--border) 1px, transparent 1px); background-size: 32px 32px; transition: background 0.3s; }
.canvas-area svg { width: 100%; height: 100%; display: none; }
.canvas-area svg.active { display: block; }

/* Elements */
.c4-element { cursor: grab; transition: opacity 0.15s; }
.c4-element:active { cursor: grabbing; }
.c4-element.dragging { opacity: 0.85; filter: drop-shadow(0 4px 12px rgba(0,0,0,0.4)); }
.c4-element:focus { outline: 2px solid var(--focus-ring); outline-offset: 2px; }
.dd-highlight rect, .dd-highlight polygon, .dd-highlight ellipse { stroke: var(--highlight-stroke) !important; stroke-width: 3 !important; stroke-dasharray: 6,3; }

/* Arrows — styled via CSS, no hardcoded SVG colors */
.arrow-line { stroke: var(--arrow-color); transition: stroke 0.15s; }
.arrow-line:hover { stroke-width: 2.5; stroke: var(--arrow-hover-stroke); }
.arrow-label-bg { fill: var(--arrow-label-bg); stroke: var(--arrow-label-border); cursor: pointer; }
.arrow-label-text { fill: var(--arrow-label-text); }
#af polygon { fill: var(--arrow-color); transition: fill 0.3s; }

/* Tooltip — Glass */
.tooltip { display: none; position: fixed; background: var(--tooltip-bg); backdrop-filter: blur(12px) saturate(1.3); -webkit-backdrop-filter: blur(12px) saturate(1.3); border: 1px solid var(--tooltip-border); color: #fff; padding: 10px 14px; border-radius: 10px; font-size: 12px; max-width: 320px; z-index: 100; pointer-events: none; line-height: 1.5; box-shadow: 0 8px 32px rgba(0,0,0,0.35); }
.tooltip.arrow-tooltip { max-width: 360px; }

/* Requirements Panel — Glass */
.nfr-panel { position: fixed; right: 0; top: 45px; bottom: 0; width: 360px; background: var(--bg-panel); backdrop-filter: blur(16px) saturate(1.3); -webkit-backdrop-filter: blur(16px) saturate(1.3); border-left: 1px solid var(--panel-border); overflow-y: auto; padding: 16px; transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1), background 0.3s; z-index: 50; }
.nfr-panel.collapsed { transform: translateX(100%); }
.nfr-panel h3 { font-size: 14px; font-weight: 700; margin-bottom: 12px; color: var(--text); letter-spacing: -0.01em; }
.nfr-item { margin-bottom: 10px; padding: 10px; background: var(--bg-card); border-radius: 8px; border: 1px solid var(--nfr-border); transition: border-color 0.2s; }
.nfr-item:hover { border-color: var(--border-hover); }
.nfr-category { font-size: 10px; font-weight: 600; color: var(--nfr-cat); text-transform: uppercase; letter-spacing: 0.04em; }
.nfr-title { font-size: 13px; font-weight: 600; margin: 2px 0; color: var(--text); }
.nfr-metric { font-size: 12px; color: var(--nfr-metric); font-weight: 500; }
.nfr-approach { font-size: 11px; color: var(--nfr-approach); margin-top: 2px; }
.dd-item { margin-bottom: 10px; padding: 10px; background: var(--bg-card); border-radius: 8px; border: 1px solid var(--dd-border); cursor: default; transition: border-color 0.2s, box-shadow 0.2s; }
.dd-item:hover { border-color: var(--dd-hover-border); box-shadow: 0 0 12px rgba(218, 165, 32, 0.15); }
.dd-title { font-size: 13px; font-weight: 600; color: var(--text); }
.dd-tradeoff { font-size: 11px; color: var(--dd-tradeoff); font-style: italic; margin-top: 2px; }

/* Code Overlay */
.code-overlay { display: none; position: fixed; inset: 0; background: var(--code-overlay-backdrop); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); z-index: 200; justify-content: center; align-items: center; padding: 40px; }
.code-overlay.visible { display: flex; }
.code-box { background: #1E1E2E; border-radius: 14px; max-width: 800px; width: 100%; max-height: 80vh; overflow: auto; border: 1px solid rgba(255,255,255,0.06); box-shadow: 0 24px 80px rgba(0,0,0,0.5); }
.code-title { padding: 12px 16px; font-size: 14px; font-weight: 600; color: #CDD6F4; border-bottom: 1px solid #313244; }
.code-content { padding: 16px; font-family: 'Fira Code','JetBrains Mono','Consolas',monospace; font-size: 13px; color: #CDD6F4; white-space: pre; line-height: 1.6; overflow-x: auto; }
.close-btn { position: absolute; top: 20px; right: 30px; font-size: 28px; color: #999; background: none; border: none; cursor: pointer; transition: color 0.15s; }
.close-btn:hover { color: #fff; }

/* Code cards (in SVG) */
.code-card { cursor: pointer; }
.code-card:hover rect:first-child { stroke: #89B4FA; stroke-width: 2; }

/* Legend — Glass */
.legend { position: fixed; bottom: 16px; left: 16px; display: flex; gap: 16px; background: var(--legend-bg); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); padding: 8px 14px; border-radius: 10px; border: 1px solid var(--legend-border); font-size: 11px; color: var(--legend-color); z-index: 30; transition: background 0.3s, border-color 0.3s; }
.legend-item { display: flex; align-items: center; gap: 6px; }
.legend-line { width: 30px; height: 2px; background: var(--legend-line); }
.legend-line.async { background: repeating-linear-gradient(90deg, var(--legend-line) 0, var(--legend-line) 8px, transparent 8px, transparent 12px); }
.legend-line.bidir { background: var(--legend-line); position: relative; }
.legend-line.bidir::before, .legend-line.bidir::after { content: ''; position: absolute; top: -3px; border: 4px solid transparent; }
.legend-line.bidir::before { left: -4px; border-right-color: var(--legend-line); }
.legend-line.bidir::after { right: -4px; border-left-color: var(--legend-line); }

/* Drag Hint */
.drag-hint { position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%); background: var(--drag-hint-bg); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); color: var(--drag-hint-text); padding: 6px 14px; border-radius: 20px; font-size: 11px; z-index: 30; pointer-events: none; border: 1px solid var(--border); }

/* Print */
@media print {
  .nav-bar, .legend, .drag-hint, .tooltip, .code-overlay, .nfr-toggle, .theme-toggle, .skip-link { display: none; }
  .canvas-area { overflow: visible; padding: 0; }
  .canvas-area svg { display: block !important; page-break-inside: avoid; margin-bottom: 20px; }
  .nfr-panel { position: static; transform: none; width: 100%; page-break-before: always; border: 1px solid #ccc; background: #fff; backdrop-filter: none; }
  body { height: auto; overflow: visible; background: #fff; color: #000; }
}
```

## What the Generator Must Produce

The rendering engine above is **complete and static**. When generating an HTML file, only these parts are dynamic:

1. **`const C4 = { ... }`** — The data object built from `architecture.json`
2. **`{{FR_PANEL_HTML}}`** — FR items HTML for the aside
3. **`{{NFR_PANEL_HTML}}`** — NFR items HTML for the aside
4. **`{{DESIGN_DECISIONS_HTML}}`** — DD items with `data-elements` attribute
5. **`{{COMPONENT_SVGS}}`** — One `<svg id="svg-component-<id>">` per component view
6. **`{{COMPONENT_TABS}}`** — One `<button class="tab" data-level="component:<id>">` per component view
7. **ViewBox dimensions** — Calculated per level from element count and positions
8. **`{{PROJECT_NAME}}`** — From `project.name`

Everything else (CSS, JS engine, template structure) is copied verbatim from this reference.

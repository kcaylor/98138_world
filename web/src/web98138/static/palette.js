/* 98138.world palette chooser (feature 015). Hand-written, no build step, first-party only:
   it fetches this map's prebuilt cells.json from the site and recolors the preview in the page.
   No cookies, no storage, no other hosts; the state lives in the address fragment only.
   Preview only: parts lists, prices, build sheets and downloads keep the map's default colors.
   Not affiliated with or endorsed by The LEGO Group. */
(function (root) {
  'use strict';
  var MAX_CLASSES = 12;
  var LAYERS = ['land', 'ocean'];
  var PART = { land: '6141', ocean: '98138' };

  // ---- pure functions (also run by the web tests under Node) --------------------------------

  function classOf(v, inner) {            // bins: [lower, upper); below the first bound -> 0
    var k = 0;
    while (k < inner.length && v >= inner[k]) k++;
    return k;
  }

  function roundTo(v, d) { var f = Math.pow(10, d || 0); return Math.round(v * f) / f; }

  function layerValues(data, cls) {
    var L = data.layers[cls], out = [];
    if (!L.values) return out;
    for (var i = 0; i < L.values.length; i++) if (L.values[i] !== null && L.classes[i] >= 0) out.push(L.values[i]);
    return out;
  }

  function equalShareBounds(values, n, d) {   // n - 1 bounds giving n classes of equal size
    var sv = values.slice().sort(function (a, b) { return a - b; }), N = sv.length, out = [];
    for (var k = 1; k < n; k++) {
      var c = Math.min(Math.max(Math.round(k * N / n), 1), N - 1);
      out.push(roundTo((sv[c - 1] + sv[c]) / 2, d));
    }
    for (var j = 1; j < out.length; j++) {     // keep them strictly increasing on ties
      if (!(out[j] > out[j - 1])) out[j] = roundTo(out[j - 1] + Math.pow(10, -(d || 0)), d);
    }
    return out;
  }

  function spreadColors(colors, n) {          // n colors sampled evenly along the current ramp
    var m = colors.length, out = [];
    for (var i = 0; i < n; i++) out.push(colors[n === 1 ? 0 : Math.round(i * (m - 1) / (n - 1))]);
    return out;
  }

  function validBounds(b) {
    if (!Array.isArray(b)) return false;
    for (var i = 0; i < b.length; i++) {
      if (typeof b[i] !== 'number' || !isFinite(b[i])) return false;
      if (i && !(b[i] > b[i - 1])) return false;
    }
    return true;
  }

  function defaultState(data) {
    var s = { ice: 'data', shadow: data.shadow.color, layers: {} };
    LAYERS.forEach(function (c) { s.layers[c] = { colors: data.layers[c].colors.slice(), bounds: null }; });
    return s;
  }

  function sameState(a, b) { return JSON.stringify(a) === JSON.stringify(b); }

  function iceFlags(data) {                   // 1 = land ice, 2 = sea ice
    if (!data._ice) {
      var f = new Uint8Array(data.width * data.height);
      data.ice.land.forEach(function (i) { f[i] = 1; });
      data.ice.sea.forEach(function (i) { f[i] = 2; });
      data._ice = f;
    }
    return data._ice;
  }

  function layerClass(data, state, cls, i) {
    var L = data.layers[cls], st = state.layers[cls];
    if (st.bounds && L.values) return L.values[i] === null ? -1 : classOf(L.values[i], st.bounds);
    return L.classes[i];
  }

  function cellColors(data, state) {          // a color key per cell, row-major as hung
    var n = data.width * data.height, out = new Array(n), ice = iceFlags(data);
    for (var i = 0; i < n; i++) {
      var k = data.cells.charAt(i);
      if (k === 'S') out[i] = state.shadow;
      else if (state.ice === 'white' && ice[i]) out[i] = data.ice.color;
      else {
        var cls = k === 'L' ? 'land' : 'ocean';
        out[i] = state.layers[cls].colors[layerClass(data, state, cls, i)];
      }
    }
    return out;
  }

  function classShares(data, state, cls) {    // studs per class among the layer's data studs
    var want = cls === 'land' ? 'L' : 'O', ice = iceFlags(data);
    var n = state.layers[cls].colors.length, cells = [], total = 0, i;
    for (i = 0; i < n; i++) cells.push(0);
    for (i = 0; i < data.cells.length; i++) {
      if (data.cells.charAt(i) !== want || (state.ice === 'white' && ice[i])) continue;
      var c = layerClass(data, state, cls, i);
      if (c >= 0) { cells[c]++; total++; }
    }
    return cells.map(function (x) { return { cells: x, share: total ? x / total : 0 }; });
  }

  function encodeState(data, state) {
    var o = { m: data.recipe.id, i: state.ice === 'white' ? 1 : 0, s: state.shadow };
    LAYERS.forEach(function (c) { o[c] = { c: state.layers[c].colors, b: state.layers[c].bounds }; });
    return 'palette=' + encodeURIComponent(JSON.stringify(o));
  }

  function decodeState(data, text) {
    var fail = function (msg) { return { state: null, error: msg }; };
    var m = /(?:^#?|&)palette=([^&]*)/.exec(text || '');
    if (!m) return { state: null, error: null };
    var o;
    try { o = JSON.parse(decodeURIComponent(m[1])); } catch (e) { return fail('unreadable'); }
    if (!o || o.m !== data.recipe.id) return fail('made for another map');
    var keys = {};
    Object.keys(data.palette).forEach(function (p) {
      keys[p] = {};
      data.palette[p].forEach(function (r) { keys[p][r.key] = true; });
    });
    var s = { ice: o.i === 1 ? 'white' : 'data', shadow: o.s, layers: {} };
    if (o.i !== 0 && o.i !== 1) return fail('bad ice setting');
    if (!keys['98138'][o.s] || (!data.shadow.enabled && o.s !== data.shadow.color)) return fail('bad shadow color');
    for (var j = 0; j < LAYERS.length; j++) {
      var c = LAYERS[j], L = data.layers[c], x = o[c] || {};
      var colors = x.c, bounds = x.b === undefined ? null : x.b;
      if (!Array.isArray(colors) || colors.length < 1 || colors.length > MAX_CLASSES) return fail('bad colors');
      for (var k = 0; k < colors.length; k++) if (!keys[PART[c]][colors[k]]) return fail('unknown color');
      if (bounds === null) {
        if (colors.length !== L.colors.length) return fail('bad class count');
      } else if (!L.editable_classes || !validBounds(bounds) || bounds.length !== colors.length - 1) {
        return fail('bad bounds');
      }
      s.layers[c] = { colors: colors.slice(), bounds: bounds === null ? null : bounds.slice() };
    }
    return { state: s, error: null };
  }

  var core = { classOf: classOf, equalShareBounds: equalShareBounds, spreadColors: spreadColors,
    validBounds: validBounds, defaultState: defaultState, cellColors: cellColors,
    classShares: classShares, encodeState: encodeState, decodeState: decodeState };
  if (typeof module !== 'undefined' && module.exports) { module.exports = core; return; }

  // ---- the page -------------------------------------------------------------------------------

  var doc = root.document;
  var section = doc.getElementById('palette');
  if (!section || !root.fetch || !doc.createElement('canvas').getContext) return;

  function el(tag, attrs, kids) {
    var e = doc.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === 'text') e.textContent = attrs[k];
      else if (k === 'className') e.className = attrs[k];
      else e.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (c) { if (c) e.appendChild(c); });
    return e;
  }

  function fmt(v, d) {
    return Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function pct(x) { return (x * 100).toFixed(x > 0 && x < 0.1 ? 1 : 0) + '%'; }

  var data, state, base, info = {}, swatchCache = {};
  var status = section.querySelector('.pc-status');
  var img = doc.getElementById('preview-img');
  var STUD_PX = 10, STUD_DIAMETER = 0.9;   // as the built preview.png: round studs on black
  var canvas = el('canvas', { width: '1280', height: '800', className: 'stud-img', role: 'img', hidden: '' });

  function say(msg) { status.textContent = msg; }

  function rgbOf(part, key) { return info[part][key].rgb; }
  function swatch(part, key) {
    var s = el('span', { className: 'pc-swatch', 'aria-hidden': 'true' });
    s.style.backgroundColor = 'rgb(' + rgbOf(part, key).join(',') + ')';
    return s;
  }
  function colorLabel(part, key) {
    var r = info[part][key];
    return r.bricklink.name + (r.lego.name !== r.bricklink.name ? ' (LEGO ' + r.lego.name + ')' : '') +
      ' · L* ' + r.lightness + (r.in_kit ? ' · in the kit' : '');
  }

  function colorSelect(part, value, label, onChange) {
    var sel = el('select', { 'aria-label': label });
    data.palette[part].forEach(function (r) {
      var o = el('option', { value: r.key, text: colorLabel(part, r.key) });
      if (r.key === value) o.selected = true;
      sel.appendChild(o);
    });
    sel.addEventListener('change', function () { onChange(sel.value); });
    return sel;
  }

  function innerBounds(c) {
    var L = data.layers[c], st = state.layers[c];
    if (st.bounds) return st.bounds;
    return L.bounds ? L.bounds.slice(1, -1) : null;
  }

  function rangeText(c, i, n) {
    var L = data.layers[c];
    if (L.role === 'background') return L.class_labels[i] || L.cls;
    if (L.method === 'categorical') return 'design color: ' + info[PART[c]][L.categories[i]].lego.name;
    var b = innerBounds(c), d = L.decimals, u = L.units ? ' ' + L.units : '';
    if (n === 1) return 'all values';
    var t = i === 0 ? 'below ' + fmt(b[0], d) + u : i === n - 1 ? fmt(b[n - 2], d) + u + ' and above'
      : fmt(b[i - 1], d) + ' to ' + fmt(b[i], d) + u;
    return t + (!state.layers[c].bounds && L.bounds_source === 'built classes' ? ' (about)' : '');
  }

  function describe(c) {
    var L = data.layers[c];
    if (L.role === 'background') return 'Background layer: choose a color for each part of it.';
    if (L.method === 'categorical') return 'The official design, color for color: choose a color for each design color. Class bounds do not apply.';
    var t = 'Data layer (' + L.dataset + ', ' + L.method + ', ' + L.units + ').';
    if (state.layers[c].bounds) t += ' Custom bounds: each stud takes the class of its value, without the blend texture.';
    else if (L.texture === 'blend') t += ' Shown as built, with the blend texture.';
    if (L.no_value && L.no_value.length) {
      t += ' ' + L.no_value.length + ' studs have no source value and show the nearest value, as in the build (' +
        L.no_value_ice + ' of them in ice regions).';
    }
    return t;
  }

  var views = {};

  function buildLayer(c) {
    var L = data.layers[c], st = state.layers[c], v = views[c], part = PART[c];
    var body = v.body;
    while (body.firstChild) body.removeChild(body.firstChild);
    v.rows = [];
    var n = st.colors.length;
    if (L.editable_classes) {
      var b = innerBounds(c);
      var wrap = el('div', { className: 'pc-bounds' });
      if (n > 1) {
        wrap.appendChild(el('span', { className: 'pc-label', text: 'Bounds (' + L.units + ')' }));
        b.forEach(function (x, i) {
          var inp = el('input', { type: 'number', step: 'any', value: String(x), inputmode: 'decimal',
            'aria-label': 'Bound between class ' + (i + 1) + ' and ' + (i + 2) + ' (' + L.units + ')' });
          inp.addEventListener('change', function () { readBounds(c); });
          wrap.appendChild(inp);
        });
      }
      v.boundsMsg = el('p', { className: 'pc-error', role: 'alert' });
      body.appendChild(wrap);
      body.appendChild(v.boundsMsg);
      v.boundsWrap = wrap;
    }
    var tbody = el('tbody');
    for (var i = 0; i < n; i++) {
      (function (i) {
        var sw = swatch(part, st.colors[i]);
        var range = el('span', { text: rangeText(c, i, n) });
        var share = el('td', { className: 'num' });
        var lstar = el('td', { className: 'num' });
        var sel = colorSelect(part, st.colors[i], 'Color of class ' + (i + 1) + ', ' + rangeText(c, i, n), function (k) {
          st.colors[i] = k; changed();
        });
        tbody.appendChild(el('tr', {}, [el('th', { scope: 'row' }, [sw, range]), el('td', {}, [sel]), lstar, share]));
        v.rows.push({ sw: sw, range: range, share: share, lstar: lstar, sel: sel });
      })(i);
    }
    body.appendChild(el('div', { className: 'table-scroll' }, [el('table', { className: 'pc-table' }, [
      el('thead', {}, [el('tr', {}, [el('th', { scope: 'col', text: 'Class' }), el('th', { scope: 'col', text: 'Color (BrickLink, LEGO)' }),
        el('th', { scope: 'col', className: 'num', text: 'L*' }), el('th', { scope: 'col', className: 'num', text: 'Share' })])]),
      tbody])]));
  }

  function readBounds(c) {
    var v = views[c], inputs = v.boundsWrap.querySelectorAll('input'), b = [];
    for (var i = 0; i < inputs.length; i++) b.push(inputs[i].value.trim() === '' ? NaN : Number(inputs[i].value));
    var ok = validBounds(b);
    for (var j = 0; j < inputs.length; j++) inputs[j].setAttribute('aria-invalid', ok ? 'false' : 'true');
    if (!ok) { v.boundsMsg.textContent = 'Bounds must be numbers that increase from left to right; keeping the last valid ones.'; return; }
    v.boundsMsg.textContent = '';
    state.layers[c].bounds = b;
    changed();
  }

  function refreshLayer(c) {
    var st = state.layers[c], v = views[c], part = PART[c], shares = classShares(data, state, c);
    v.desc.textContent = describe(c);
    if (v.count) v.count.value = String(st.colors.length);
    v.rows.forEach(function (r, i) {
      r.sw.style.backgroundColor = 'rgb(' + rgbOf(part, st.colors[i]).join(',') + ')';
      r.range.textContent = rangeText(c, i, st.colors.length);
      r.sel.value = st.colors[i];
      r.sel.setAttribute('aria-label', 'Color of class ' + (i + 1) + ', ' + r.range.textContent);
      r.lstar.textContent = String(info[part][st.colors[i]].lightness);
      r.share.textContent = pct(shares[i].share);
    });
  }

  function setupLayer(c, holder) {
    var L = data.layers[c];
    var title = (c === 'land' ? 'Land: 1×1 round plates (part 6141)' : 'Ocean: 1×1 round tiles (part 98138)');
    var fs = el('fieldset', { className: 'pc-layer' }, [el('legend', { text: title })]);
    var v = views[c] = { desc: el('p', { className: 'note' }), body: el('div') };
    fs.appendChild(v.desc);
    if (L.editable_classes) {
      var id = 'pc-count-' + c;
      v.count = el('input', { id: id, type: 'number', min: '1', max: String(MAX_CLASSES), step: '1' });
      v.count.addEventListener('change', function () {
        var n = Math.round(Number(v.count.value));
        if (!(n >= 1 && n <= MAX_CLASSES)) { v.count.value = String(state.layers[c].colors.length); say('Choose 1 to 12 classes.'); return; }
        var st = state.layers[c];
        if (n === st.colors.length) return;
        st.bounds = equalShareBounds(layerValues(data, c), n, L.decimals);
        st.colors = spreadColors(st.colors, n);
        buildLayer(c);
        changed();
      });
      fs.appendChild(el('p', { className: 'pc-count' }, [el('label', { 'for': id, text: 'Number of classes (1–12) ' }), v.count]));
    }
    fs.appendChild(v.body);
    holder.appendChild(fs);
    buildLayer(c);
  }

  function draw() {
    var keys = cellColors(data, state), ctx = canvas.getContext('2d');
    var r = STUD_PX * STUD_DIAMETER / 2;
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    for (var i = 0; i < keys.length; i++) {
      var x = i % data.width, y = (i - x) / data.width;
      ctx.fillStyle = 'rgb(' + rgbOf(data.cells.charAt(i) === 'L' ? '6141' : '98138', keys[i]).join(',') + ')';
      ctx.beginPath();
      ctx.arc((x + 0.5) * STUD_PX, (y + 0.5) * STUD_PX, r, 0, 2 * Math.PI);
      ctx.fill();
    }
  }

  function markUsed() {
    var used = {};
    LAYERS.forEach(function (c) { state.layers[c].colors.forEach(function (k) { used[PART[c] + k] = true; }); });
    if (data.shadow.enabled) used['98138' + state.shadow] = true;
    Object.keys(swatchCache).forEach(function (id) { swatchCache[id].classList.toggle('used', !!used[id]); });
  }

  function changed(quiet) {
    var isDefault = sameState(state, base);
    if (isDefault) { canvas.hidden = true; img.hidden = false; } else { draw(); canvas.hidden = false; img.hidden = true; }
    LAYERS.forEach(refreshLayer);
    markUsed();
    var hash = isDefault ? '' : '#' + encodeState(data, state);
    try { root.history.replaceState(null, '', root.location.pathname + root.location.search + hash); } catch (e) { /* ignore */ }
    var links = doc.querySelectorAll('.combos a');
    for (var i = 0; i < links.length; i++) links[i].setAttribute('href', links[i].getAttribute('href').split('#')[0] + hash);
    if (!quiet) say(isDefault ? 'Preview shows the map\'s own colors.' : 'Preview updated.');
  }

  function paletteList(part, title) {
    var ul = el('ul', { className: 'pc-chips' });
    data.palette[part].forEach(function (r) {
      var li = el('li', { className: 'pc-chip' + (r.in_kit ? ' kit' : '') }, [swatch(part, r.key),
        el('span', { className: 'pc-chip-name', text: r.bricklink.name }), el('span', { className: 'pc-chip-l', text: String(r.lightness) })]);
      swatchCache[part + r.key] = li;
      ul.appendChild(li);
    });
    return el('div', {}, [el('h4', { text: title }), ul]);
  }

  function init(d) {
    data = d;
    Object.keys(data.palette).forEach(function (p) {
      info[p] = {};
      data.palette[p].forEach(function (r) { info[p][r.key] = r; });
    });
    base = defaultState(data);
    state = defaultState(data);
    var dec = decodeState(data, root.location.hash);
    if (dec.state) state = dec.state;
    canvas.setAttribute('aria-label', img.getAttribute('alt') + ', in the colors chosen below');
    img.parentNode.insertBefore(canvas, img);

    var holder = section.querySelector('.pc-layers');
    LAYERS.forEach(function (c) { setupLayer(c, holder); });

    var shadowBox = section.querySelector('.pc-shadow');
    if (data.shadow.enabled) {
      shadowBox.appendChild(el('label', { 'for': 'pc-shadow', text: 'Land shadow (' + data.shadow.cells + ' tiles just east of land) ' }));
      var sel = colorSelect('98138', state.shadow, 'Land shadow color', function (k) { state.shadow = k; changed(); });
      sel.id = 'pc-shadow';
      shadowBox.appendChild(sel);
    }

    var nLand = data.ice.land.length, nSea = data.ice.sea.filter(function (i) { return data.cells.charAt(i) === 'O'; }).length;
    section.querySelector('.pc-ice-note').textContent = 'Land ice: ' + nLand + ' plates (Antarctica, Greenland)' +
      (data.layers.land.role === 'background' ? ', already the land color here' : '') + '; sea ice: ' + nSea +
      ' tiles. The land shadow keeps its color. Shares count only studs that show data.';
    var radios = section.querySelectorAll('input[name="pc-ice"]');
    for (var i = 0; i < radios.length; i++) {
      radios[i].checked = radios[i].value === state.ice;
      radios[i].addEventListener('change', function (e) { if (e.target.checked) { state.ice = e.target.value; changed(); } });
    }
    section.querySelector('.pc-reset').addEventListener('click', function () {
      state = defaultState(data);
      LAYERS.forEach(buildLayer);
      for (var j = 0; j < radios.length; j++) radios[j].checked = radios[j].value === 'data';
      var s = doc.getElementById('pc-shadow');
      if (s) s.value = state.shadow;
      changed();
    });
    var pal = section.querySelector('.pc-swatches');
    pal.appendChild(paletteList('98138', 'Ocean tiles (part 98138), light to dark'));
    pal.appendChild(paletteList('6141', 'Land plates (part 6141), light to dark'));

    section.hidden = false;
    changed(true);
    if (dec.error) say('The colors in this link do not fit this map (' + dec.error + '); showing the map\'s own colors.');
  }

  root.fetch(section.getAttribute('data-cells'), { credentials: 'omit' })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(init)
    .catch(function () {
      section.hidden = false;
      say('The color chooser could not load; the preview shows the map\'s own colors.');
      var parts = section.querySelectorAll('fieldset, .pc-actions, details');
      for (var i = 0; i < parts.length; i++) parts[i].hidden = true;
    });
})(typeof window !== 'undefined' ? window : this);

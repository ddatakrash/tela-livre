/*
 * Tela Livre para LG: a tela inicial. Fotos de paisagem trocando ao fundo; saudação, hora, data e clima no alto;
 * Entradas e Configurações no canto; os apps favoritos e "Todos os apps" embaixo.
 * ES5 puro, como o resto: as TVs rodam um Chromium antigo. Fala com a TV pelo tv.js (do Free My TV, MIT).
 */
(function () {
  'use strict';

  var C = window.CONFIG || {};
  var DOCK = C.dock || [];
  var PHOTOS = C.photos || [];
  var COLS = 6;   // colunas na folha de todos os apps
  var WEEK = ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado'];
  var MONTH = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro',
    'novembro', 'dezembro'];

  function $(id) { return document.getElementById(id); }
  function pad(n) { return n < 10 ? '0' + n : '' + n; }
  function el(tag, cls) { var e = document.createElement(tag); if (cls) e.className = cls; return e; }

  // MARK: - Hora e data

  function tick() {
    var d = new Date(), h = d.getHours();
    $('greeting').textContent = h >= 5 && h < 12 ? 'Bom dia' : h >= 12 && h < 18 ? 'Boa tarde' : 'Boa noite';
    $('clock').textContent = pad(h) + ':' + pad(d.getMinutes());
    $('weekday').textContent = WEEK[d.getDay()];
    $('day').textContent = d.getDate() + ' de ' + MONTH[d.getMonth()];
  }

  // MARK: - Clima (Open-Meteo, sem chave)

  function symbolFor(code, day) {
    if (code === 0) return day ? 'sunny' : 'clear_night';
    if (code <= 2) return day ? 'partly_cloudy_day' : 'partly_cloudy_night';
    if (code === 3) return 'cloud';
    if (code === 45 || code === 48) return 'foggy';
    if (code >= 95) return 'thunderstorm';
    if ((code >= 71 && code <= 77) || code === 85 || code === 86) return 'snowflake';
    return 'rainy';
  }

  function weather() {
    if (C.latitude === undefined) return;
    var url = 'https://api.open-meteo.com/v1/forecast?latitude=' + C.latitude + '&longitude=' + C.longitude +
      '&current=temperature_2m,weather_code,is_day&timezone=auto';
    var x = new XMLHttpRequest();
    x.open('GET', url);
    x.timeout = 15000;
    x.onload = function () {
      var cur = null;
      try { cur = JSON.parse(x.responseText).current; } catch (e) {}
      if (!cur) return;
      $('wicon').src = 'symbols/' + symbolFor(cur.weather_code, cur.is_day === 1) + '.png';
      $('wtemp').textContent = Math.round(cur.temperature_2m) + '°';
      $('wcity').textContent = C.city || '';
      $('weather').className = 'on';
    };
    x.send();
  }

  // MARK: - Fotos de fundo

  var photoAt = 0, front = 'photoA';
  function nextPhoto() {
    if (!PHOTOS.length) return;
    var src = PHOTOS[photoAt++ % PHOTOS.length];
    var back = front === 'photoA' ? 'photoB' : 'photoA';
    var img = new Image();
    img.onload = function () {
      $(back).style.backgroundImage = 'url("' + src + '")';
      $(back).className = 'photo on';
      $(front).className = 'photo';
      front = back;
    };
    img.src = src;
  }

  // MARK: - Apps

  var installed = [];   // [{id, title, icon, color}] da TV

  function iconOf(id) {
    for (var i = 0; i < installed.length; i++) if (installed[i].id === id) return installed[i];
    return null;
  }

  function appTile(app, logo, bg) {
    var t = el('div', 'tile');
    var tv = iconOf(app.id);
    if (logo) {
      t.style.background = bg || '#fff';
      var img = el('img', 'logo');
      img.src = logo;
      t.appendChild(img);
    } else if (tv && tv.icon) {
      t.className += ' hasicon';
      t.style.background = tv.color || bg || '#222';
      var full = el('img', 'tvicon');
      full.src = tv.icon;
      t.appendChild(full);
    } else {
      t.style.background = bg || tv && tv.color || '#2A3442';
      var n = el('div', 'name');
      n.textContent = app.title;
      t.appendChild(n);
    }
    return t;
  }

  function open(id, title) {
    TV.launch(id, null, function (ok) {
      if (!ok) toast('Não consegui abrir ' + (title || id) + '. Ele está instalado?');
    });
  }

  var tiles = [];
  function renderDock() {
    var dock = $('dock');
    dock.innerHTML = '';
    tiles = [];
    for (var i = 0; i < DOCK.length; i++) {
      var t = appTile(DOCK[i], DOCK[i].logo, DOCK[i].bg);
      dock.appendChild(t);
      tiles.push({el: t, title: DOCK[i].title, run: (function (a) { return function () { open(a.id, a.title); }; })(DOCK[i])});
    }
    var all = el('div', 'tile all');
    var ic = el('img');
    ic.src = 'symbols/apps.png';
    all.appendChild(ic);
    dock.appendChild(all);
    tiles.push({el: all, title: 'Todos os apps', run: function () { showAllApps(); }});
  }

  // MARK: - Folha (todos os apps, entradas)

  var sheetItems = [];
  function showSheet(title, items) {
    $('sheetTitle').textContent = title;
    var grid = $('sheetGrid');
    grid.innerHTML = '';
    grid.scrollTop = 0;
    sheetItems = items;
    for (var i = 0; i < items.length; i++) grid.appendChild(items[i].el);
    $('sheet').className = '';
    $('stage').className = 'sheetOpen';
    st.zone = 'sheet';
    st.sheet = 0;
    focus();
  }

  function hideSheet() {
    $('sheet').className = 'hidden';
    $('stage').className = '';
    st.zone = 'dock';
    focus();
  }

  function showAllApps() {
    var list = installed.slice().sort(function (a, b) { return a.title.localeCompare(b.title); });
    var items = list.map(function (a) {
      var t = appTile(a, '', a.color);
      var cap = el('div', 'cap');
      cap.textContent = a.title;
      t.appendChild(cap);
      return {el: t, run: function () { open(a.id, a.title); }};
    });
    if (!items.length) { toast('A TV ainda não mostrou a lista de apps'); return; }
    showSheet('Todos os apps', items);
  }

  function showInputs() {
    TV.inputs(function (list) {
      var items = list.map(function (x) {
        var t = el('div', 'tile input' + (x.connected ? '' : ' off'));
        var img = el('img');
        img.src = 'symbols/' + (x.symbol || 'hdmi') + '.png';
        var n = el('div', 'name');
        n.textContent = x.label || 'TV';
        t.appendChild(img);
        t.appendChild(n);
        return {el: t, run: function () { open(x.id, x.label || 'TV'); }};
      });
      showSheet('Entradas', items);
    });
  }

  // MARK: - Foco e controle remoto

  var st = {zone: 'dock', dock: 0, corner: 0, sheet: 0};
  var corner = [
    {el: $('btnInputs'), run: showInputs},
    {el: $('btnSettings'), run: function () { TV.settings(function (ok) { if (!ok) toast('Não consegui abrir as configurações'); }); }}
  ];

  function focus() {
    var i;
    for (i = 0; i < tiles.length; i++) tiles[i].el.className = tiles[i].el.className.replace(/ ?focus/g, '') + (st.zone === 'dock' && i === st.dock ? ' focus' : '');
    for (i = 0; i < corner.length; i++) corner[i].el.className = 'round' + (st.zone === 'corner' && i === st.corner ? ' focus' : '');
    for (i = 0; i < sheetItems.length; i++) sheetItems[i].el.className = sheetItems[i].el.className.replace(/ ?focus/g, '') + (st.zone === 'sheet' && i === st.sheet ? ' focus' : '');
    $('dockLabel').textContent = st.zone === 'dock' && tiles[st.dock] ? tiles[st.dock].title : '';
    $('dockLabel').className = st.zone === 'dock' ? 'on' : '';
    $('cornerLabel').textContent = st.zone === 'corner' ? corner[st.corner].el.getAttribute('data-label') : '';
    $('cornerLabel').className = st.zone === 'corner' ? 'on' : '';
    if (st.zone === 'sheet' && sheetItems[st.sheet]) {   // rola a folha para a linha em foco
      var row = Math.floor(st.sheet / COLS);
      $('sheetGrid').scrollTop = Math.max(0, row - 2) * 199;
    }
  }

  function move(dx, dy) {
    if (st.zone === 'dock') {
      if (dy < 0) { st.zone = 'corner'; st.corner = corner.length - 1; }
      else st.dock = Math.max(0, Math.min(tiles.length - 1, st.dock + dx));
    } else if (st.zone === 'corner') {
      if (dy > 0) st.zone = 'dock';
      else st.corner = Math.max(0, Math.min(corner.length - 1, st.corner + dx));
    } else {
      var n = st.sheet + dx + dy * COLS;
      if (n >= 0 && n < sheetItems.length) st.sheet = n;
      else if (dy > 0 && Math.floor(st.sheet / COLS) < Math.floor((sheetItems.length - 1) / COLS)) st.sheet = sheetItems.length - 1;
    }
    focus();
  }

  function ok() {
    var item = st.zone === 'dock' ? tiles[st.dock] : st.zone === 'corner' ? corner[st.corner] : sheetItems[st.sheet];
    if (item) item.run();
  }

  document.addEventListener('keydown', function (e) {
    var k = e.keyCode, K = TV.keys;
    if (k === K.left) move(-1, 0);
    else if (k === K.right) move(1, 0);
    else if (k === K.up) move(0, -1);
    else if (k === K.down) move(0, 1);
    else if (k === K.ok) ok();
    else if (k === K.back || k === 8 || k === 27) {
      if (st.zone === 'sheet') hideSheet();
      else if (st.zone === 'corner') { st.zone = 'dock'; focus(); }
      else TV.back();
    } else return;
    e.preventDefault();
  });

  var toastTimer = null;
  function toast(text) {
    $('toast').textContent = text;
    $('toast').className = 'on';
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { $('toast').className = ''; }, 3500);
  }

  // MARK: - Início

  function loadApps() {
    TV.apps(function (list) {
      installed = list || [];
      var keep = st.zone;
      renderDock();
      st.zone = keep;
      focus();
    });
  }

  function reopened() {
    if (window.PalmSystem && window.PalmSystem.activate) window.PalmSystem.activate();
    if (st.zone === 'sheet') { $('sheet').className = 'hidden'; $('stage').className = ''; }
    st.zone = 'dock';
    st.dock = 0;
    focus();
    loadApps();
  }

  document.addEventListener('webOSRelaunch', reopened);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) { tick(); weather(); } });

  tick();
  renderDock();
  focus();
  loadApps();
  weather();
  nextPhoto();
  setInterval(tick, 5000);
  setInterval(weather, 15 * 60000);
  if (PHOTOS.length > 1) setInterval(nextPhoto, (C.photoSeconds || 60) * 1000);

  window.TelaLivreLG = {state: st, move: move, ok: ok, showAllApps: showAllApps, showInputs: showInputs};
})();

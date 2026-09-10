(() => {
  const KEY = 'c2_server_audio_device_v1';
  function load() {
    try { return localStorage.getItem(KEY) || ''; } catch (e) { return ''; }
  }
  function save(v) { try { localStorage.setItem(KEY, v); window.dispatchEvent(new CustomEvent('serverAudioDeviceChanged', { detail: v })); } catch (e) {} }

  async function fetchDevices() {
    try {
      const res = await fetch('/system/audio-devices');
      if (!res.ok) return [];
      const j = await res.json();
      return j.cards || [];
    } catch (e) { return []; }
  }

  function createModal() {
    const modal = document.createElement('div');
    modal.id = 'sound-settings-modal';
    modal.className = 'fixed inset-0 bg-black/50 flex items-center justify-center hidden';
    modal.innerHTML = `
      <div class="bg-zinc-900 text-zinc-100 rounded p-4 w-96">
        <h3 class="font-semibold mb-2">Sound Settings</h3>
        <div id="server-audio-list" class="mb-3 max-h-48 overflow-auto"></div>
        <div class="flex justify-end gap-2">
          <button id="sound-settings-cancel" class="px-3 py-1 bg-zinc-700 rounded">Cancel</button>
          <button id="sound-settings-save" class="px-3 py-1 bg-emerald-600 rounded">Save</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
    return modal;
  }

  async function openModal() {
    let modal = document.getElementById('sound-settings-modal');
    if (!modal) modal = createModal();
    modal.classList.remove('hidden');

    const list = modal.querySelector('#server-audio-list');
    list.innerHTML = 'Loading...';
    const cards = await fetchDevices();
    list.innerHTML = '';
    const cur = load();
    const ul = document.createElement('ul');
    ul.className = 'space-y-2';
    if (cards.length === 0) {
      list.textContent = 'No ALSA devices found.';
    }
    cards.forEach(c => {
      const li = document.createElement('li');
      const h = document.createElement('div');
      h.className = 'font-medium';
      h.textContent = `Card ${c.card}: ${c.name}`;
      li.appendChild(h);
      const inner = document.createElement('div');
      inner.className = 'ml-2';
      c.devices.forEach(d => {
        const id = `card${c.card}_dev${d.device}`;
        const label = document.createElement('label');
        label.className = 'flex items-center gap-2';
        const inp = document.createElement('input');
        inp.type = 'radio';
        inp.name = 'server-audio-device';
        inp.value = `hw:Card${c.card},${d.device}`;
        if (inp.value === cur) inp.checked = true;
        const span = document.createElement('span');
        span.textContent = `${d.name} (device ${d.device})`;
        label.appendChild(inp);
        label.appendChild(span);
        inner.appendChild(label);
      });
      li.appendChild(inner);
      ul.appendChild(li);
    });
    list.appendChild(ul);

    modal.querySelector('#sound-settings-cancel').onclick = () => { modal.classList.add('hidden'); };
    modal.querySelector('#sound-settings-save').onclick = () => {
      const sel = modal.querySelector('input[name="server-audio-device"]:checked');
      if (sel) save(sel.value);
      modal.classList.add('hidden');
    };
  }

  // attach open button
  function init() {
    const btn = document.getElementById('open-sound-settings');
    if (btn) btn.addEventListener('click', openModal);
    // expose getter
    window.getServerAudioDevice = function() { return load() || 'default'; };
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();

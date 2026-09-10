(() => {
  const KEY = 'c2_radio_presets_v1';

  async function loadAll() {
    // try server first
    try {
      const res = await fetch('/system/presets');
      if (res.ok) {
        const j = await res.json();
        if (j && (j.sdr1 || j.sdr2)) return j;
      }
    } catch (e) {
      // ignore and fallback to local
    }
    try {
      const s = localStorage.getItem(KEY);
      if (!s) return { sdr1: [], sdr2: [] };
      return JSON.parse(s);
    } catch (e) {
      return { sdr1: [], sdr2: [] };
    }
  }

  async function saveAll(obj) {
    // save local copy
    try { localStorage.setItem(KEY, JSON.stringify(obj)); } catch (e) {}
    // try server
    try {
      await fetch('/system/presets', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(obj) });
    } catch (e) {
      // ignore
    }
  }

  async function getPresets(streamId) {
    const all = await loadAll();
    return all[streamId] || [];
  }

  async function setPresets(streamId, arr) {
    const all = await loadAll();
    all[streamId] = arr;
    await saveAll(all);
  }

  async function populateSelect(streamId) {
    const sel = document.getElementById(`${streamId}-presets`);
    if (!sel) return;
    const presets = await getPresets(streamId);
    sel.innerHTML = '';
    const empty = document.createElement('option');
    empty.value = '';
    empty.textContent = '-- presets --';
    sel.appendChild(empty);
    for (const p of presets) {
      const o = document.createElement('option');
      o.value = p.name;
      o.textContent = `${p.name} — ${p.mhz} MHz`;
      sel.appendChild(o);
    }
  }

  async function savePreset(streamId, name, mhz) {
    if (!name) return false;
    const presets = await getPresets(streamId);
    const filtered = presets.filter(p => p.name !== name);
    filtered.push({ name, mhz: mhz });
    await setPresets(streamId, filtered);
    await populateSelect(streamId);
    return true;
  }

  async function removePreset(streamId, name) {
    if (!name) return false;
    const presets = (await getPresets(streamId)).filter(p => p.name !== name);
    await setPresets(streamId, presets);
    await populateSelect(streamId);
    return true;
  }

  document.addEventListener('DOMContentLoaded', () => {
    ['sdr1', 'sdr2'].forEach((sid) => populateSelect(sid));

    // sdr1 handlers
    const s1save = document.getElementById('sdr1-save-preset');
    const s1apply = document.getElementById('sdr1-apply-preset');
    const s1remove = document.getElementById('sdr1-remove-preset');
    const s1sel = document.getElementById('sdr1-presets');
    const s1in = document.getElementById('sdr1-freq');
    if (s1save) s1save.addEventListener('click', async () => {
      const mhz = s1in.value.trim();
      if (!mhz) return alert('Enter MHz to save');
      const name = prompt('Preset name:', mhz + 'MHz');
      if (!name) return;
      await savePreset('sdr1', name, mhz);
    });
    if (s1apply) s1apply.addEventListener('click', async () => {
      const name = s1sel.value;
      if (!name) return alert('Select a preset');
      const p = (await getPresets('sdr1')).find(x => x.name === name);
      if (!p) return;
      s1in.value = p.mhz;
      // trigger set button
      const btn = document.getElementById('sdr1-set');
      if (btn) btn.click();
    });
    if (s1remove) s1remove.addEventListener('click', async () => {
      const name = s1sel.value;
      if (!name) return alert('Select a preset');
      if (!confirm(`Remove preset ${name}?`)) return;
      await removePreset('sdr1', name);
    });

    // sdr2 handlers
    const s2save = document.getElementById('sdr2-save-preset');
    const s2apply = document.getElementById('sdr2-apply-preset');
    const s2remove = document.getElementById('sdr2-remove-preset');
    const s2sel = document.getElementById('sdr2-presets');
    const s2in = document.getElementById('sdr2-freq');
    if (s2save) s2save.addEventListener('click', async () => {
      const mhz = s2in.value.trim();
      if (!mhz) return alert('Enter MHz to save');
      const name = prompt('Preset name:', mhz + 'MHz');
      if (!name) return;
      await savePreset('sdr2', name, mhz);
    });
    if (s2apply) s2apply.addEventListener('click', async () => {
      const name = s2sel.value;
      if (!name) return alert('Select a preset');
      const p = (await getPresets('sdr2')).find(x => x.name === name);
      if (!p) return;
      s2in.value = p.mhz;
      const btn = document.getElementById('sdr2-set');
      if (btn) btn.click();
    });
    if (s2remove) s2remove.addEventListener('click', async () => {
      const name = s2sel.value;
      if (!name) return alert('Select a preset');
      if (!confirm(`Remove preset ${name}?`)) return;
      await removePreset('sdr2', name);
    });

    // update selects when presets change in other tabs
    window.addEventListener('storage', (ev) => {
      if (ev.key === KEY) {
        populateSelect('sdr1');
        populateSelect('sdr2');
      }
    });
  });

})();

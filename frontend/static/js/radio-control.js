(() => {
  async function apiPost(path) {
    const res = await fetch(path, { method: 'POST' });
    return res.json();
  }

  async function apiGet(path) {
    const res = await fetch(path);
    return res.json();
  }

  async function setFrequency(streamId, mhz) {
    const n = parseFloat(mhz);
    if (isNaN(n)) return { ok: false, error: 'invalid MHz' };
    const hz = Math.round(n * 1e6);
    return apiPost(`/sdr/${streamId}/frequency?hz=${hz}`);
  }

  async function refreshCurrent(streamId) {
    try {
      const j = await apiGet(`/sdr/${streamId}/frequency`);
      const el = document.getElementById(`${streamId}-current`);
      if (el) {
        if (j && typeof j.frequency === 'number') {
          el.innerText = `${(j.frequency/1e6).toFixed(6)} MHz`;
        } else {
          el.innerText = '-';
        }
      }
    } catch (e) {
      // ignore
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    const s1btn = document.getElementById('sdr1-set');
    const s1in = document.getElementById('sdr1-freq');
    const s2btn = document.getElementById('sdr2-set');
    const s2in = document.getElementById('sdr2-freq');

    if (s1btn && s1in) {
      s1btn.addEventListener('click', async () => {
        s1btn.disabled = true;
        const r = await setFrequency('sdr1', s1in.value.trim());
        if (r && r.ok) await refreshCurrent('sdr1');
        s1btn.disabled = false;
      });
      s1in.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') s1btn.click();
      });
    }

    if (s2btn && s2in) {
      s2btn.addEventListener('click', async () => {
        s2btn.disabled = true;
        const r = await setFrequency('sdr2', s2in.value.trim());
        if (r && r.ok) await refreshCurrent('sdr2');
        s2btn.disabled = false;
      });
      s2in.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') s2btn.click();
      });
    }

    // initial load
    refreshCurrent('sdr1');
    refreshCurrent('sdr2');
  });

})();

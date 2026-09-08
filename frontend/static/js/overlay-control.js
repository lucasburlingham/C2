(() => {
  const POLL_INTERVAL = 2000;

  async function api(path, method = 'GET', body = null) {
    const opts = { method, headers: {} };
    if (body && (method === 'POST' || method === 'PUT')) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(path, opts);
    return res.json();
  }

  async function startOverlay(streamId) {
    const engineEl = document.getElementById(`${streamId}-engine`);
    const engine = engineEl ? engineEl.value : 'ffmpeg';
    const outEl = document.getElementById(`${streamId}-out-url`);
    const outUrl = outEl ? outEl.value.trim() || 'udp://127.0.0.1:5004' : 'udp://127.0.0.1:5004';
    const params = new URLSearchParams({ engine, audio_device: 'default', out_url: outUrl });
    const resp = await fetch(`/sdr/${streamId}/overlay/start?${params.toString()}`, { method: 'POST' });
    return resp.json();
  }

  async function stopOverlay(streamId) {
    const resp = await fetch(`/sdr/${streamId}/overlay/stop`, { method: 'POST' });
    return resp.json();
  }

  async function getStatus(streamId) {
    const res = await fetch(`/sdr/${streamId}/overlay/status`);
    return res.json();
  }

  function setStatusText(streamId, txt) {
    const el = document.getElementById(`${streamId}-overlay-status`);
    if (el) el.innerText = txt;
  }

  // attach buttons
  document.addEventListener('click', async (e) => {
    const startBtn = e.target.closest('.start-overlay');
    const stopBtn = e.target.closest('.stop-overlay');
    if (startBtn) {
      const sid = startBtn.getAttribute('data-stream');
      setStatusText(sid, 'starting...');
      const r = await startOverlay(sid);
      setStatusText(sid, r.ok ? `running (pid ${r.pid})` : `error: ${r.error}`);
    }
    if (stopBtn) {
      const sid = stopBtn.getAttribute('data-stream');
      setStatusText(sid, 'stopping...');
      const r = await stopOverlay(sid);
      setStatusText(sid, r.ok ? 'stopped' : `error: ${r.error}`);
    }
  });

  // poll statuses
  const STREAMS = ['sdr1', 'sdr2'];
  async function poll() {
    for (const s of STREAMS) {
      try {
        const st = await getStatus(s);
        if (st.ok && st.running) setStatusText(s, `running (pid ${st.pid})`);
        else if (st.ok) setStatusText(s, 'not running');
        else setStatusText(s, 'unknown');
      } catch (e) {
        setStatusText(s, 'error');
      }
    }
  }

  setInterval(poll, POLL_INTERVAL);
  // initial poll
  poll();

  // poll logs for running overlays
  async function fetchLogs(streamId, lines = 200) {
    try {
      const res = await fetch(`/sdr/${streamId}/overlay/logs?lines=${lines}`);
      const j = await res.json();
      const pre = document.getElementById(`${streamId}-overlay-log`);
      if (!pre) return;
      if (j.ok) {
        pre.textContent = j.logs || '';
        pre.scrollTop = pre.scrollHeight;
      } else {
        pre.textContent = `No logs: ${j.error || ''}`;
      }
    } catch (e) {
      // ignore
    }
  }

  setInterval(() => {
    for (const s of STREAMS) fetchLogs(s, 300);
  }, 3000);

  // initial logs
  for (const s of STREAMS) fetchLogs(s, 300);

})();

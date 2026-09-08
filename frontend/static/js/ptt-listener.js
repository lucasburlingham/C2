let isPttActive = false;

document.addEventListener('keydown', async (e) => {
    if (e.code === 'Space' && !isPttActive && document.activeElement.tagName !== 'INPUT') {
        e.preventDefault();
        isPttActive = true;
        try {
            await fetch('/radio/ptt?keying=true', { method: 'POST' });
        } catch (err) {
            console.error('PTT error', err);
        }
    }
});

document.addEventListener('keyup', async (e) => {
    if (e.code === 'Space' && isPttActive) {
        e.preventDefault();
        isPttActive = false;
        try {
            await fetch('/radio/ptt?keying=false', { method: 'POST' });
        } catch (err) {
            console.error('PTT error', err);
        }
    }
});

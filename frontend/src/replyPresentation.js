// Presentation only: the server saves the complete reply before this runs.
const segmenter = typeof Intl.Segmenter === 'function'
  ? new Intl.Segmenter('ko', { granularity: 'grapheme' }) : null;

export function prefersReducedMotion() {
  return globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
}

export function revealBoundaries(text) {
  const boundaries = [];
  let end = 0;
  let weight = 0;
  for (const part of text.split(/(```[\s\S]*?```)/g)) {
    if (!part) continue;
    if (part.startsWith('```') && part.endsWith('```')) {
      end += part.length;
      weight += Math.min(45, [...(segmenter?.segment(part) ?? part)].length);
      boundaries.push({ end, weight });
    } else {
      for (const item of segmenter?.segment(part) ?? part) {
        end += typeof item === 'string' ? item.length : item.segment.length;
        boundaries.push({ end, weight: ++weight });
      }
    }
  }
  return boundaries;
}

export function createReplyPresentation({ onUpdate, minimumDelay = 900 + Math.random() * 500,
  reducedMotion = prefersReducedMotion() || !segmenter }) {
  const started = performance.now();
  let timeout = null;
  let frame = null;
  let resolve = null;
  let finished = false;
  let cancelled = false;
  let reply = '';
  let lastEnd = -1;

  function finish(completed) {
    if (finished) return;
    finished = true;
    if (timeout !== null) clearTimeout(timeout);
    if (frame !== null) cancelAnimationFrame(frame);
    globalThis.document?.removeEventListener('visibilitychange', onVisibility);
    resolve?.(completed);
  }

  function skip() {
    if (finished || !resolve) return;
    onUpdate({ phase: 'typing', visibleText: reply, complete: true });
    finish(true);
  }

  function onVisibility() {
    if (globalThis.document?.hidden) skip();
  }

  function beginTyping() {
    if (finished) return;
    if (reducedMotion || globalThis.document?.hidden) { skip(); return; }
    const boundaries = revealBoundaries(reply);
    const total = boundaries.at(-1)?.weight ?? 0;
    const duration = Math.min(4500, Math.max(400, total / 45 * 1000));
    const typingStarted = performance.now();
    let index = 0;
    let end = 0;
    onUpdate({ phase: 'typing', visibleText: '', complete: false });
    function tick(now) {
      if (finished) return;
      const progress = Math.min(1, Math.max(0, (now - typingStarted) / duration));
      const target = total * progress;
      while (index < boundaries.length && boundaries[index].weight <= target) {
        end = boundaries[index++].end;
      }
      if (progress === 1) end = reply.length;
      if (end !== lastEnd) {
        lastEnd = end;
        onUpdate({ phase: 'typing', visibleText: reply.slice(0, end), complete: progress === 1 });
      }
      if (progress === 1) finish(true);
      else frame = requestAnimationFrame(tick);
    }
    timeout = setTimeout(skip, duration);
    frame = requestAnimationFrame(tick);
  }

  return {
    present(text) {
      if (finished) return Promise.resolve(false);
      reply = text;
      return new Promise(done => {
        resolve = done;
        globalThis.document?.addEventListener('visibilitychange', onVisibility);
        const remaining = Math.max(0, minimumDelay - (performance.now() - started));
        if (remaining && !globalThis.document?.hidden) timeout = setTimeout(beginTyping, remaining);
        else beginTyping();
      });
    },
    skip,
    get cancelled() { return cancelled; },
    cancel() { if (!finished) cancelled = true; finish(false); },
  };
}

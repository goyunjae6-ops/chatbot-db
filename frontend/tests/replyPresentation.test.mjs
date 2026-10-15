import test from 'node:test';
import assert from 'node:assert/strict';
import { createReplyPresentation, revealBoundaries } from '../src/replyPresentation.js';

async function withClock(run) {
  const keys = ['performance', 'setTimeout', 'clearTimeout', 'requestAnimationFrame', 'cancelAnimationFrame', 'document', 'matchMedia'];
  const saved = new Map(keys.map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  let now = 0;
  let id = 0;
  const jobs = new Map();
  const doc = new EventTarget();
  doc.hidden = false;
  const add = (callback, delay) => { jobs.set(++id, { at: now + delay, callback }); return id; };
  const values = {
    performance: { now: () => now },
    setTimeout: (callback, delay) => add(callback, delay),
    clearTimeout: key => jobs.delete(key),
    requestAnimationFrame: callback => add(() => callback(now), 16),
    cancelAnimationFrame: key => jobs.delete(key),
    document: doc,
    matchMedia: () => ({ matches: false }),
  };
  for (const key of keys) Object.defineProperty(globalThis, key, { value: values[key], configurable: true, writable: true });
  const clock = {
    jobs,
    advance(amount) {
      const target = now + amount;
      let count = 0;
      while (jobs.size) {
        const [key, job] = [...jobs].sort((a, b) => a[1].at - b[1].at)[0];
        if (job.at > target) break;
        assert.ok(++count < 2000, 'scheduler did not settle');
        now = job.at;
        jobs.delete(key);
        job.callback();
      }
      now = target;
    },
    hide() { doc.hidden = true; doc.dispatchEvent(new Event('visibilitychange')); },
  };
  try { await run(clock); }
  finally {
    for (const key of keys) {
      if (saved.get(key)) Object.defineProperty(globalThis, key, saved.get(key));
      else delete globalThis[key];
    }
  }
}

test('fast responses wait, then expose a partial reply before completing', () => withClock(async clock => {
  const updates = [];
  const view = createReplyPresentation({ onUpdate: x => updates.push(x), minimumDelay: 1100 });
  const reply = '자연스러운 답변입니다. '.repeat(5);
  const done = view.present(reply);
  clock.advance(1099);
  assert.equal(updates.length, 0);
  clock.advance(401);
  const partial = updates.at(-1);
  assert.equal(partial.phase, 'typing');
  assert.ok(partial.visibleText.length > 0 && partial.visibleText.length < reply.length);
  clock.advance(4500);
  assert.equal(await done, true);
  assert.equal(updates.at(-1).visibleText, reply);
  assert.equal(clock.jobs.size, 0);
}));

test('slow responses do not wait for a second artificial thinking period', () => withClock(async clock => {
  const updates = [];
  const view = createReplyPresentation({ onUpdate: x => updates.push(x), minimumDelay: 1000 });
  clock.advance(2500);
  const done = view.present('답변');
  assert.equal(updates[0].phase, 'typing');
  clock.advance(400);
  assert.equal(await done, true);
}));

test('long replies finish at the 4500ms presentation limit', () => withClock(async clock => {
  const updates = [];
  const view = createReplyPresentation({ onUpdate: x => updates.push(x), minimumDelay: 0 });
  const reply = '가'.repeat(12000);
  const done = view.present(reply);
  clock.advance(4499);
  assert.notEqual(updates.at(-1).visibleText, reply);
  clock.advance(1);
  assert.equal(await done, true);
  assert.equal(updates.at(-1).visibleText, reply);
  assert.equal(clock.jobs.size, 0);
}));

test('Korean, combining characters and emoji sequences stay intact', () => withClock(async clock => {
  const reply = '가👨‍👩‍👧‍👦나e\u0301🙂🇰🇷';
  const allowed = new Set(['', ...revealBoundaries(reply).map(point => reply.slice(0, point.end))]);
  assert.equal(allowed.size, 7);
  const updates = [];
  const view = createReplyPresentation({ onUpdate: x => updates.push(x), minimumDelay: 0 });
  const done = view.present(reply);
  clock.advance(400);
  assert.equal(await done, true);
  assert.ok(updates.every(update => allowed.has(update.visibleText)));
}));

test('fenced code is revealed as a complete block', () => withClock(async clock => {
  const reply = '코드예요.\n```python\nprint("안녕")\n```\n끝.';
  const updates = [];
  const view = createReplyPresentation({ onUpdate: x => updates.push(x), minimumDelay: 0 });
  const done = view.present(reply);
  clock.advance(4500);
  assert.equal(await done, true);
  assert.ok(updates.every(x => (x.visibleText.match(/```/g)?.length ?? 0) % 2 === 0));
  assert.equal(updates.at(-1).visibleText, reply);
}));

test('show all immediately completes and removes all scheduled work', () => withClock(async clock => {
  const updates = [];
  const view = createReplyPresentation({ onUpdate: x => updates.push(x), minimumDelay: 0 });
  const done = view.present('조금 긴 답변입니다. '.repeat(20));
  clock.advance(150);
  view.skip();
  assert.equal(await done, true);
  assert.equal(updates.at(-1).complete, true);
  assert.equal(clock.jobs.size, 0);
}));

for (const phase of ['waiting', 'typing']) {
  test(`cancelling during ${phase} releases the caller and prevents later updates`, () => withClock(async clock => {
    const updates = [];
    const view = createReplyPresentation({ onUpdate: x => updates.push(x), minimumDelay: phase === 'waiting' ? 1000 : 0 });
    const done = view.present('답변을 표시하는 중입니다. '.repeat(10));
    clock.advance(100);
    view.cancel();
    const count = updates.length;
    clock.advance(10000);
    assert.equal(await done, false);
    assert.equal(view.cancelled, true);
    assert.equal(updates.length, count);
    assert.equal(clock.jobs.size, 0);
  }));
}

test('cancelling before the network completes prevents a later animation', () => withClock(async clock => {
  const updates = [];
  const view = createReplyPresentation({ onUpdate: x => updates.push(x) });
  view.cancel();
  assert.equal(await view.present('늦게 도착한 답변'), false);
  assert.equal(updates.length, 0);
  assert.equal(clock.jobs.size, 0);
}));

test('reduced motion waits once then shows the entire reply without frames', () => withClock(async clock => {
  const updates = [];
  const view = createReplyPresentation({ onUpdate: x => updates.push(x), minimumDelay: 1000, reducedMotion: true });
  const done = view.present('답변 전체');
  clock.advance(999);
  assert.equal(updates.length, 0);
  clock.advance(1);
  assert.equal(await done, true);
  assert.deepEqual(updates, [{ phase: 'typing', visibleText: '답변 전체', complete: true }]);
  assert.equal(clock.jobs.size, 0);
}));

test('hiding the tab finishes presentation without waiting on background frames', () => withClock(async clock => {
  const updates = [];
  const view = createReplyPresentation({ onUpdate: x => updates.push(x), minimumDelay: 1000 });
  const done = view.present('전체 답변');
  clock.hide();
  assert.equal(await done, true);
  assert.equal(updates.at(-1).visibleText, '전체 답변');
  assert.equal(clock.jobs.size, 0);
}));

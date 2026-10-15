import { spawn } from 'node:child_process';
import { createServer as createNetServer } from 'node:net';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { join } from 'node:path';

const root = fileURLToPath(new URL('.', import.meta.url));
const frontend = join(root, 'frontend');
const { createServer } = await import(pathToFileURL(join(frontend, 'node_modules/vite/dist/node/index.js')).href);
const probe = createNetServer();
await new Promise((resolve, reject) => {
  probe.once('error', reject);
  probe.listen(0, '127.0.0.1', resolve);
});
const backendPort = probe.address().port;
await new Promise(resolve => probe.close(resolve));
const backend = spawn(join(root, 'backend/.venv/Scripts/python.exe'), ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(backendPort)], {
  cwd: join(root, 'backend'), stdio: 'inherit', windowsHide: true,
});
let server;
let stopping = false;
async function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  backend.kill();
  await server?.close();
  process.exit(code);
}
backend.on('error', error => { console.error(error.message); void stop(1); });
backend.on('exit', code => { if (!stopping) void stop(code || 1); });
process.on('SIGINT', () => void stop());
process.on('SIGTERM', () => void stop());
try {
  for (let attempt = 0; ; attempt++) {
    if (attempt === 100) throw new Error('Backend did not become ready. Check the error above.');
    try {
      const response = await fetch(`http://127.0.0.1:${backendPort}/health`, { signal: AbortSignal.timeout(1000) });
      if (response.ok) break;
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  server = await createServer({
    root: frontend, configFile: join(frontend, 'vite.config.js'),
    define: { 'import.meta.env.VITE_API_URL': JSON.stringify('/api') },
    server: {
      host: '127.0.0.1', port: 5173, strictPort: false,
      open: !process.argv.includes('--no-open'),
      proxy: { '/api': { target: `http://127.0.0.1:${backendPort}`, rewrite: path => path.replace(/^\/api/, '') } },
    },
  });
  await server.listen();
  server.printUrls();
  console.log('Press Ctrl+C to stop both servers.');
} catch (error) {
  console.error(error.message);
  await stop(1);
}

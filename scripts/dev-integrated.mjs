// Isolated loopback launcher. Never manages an existing listener or runtime directory.
import { spawn } from 'node:child_process'
import { createServer } from 'node:net'
import { homedir } from 'node:os'
import { resolve } from 'node:path'
import { existsSync } from 'node:fs'
process.umask(0o077)
const root = resolve(import.meta.dirname, '..')
const base = process.env.REVELIO_RUNTIME_DIR || resolve(homedir(), '.local/share/revelio-witness')
const python = resolve(root, 'witness-backend/.venv/bin/python')
if (!existsSync(python)) throw new Error('Install witness-backend/.venv first; see docs/integration/STARTUP_GUIDE.md')
for (const port of [5182, 8021, 8022]) {
  await new Promise((ok, fail) => {
    const socket = createServer()
    socket.once('error', () => fail(new Error(`Port ${port} is occupied. No process was stopped.`)))
    socket.listen(port, '127.0.0.1', () => socket.close(ok))
  })
}
const env = { ...process.env, VITE_WITNESSTRACE_LOCAL: '1', WITNESSTRACE_PORT: '8022',
  WITNESSTRACE_DATA_DIR: process.env.WITNESSTRACE_DATA_DIR || resolve(base, 'data'),
  WITNESSTRACE_OUTPUTS_DIR: process.env.WITNESSTRACE_OUTPUTS_DIR || resolve(base, 'outputs'),
  WITNESSTRACE_WORK_DIR: process.env.WITNESSTRACE_WORK_DIR || resolve(base, 'work'),
  REVELIO_DATA_DIR: process.env.REVELIO_DATA_DIR || resolve(base, 'accounts'),
  WITNESSTRACE_GATEWAY_TARGET: 'http://127.0.0.1:8022', REVELIO_API_URL: 'http://127.0.0.1:8021',
  REVELIO_GATEWAY_URL: 'http://127.0.0.1:8021', REVELIO_HOSTED_PROVIDER: '' }
const children = []
let stopping = false
const stop = () => { if (stopping) return; stopping = true; children.forEach(child => child.kill('SIGTERM')) }
process.on('SIGINT', stop); process.on('SIGTERM', stop)
const start = (command, args, cwd = root) => {
  const child = spawn(command, args, { cwd, env, stdio: 'inherit' }); children.push(child)
  child.on('error', error => { console.error(error.message); process.exitCode = 1; stop() })
  child.on('exit', code => { if (!stopping) { process.exitCode = code || 1; stop() } })
}
start(python, ['-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', '8022'], resolve(root, 'witness-backend'))
start(python, ['-m', 'uvicorn', 'app.main:app', '--app-dir', 'backend', '--host', '127.0.0.1', '--port', '8021'])
start(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5182', '--strictPort'])
console.log('Revelio + WitnessTrace: http://127.0.0.1:5182 — local shared collection; accounts at /register')

// Runs the API and the Vite dev server together. Ctrl+C stops both.
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('..', import.meta.url))
const procs = [
  spawn(process.execPath, ['scripts/run-api.mjs'], { cwd: root, stdio: 'inherit' }),
  spawn(process.platform === 'win32' ? 'npx.cmd' : 'npx', ['vite'], { cwd: root, stdio: 'inherit' }),
]
const stop = () => procs.forEach((p) => p.kill('SIGTERM'))
procs.forEach((p) => p.on('exit', (code) => { if (code) { stop(); process.exit(code) } }))
process.on('SIGINT', () => { stop(); process.exit(0) })

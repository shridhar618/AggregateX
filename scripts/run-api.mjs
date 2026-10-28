// Starts the local Revelio API (or its tests) using backend/.venv.
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { existsSync } from 'node:fs'
import { join } from 'node:path'

const root = fileURLToPath(new URL('..', import.meta.url))
const backend = join(root, 'backend')
const isWin = process.platform === 'win32'
const py = join(backend, '.venv', isWin ? 'Scripts' : 'bin', isWin ? 'python.exe' : 'python')

if (!existsSync(py)) {
  console.error('\n[revelio] backend/.venv not found. Create it first:\n' +
    '  python3 -m venv backend/.venv\n' +
    '  backend/.venv/bin/pip install -r backend/requirements.txt\n')
  process.exit(1)
}

const args = process.argv.includes('--test')
  ? ['-m', 'pytest', '-q']
  : ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', process.env.REVELIO_API_PORT || '8000']
const child = spawn(py, args, { cwd: backend, stdio: 'inherit' })
child.on('exit', (code) => process.exit(code ?? 0))
for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, () => child.kill(sig))

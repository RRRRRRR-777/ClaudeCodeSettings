import { expect, test } from 'claude-code/testing'

import { capNewFile, lineColor, parseDiff, stripControl } from './register'

const DIFF = [
  'diff --git a/src/a.ts b/src/a.ts',
  'index 1..2 100644',
  '--- a/src/a.ts',
  '+++ b/src/a.ts',
  '@@ -1 +1 @@',
  '-old',
  '+new',
]

test('parseDiff splits per file with counts, new files included', () => {
  const added = ['diff --git a/notes.md b/notes.md', 'new file mode 100644', '+hello', '+world']
  const [first, second] = parseDiff([...DIFF, ...added])

  expect(first).toMatchObject({ path: 'src/a.ts', added: 1, removed: 1, isTruncated: false })
  expect(first.lines).toEqual(DIFF)
  expect(second).toMatchObject({ path: 'notes.md', added: 2, removed: 0 })
})

test('parseDiff of nothing is empty', () => {
  expect(parseDiff([])).toEqual([])
})

test('parseDiff cuts one file at 2000 lines', () => {
  const many = ['diff --git a/big b/big', ...Array.from({ length: 2500 }, (_, i) => `+${i}`)]
  const [file] = parseDiff(many)

  expect(file.lines).toHaveLength(2000)
  expect(file.isTruncated).toBe(true)
})

test('capNewFile keeps a short file whole and cuts a long one with a note', () => {
  expect(capNewFile('+a\n+b\n')).toEqual(['+a', '+b'])
  expect(capNewFile('')).toEqual([])

  const long = Array.from({ length: 350 }, (_, i) => `+${i}`).join('\n')
  const capped = capNewFile(long)

  expect(capped).toHaveLength(301)
  expect(capped.at(-1)).toBe('… 50 more lines in this file')
})

test('lineColor colors added, removed and hunk lines only', () => {
  expect(lineColor('+new')).toBe('green')
  expect(lineColor('-old')).toBe('red')
  expect(lineColor('@@ -1 +1 @@')).toBe('cyan')
  expect(lineColor('+++ b/src/a.ts')).toBeUndefined()
  expect(lineColor(' context')).toBeUndefined()
})

test('stripControl escapes terminal control characters, keeps tabs, drops a trailing CR', () => {
  expect(stripControl('a\x1b[31mred\x07')).toBe('a\\x1b[31mred\\x07')
  expect(stripControl('\tindented')).toBe('\tindented')
  expect(stripControl('crlf line\r')).toBe('crlf line')
})

test('parseDiff escapes control characters in paths and lines', () => {
  const [file] = parseDiff(['diff --git a/x\x1b b/x\x1b', '+\x1b[2Jboom'])

  expect(file.path).toBe('x\\x1b')
  expect(file.lines.join('')).not.toContain('\x1b')
})

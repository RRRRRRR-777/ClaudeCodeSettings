import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { FileDiff } from '../types'

const PANE = 'git-diff'
const MAX_LINES = 2000
const MAX_LINES_PER_NEW_FILE = 300
const MAX_NEW_FILES = 50
const REFRESH_TOOLS = new Set(['Edit', 'Write', 'MultiEdit', 'NotebookEdit', 'Bash'])

const files = atom({ plugin: 'git-diff-button', key: 'files' } as const, [] as FileDiff[])
const selected = atom({ plugin: 'git-diff-button', key: 'selected' } as const, null as string | null)

const splitLines = (text: string) => (text === '' ? [] : text.replace(/\n$/, '').split('\n'))

export const capNewFile = (diff: string): string[] => {
  const lines = splitLines(diff)
  if (lines.length <= MAX_LINES_PER_NEW_FILE) return lines

  return [
    ...lines.slice(0, MAX_LINES_PER_NEW_FILE),
    `… ${lines.length - MAX_LINES_PER_NEW_FILE} more lines in this file`,
  ]
}

const CONTROL = /[\x00-\x08\x0b-\x1f\x7f-\x9f]/g

export const stripControl = (line: string) =>
  line
    .replace(/\r$/, '')
    .replace(CONTROL, c => `\\x${c.charCodeAt(0).toString(16).padStart(2, '0')}`)

export const parseDiff = (raw: string[]): FileDiff[] => {
  const lines = raw.map(stripControl)
  const starts = lines.flatMap((line, i) => (line.startsWith('diff --git ') ? [i] : []))

  return starts.map((from, n) => {
    const body = lines.slice(from, starts[n + 1] ?? lines.length)

    return {
      path: body[0].replace(/^diff --git a\/.* b\//, ''),
      lines: body.slice(0, MAX_LINES),
      added: body.filter(line => line.startsWith('+') && !line.startsWith('+++')).length,
      removed: body.filter(line => line.startsWith('-') && !line.startsWith('---')).length,
      isTruncated: body.length > MAX_LINES,
    }
  })
}

export const lineColor = (line: string) => {
  if (line.startsWith('+++') || line.startsWith('---')) return undefined
  if (line.startsWith('+')) return 'green'
  if (line.startsWith('-')) return 'red'
  if (line.startsWith('@@')) return 'cyan'

  return undefined
}

async function refresh($: EngineInterface) {
  const [tracked, others] = await Promise.all([
    $.process.run(['git', 'diff', 'HEAD', '--no-color']),
    $.process.run(['git', 'ls-files', '-z', '--others', '--exclude-standard']),
  ])
  const paths = others.stdout.split('\0').filter(path => path !== '').slice(0, MAX_NEW_FILES)
  const added = await Promise.all(
    paths.map(path =>
      $.process.run(['git', 'diff', '--no-index', '--no-color', '--', '/dev/null', path]),
    ),
  )
  const lines = [...splitLines(tracked.stdout), ...added.flatMap(one => capNewFile(one.stdout))]
  await update($, files, () => parseDiff(lines))
}

async function show($: EngineInterface, path: string | null, focusKey: string) {
  await update($, selected, () => path)
  await $.ui.focus({ requestId: PANE, key: focusKey }).catch(() => undefined)
}

export const register: Register = on => {
  let isWatching = false

  on('tool.call', async ($, e, next) => {
    const ran = await next(e)
    if (isWatching && REFRESH_TOOLS.has(e.tool)) {
      await refresh($).catch(() => undefined)
    }

    return ran
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const { Box, Button } = $.ui.resolve(e)
    const rest = await next(e)

    return (
      <Box flexDirection="column">
        {rest}
        <Box justifyContent="flex-end">
          <Button
            key="open-diff"
            label="diff"
            dimColor
            onPress={async () => {
              isWatching = true
              await refresh($)
              await update($, selected, () => null)
              await $.ui.open({ id: PANE, title: 'diff', focus: true, closeOnEscape: true })
            }}
          />
        </Box>
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Button, Text } = $.ui.resolve(e)
    const all = await read($, files)
    const path = await read($, selected)
    const file = all.find(one => one.path === path)

    if (all.length === 0) {
      return <Text dimColor>No changes.</Text>
    }

    if (file === undefined) {
      return (
        <Box flexDirection="column">
          <Text bold>{all.length} files changed</Text>
          {all.map((one, i) => (
            <Button
              key={one.path}
              autoFocus={i === 0 ? true : undefined}
              onPress={() => show($, one.path, 'back')}
            >
              <Text>{one.path} </Text>
              <Text color="green">+{one.added} </Text>
              <Text color="red">-{one.removed}</Text>
            </Button>
          ))}
        </Box>
      )
    }

    return (
      <Box flexDirection="column">
        <Box gap={1}>
          <Button
            key="back"
            label="< files"
            hotkey="b"
            autoFocus
            onPress={() => show($, null, file.path)}
          />
          <Text bold>{file.path}</Text>
        </Box>
        {file.lines.map(line => (
          <Text color={lineColor(line)} dimColor={line.startsWith('diff --git')}>
            {line}
          </Text>
        ))}
        {file.isTruncated && <Text dimColor>… cut at {MAX_LINES} lines</Text>}
      </Box>
    )
  })
}

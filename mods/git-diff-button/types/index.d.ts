export type FileDiff = {
  path: string
  lines: string[]
  added: number
  removed: number
  isTruncated: boolean
}

declare module 'claude-code' {
  interface PluginState {
    'git-diff-button': { files: FileDiff[]; selected: string | null }
  }
}

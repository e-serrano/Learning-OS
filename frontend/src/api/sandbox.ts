import { request } from './client'

export type SqlCell = string | number | null

export interface SqlSandboxResult {
  columns: string[]
  rows: SqlCell[][]
  row_count: number
  truncated: boolean
  statement_count: number
  error: string | null
}

export { ApiError } from './client'

export function runSql(sql: string): Promise<SqlSandboxResult> {
  return request('/sandbox/sql', { method: 'POST', body: JSON.stringify({ sql }) })
}

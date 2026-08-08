import { mkdir, writeFile } from "node:fs/promises"

const token = process.env.GITHUB_TOKEN
const username = process.env.GITHUB_USERNAME
const days = 365
const output = "profile/metrics.languages.recent.svg"
const excluded = new Set([`${username}/${username}`, `${username}/${username}.github.io`])

if (!token || !username) {
  throw new Error("GITHUB_TOKEN and GITHUB_USERNAME are required")
}

async function github(path) {
  const response = await fetch(`https://api.github.com${path}`, {
    headers: {
      accept: "application/vnd.github+json",
      authorization: `Bearer ${token}`,
      "x-github-api-version": "2022-11-28",
    },
  })
  if (!response.ok) {
    throw new Error(`GitHub API ${response.status} for ${path}: ${await response.text()}`)
  }
  return response.json()
}

const cutoff = Date.now() - days * 24 * 60 * 60 * 1000
const repositories = []
for (let page = 1; ; page++) {
  const batch = await github(`/users/${encodeURIComponent(username)}/repos?per_page=100&page=${page}&type=owner&sort=pushed`)
  repositories.push(...batch)
  if (batch.length < 100) break
}

const recentRepositories = repositories.filter((repo) =>
  !repo.fork && !excluded.has(repo.full_name) && new Date(repo.pushed_at).getTime() >= cutoff,
)

const totals = new Map()
for (let index = 0; index < recentRepositories.length; index += 8) {
  const batch = recentRepositories.slice(index, index + 8)
  const languages = await Promise.all(batch.map((repo) => github(`/repos/${repo.full_name}/languages`)))
  for (const languageSet of languages) {
    for (const [language, bytes] of Object.entries(languageSet)) {
      totals.set(language, (totals.get(language) ?? 0) + bytes)
    }
  }
}

const languages = [...totals.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6)
const totalBytes = languages.reduce((sum, [, bytes]) => sum + bytes, 0)
const colors = ["#3572A5", "#f1e05a", "#DA5B0B", "#3178c6", "#00ADD8", "#A97BFF"]
const escape = (value) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;")
const rows = languages.length
  ? languages.map(([language, bytes], index) => {
      const percentage = (bytes / totalBytes) * 100
      const y = 54 + index * 25
      const width = Math.max(2, percentage * 4.1)
      return `<circle cx="20" cy="${y - 5}" r="5" fill="${colors[index % colors.length]}"/><text x="34" y="${y}" fill="#c9d1d9" font-family="Arial, sans-serif" font-size="13">${escape(language)}</text><rect x="170" y="${y - 14}" width="${width.toFixed(1)}" height="8" rx="4" fill="${colors[index % colors.length]}"/><text x="465" y="${y}" text-anchor="end" fill="#8b949e" font-family="Arial, sans-serif" font-size="12">${percentage.toFixed(1)}%</text>`
    }).join("")
  : '<text x="20" y="70" fill="#8b949e" font-family="Arial, sans-serif" font-size="13">No recent language data</text>'

const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="500" height="205" viewBox="0 0 500 205"><rect width="500" height="205" rx="6" fill="#0d1117"/><text x="20" y="28" fill="#f0f6fc" font-family="Arial, sans-serif" font-size="16" font-weight="600">Recently used languages</text><text x="20" y="44" fill="#8b949e" font-family="Arial, sans-serif" font-size="11">Last ${days} days · ${recentRepositories.length} active repositories</text>${rows}</svg>`
await mkdir("profile", { recursive: true })
await writeFile(output, svg)
console.log(`Generated ${output} from ${recentRepositories.length} repositories`)

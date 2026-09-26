import type { ReactNode } from "react"

// 홈 AI 채팅 답변용 최소 마크다운 렌더러 — 굵게·링크·URL·인라인 코드·목록·문단만 지원한다.
// 시스템 프롬프트가 이 범위 안에서만 쓰도록 모델에 지시한다(표·제목·이미지 없음). 의존성 추가 없음.

const INLINE = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\((https?:\/\/[^\s)]+)\)|https?:\/\/[^\s)]+)/g

function renderInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = []
  let last = 0
  for (const match of text.matchAll(INLINE)) {
    const token = match[0]
    const start = match.index ?? 0
    if (start > last) nodes.push(text.slice(last, start))
    if (token.startsWith("**")) {
      nodes.push(<strong key={start}>{token.slice(2, -2)}</strong>)
    } else if (token.startsWith("`")) {
      nodes.push(
        <code
          key={start}
          className="rounded bg-black/10 px-1 py-0.5 text-[0.85em] dark:bg-white/10"
        >
          {token.slice(1, -1)}
        </code>
      )
    } else {
      const linkMatch = token.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/)
      const label = linkMatch ? linkMatch[1] : token
      const href = linkMatch ? linkMatch[2] : token
      nodes.push(
        <a
          key={start}
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="underline decoration-neutral-400 underline-offset-2 hover:decoration-current"
        >
          {label}
        </a>
      )
    }
    last = start + token.length
  }
  if (last < text.length) nodes.push(text.slice(last))
  return nodes
}

type Block = { kind: "p"; lines: string[] } | { kind: "ul" | "ol"; items: string[] }

function parseBlocks(text: string): Block[] {
  const blocks: Block[] = []
  for (const raw of text.split("\n")) {
    const line = raw.trimEnd()
    const bullet = line.match(/^\s*[-*•]\s+(.*)$/)
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)$/)
    const last = blocks[blocks.length - 1]
    if (bullet || numbered) {
      const kind = bullet ? "ul" : "ol"
      const item = (bullet ?? numbered)?.[1] ?? ""
      if (last && last.kind === kind) last.items.push(item)
      else blocks.push({ kind, items: [item] })
    } else if (line.trim() === "") {
      if (last && last.kind === "p" && last.lines.length > 0) blocks.push({ kind: "p", lines: [] })
    } else {
      const heading = line.replace(/^#{1,6}\s+/, "")
      const content = heading !== line ? `**${heading}**` : line
      if (last && last.kind === "p") last.lines.push(content)
      else blocks.push({ kind: "p", lines: [content] })
    }
  }
  return blocks.filter((b) => (b.kind === "p" ? b.lines.length > 0 : b.items.length > 0))
}

export function ChatMarkdown({ text }: { text: string }) {
  return (
    <div className="space-y-2">
      {parseBlocks(text).map((block, i) =>
        block.kind === "p" ? (
          <p key={i}>
            {block.lines.map((line, j) => (
              <span key={j}>
                {j > 0 && <br />}
                {renderInline(line)}
              </span>
            ))}
          </p>
        ) : block.kind === "ul" ? (
          <ul key={i} className="list-disc space-y-1 pl-5">
            {block.items.map((item, j) => (
              <li key={j}>{renderInline(item)}</li>
            ))}
          </ul>
        ) : (
          <ol key={i} className="list-decimal space-y-1 pl-5">
            {block.items.map((item, j) => (
              <li key={j}>{renderInline(item)}</li>
            ))}
          </ol>
        )
      )}
    </div>
  )
}

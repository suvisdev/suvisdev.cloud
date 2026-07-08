import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

interface ProjectCardProps {
  title: string
  description: string
  tags: string[]
  featured?: boolean
}

export function ProjectCard({ title, description, tags, featured }: ProjectCardProps) {
  return (
    <Card
      className={`group cursor-pointer border-red-950/50 bg-red-950/15 shadow-lg shadow-black/30 backdrop-blur-sm transition-all duration-300 hover:border-red-600/50 hover:bg-red-950/25 ${
        featured
          ? "ring-1 ring-amber-500/20 hover:ring-cyan-400/25"
          : "hover:shadow-cyan-950/10"
      }`}
    >
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold tracking-tight text-neutral-50 transition-colors group-hover:text-red-300">
            {title}
          </CardTitle>
          {featured && (
            <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-amber-300/95">
              Featured
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <CardDescription className="mb-4 text-[15px] leading-relaxed tracking-tight text-red-100/50">
          {description}
        </CardDescription>
        <div className="flex flex-wrap gap-2">
          {tags.map((tag) => (
            <span
              key={tag}
              className="rounded border border-red-900/45 bg-zinc-950/70 px-2 py-1 text-[11px] font-medium tracking-wide text-red-200/65"
            >
              {tag}
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

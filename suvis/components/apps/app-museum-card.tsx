import Image from "next/image"
import Link from "next/link"
import { cn } from "@/lib/utils"
import type { AppCatalogItem } from "@/lib/apps-catalog"

type AppMuseumCardProps = {
  app: AppCatalogItem
}

function CardImage({ app }: { app: AppCatalogItem }) {
  if (app.image) {
    return (
      <div className="relative min-h-[140px] flex-1 overflow-hidden bg-neutral-900">
        <Image
          src={app.image}
          alt={`${app.titleKo} — ${app.titleEn}`}
          fill
          className="object-cover object-center"
          sizes="(max-width: 768px) 50vw, (max-width: 1024px) 33vw, 25vw"
        />
        <div
          className="absolute inset-0 bg-gradient-to-t from-black/45 via-transparent to-transparent"
          aria-hidden
        />
      </div>
    )
  }

  return (
    <div
      className={cn(
        "relative min-h-[140px] flex-1 overflow-hidden bg-gradient-to-br",
        app.gradient,
      )}
    >
      {app.icon && (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-6xl opacity-75 drop-shadow-sm">{app.icon}</span>
        </div>
      )}
    </div>
  )
}

function CardText({ app }: { app: AppCatalogItem }) {
  return (
    <div className="shrink-0 px-4 py-5">
      <h2 className="text-lg font-bold leading-tight text-neutral-900 md:text-xl">{app.titleKo}</h2>
      <p className="mt-1 text-xs font-medium tracking-wide text-neutral-500 uppercase md:text-sm">
        {app.titleEn}
      </p>
      {app.team && (
        <p className="mt-2 text-[10px] font-medium tracking-[0.2em] text-neutral-400 uppercase">
          {app.team}
        </p>
      )}
      {app.available && (
        <span className="mt-2 inline-block rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-800">
          Live
        </span>
      )}
    </div>
  )
}

export function AppMuseumCard({ app }: AppMuseumCardProps) {
  const content = (
    <article
      className={cn(
        "flex h-full min-h-[280px] flex-col overflow-hidden rounded-sm bg-white shadow-md shadow-black/8 transition-shadow md:min-h-[320px]",
        app.available && "hover:shadow-lg hover:shadow-black/12",
        !app.available && !app.href && "cursor-default",
      )}
    >
      {app.imageFirst ? (
        <>
          <CardImage app={app} />
          <CardText app={app} />
        </>
      ) : (
        <>
          <CardText app={app} />
          <CardImage app={app} />
        </>
      )}
    </article>
  )

  if (app.href) {
    return (
      <Link
        href={app.href}
        target={app.available ? undefined : "_blank"}
        rel={app.available ? undefined : "noopener noreferrer"}
        className="block h-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400 focus-visible:ring-offset-2"
      >
        {content}
      </Link>
    )
  }

  return content
}

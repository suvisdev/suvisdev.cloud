"use client"

import dynamic from "next/dynamic"

const WalkHistory = dynamic(() => import("./_components/walk-history"), {
  ssr: false,
  loading: () => (
    <div className="flex h-screen items-center justify-center bg-[#0a0d0a] text-gray-400">
      불러오는 중…
    </div>
  ),
})

export default function GildleWalksPage() {
  return <WalkHistory />
}

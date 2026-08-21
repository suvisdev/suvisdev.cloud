"use client"

import dynamic from "next/dynamic"

const GildleMap = dynamic(() => import("./_components/gildle-map"), {
  ssr: false,
  loading: () => (
    <div className="flex h-screen items-center justify-center bg-[#0a0d0a] text-gray-400">
      지도 로딩 중…
    </div>
  ),
})

export default function GildleMapPage() {
  return <GildleMap />
}

import type { Metadata } from "next"
import type { ReactNode } from "react"
import { AdminSidebar } from "./_components/admin-sidebar"
import { AdminSidebarProvider } from "./_components/admin-sidebar-context"

export const metadata: Metadata = {
  title: "Admin Dashboard — Suvisdev",
}

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <AdminSidebarProvider>
      <div className="min-h-screen w-full bg-slate-50 [overflow-x:clip]">
        <AdminSidebar />
        <div className="w-full pb-16 md:pb-0 md:pl-16 lg:pl-60">
          {children}
        </div>
      </div>
    </AdminSidebarProvider>
  )
}

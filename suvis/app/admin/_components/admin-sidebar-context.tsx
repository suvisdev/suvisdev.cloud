"use client"

import { createContext, useContext, useState } from "react"
import type { ReactNode } from "react"

type Ctx = { open: boolean; setOpen: (v: boolean) => void }
const AdminSidebarContext = createContext<Ctx>({ open: false, setOpen: () => {} })

export function AdminSidebarProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <AdminSidebarContext.Provider value={{ open, setOpen }}>
      {children}
    </AdminSidebarContext.Provider>
  )
}

export function useAdminSidebar() {
  return useContext(AdminSidebarContext)
}

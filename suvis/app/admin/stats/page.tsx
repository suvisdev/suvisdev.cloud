import { redirect } from "next/navigation"

export default function StatsIndexPage() {
  redirect("/admin/stats/overview")
}

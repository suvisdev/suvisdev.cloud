import { redirect } from "next/navigation"

export default function HarvesterIndexPage() {
  redirect("/admin/harvester/crawler")
}

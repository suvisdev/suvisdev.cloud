import { AdminAgentDetailView } from "./admin-agent-detail-view"

type PageProps = {
  params: Promise<{ id: string }>
}

export default async function AdminAgentDetailPage({ params }: PageProps) {
  const { id } = await params
  return <AdminAgentDetailView id={id} />
}

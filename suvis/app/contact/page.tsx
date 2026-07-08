import type { Metadata } from "next"
import { ContactPageContent } from "@/components/contact/contact-page-content"

export const metadata: Metadata = {
  title: "Contact — Suvisdev",
  description: "Suvisdev 소개 및 연락처",
}

export default function ContactPage() {
  return <ContactPageContent />
}

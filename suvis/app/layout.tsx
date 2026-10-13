import type { Metadata } from 'next'
import { Barlow_Condensed, Geist } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import { SessionSync } from '@/components/auth/session-sync'
import { ContentGuard } from '@/components/content-guard'
import { ScrollbarAutohide } from '@/components/scrollbar-autohide'
import { SiteChrome } from '@/components/site-chrome'
import { ThemeProvider } from '@/components/theme-provider'
import './globals.css'

const geistSans = Geist({ subsets: ['latin'], variable: '--font-geist-sans' })
const displayCondensed = Barlow_Condensed({
  subsets: ['latin'],
  weight: ['600', '700'],
  variable: '--font-display-condensed',
})

export const metadata: Metadata = {
  title: 'Suvisdev - Developer Portfolio',
  description: 'Building innovative web experiences and AI-powered applications',
  generator: 'v0.app',
  // Suvisdev 마크(코드 꺾쇠 + AI 반짝임, 2026-10-06) — 헤더는 같은 마크의 투명 배경판 suvisdev-mark.svg
  icons: {
    icon: '/suvisdev-icon.svg',
    apple: '/apple-icon.png',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="ko" className="bg-background" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${displayCondensed.variable} font-sans antialiased`}
      >
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false} disableTransitionOnChange>
          <ScrollbarAutohide />
          <ContentGuard />
          <SessionSync />
          <SiteChrome>{children}</SiteChrome>
          {process.env.NODE_ENV === 'production' && <Analytics />}
        </ThemeProvider>
      </body>
    </html>
  )
}

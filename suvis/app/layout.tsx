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
  // 직접 만든 SV 육각형 로고(public/suvis-logo.png에서 워터마크 빼고 잘라 냄, 2026-10-06)
  icons: {
    icon: '/suvisdev-icon.png',
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

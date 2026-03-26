'use client'

import { Footer } from './footer'
import { Sidebar } from './sidebar'
import { cn } from '@/lib/utils'

interface MainLayoutProps {
  children: React.ReactNode
  className?: string
}

export function MainLayout({ children, className }: MainLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <div className="flex min-h-0 flex-1">
        <Sidebar />
        <main className={cn('min-w-0 flex-1 overflow-auto bg-background', className)}>
          <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
            <div className="space-y-6">{children}</div>
          </div>
        </main>
      </div>
      <Footer />
    </div>
  )
}

export default MainLayout

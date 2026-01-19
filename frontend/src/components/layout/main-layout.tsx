'use client'

import { Navbar } from './navbar'
import { Sidebar } from './sidebar'
import { Footer } from './footer'
import { cn } from '@/lib/utils'

interface MainLayoutProps {
  children: React.ReactNode
  className?: string
}

export function MainLayout({ children, className }: MainLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className={cn('flex-1 overflow-y-auto', className)}>
          <div className="container py-6">{children}</div>
        </main>
      </div>
      <Footer />
    </div>
  )
}

// Default export for backward compatibility
export default MainLayout;

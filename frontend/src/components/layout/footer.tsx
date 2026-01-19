import Link from 'next/link'
import { cn } from '@/lib/utils'

interface FooterProps {
  className?: string
}

export function Footer({ className }: FooterProps) {
  return (
    <footer
      className={cn(
        'border-t bg-background',
        className
      )}
    >
      <div className="container flex h-16 items-center justify-between px-4">
        <p className="text-sm text-muted-foreground">
          © {new Date().getFullYear()} AI Code Review Platform. All rights reserved.
        </p>
        <nav className="flex items-center gap-4">
          <Link
            href="/docs"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Documentation
          </Link>
          <Link
            href="/support"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Support
          </Link>
          <Link
            href="/privacy"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Privacy
          </Link>
        </nav>
      </div>
    </footer>
  )
}

'use client'

import dynamic from 'next/dynamic'

const DeferredToaster = dynamic(
  () => import('@/components/ui/toaster').then((module) => module.Toaster),
  { ssr: false }
)

export function ClientToaster() {
  return <DeferredToaster />
}

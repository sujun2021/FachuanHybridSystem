import { Outlet } from 'react-router'
import { motion } from 'framer-motion'
import { Scale } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { ThemeToggle } from '@/features/auth/components/ThemeToggle'

interface AuthLayoutProps {
  children?: React.ReactNode
  title?: string
  description?: string
}

export function AuthLayoutCard({ children, title, description }: AuthLayoutProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="w-full max-w-sm"
    >
      {(title || description) && (
        <div className="flex flex-col space-y-1.5 mb-6">
          {title && (
            <h2 className="text-lg font-semibold tracking-tight">
              {title}
            </h2>
          )}
          {description && (
            <p className="text-sm text-muted-foreground">
              {description}
            </p>
          )}
        </div>
      )}
      <Card className="border-0 shadow-none bg-transparent sm:border sm:shadow-sm sm:bg-card">
        <CardContent className={title || description ? 'pt-0' : 'pt-6'}>
          {children}
        </CardContent>
      </Card>
    </motion.div>
  )
}

function AuthDecorativePanel() {
  return (
    <div className="relative hidden h-full flex-col bg-muted p-10 text-muted-foreground lg:flex dark:border-l">
      <div className="absolute inset-0 bg-zinc-900 dark:bg-zinc-950" />
      <div className="relative z-20 flex items-center text-lg font-medium text-white">
        <Scale className="mr-2 h-6 w-6" />
        法穿AI Copilot
      </div>
      <div className="relative z-20 mt-auto">
        <blockquote className="space-y-2">
          <p className="text-lg text-white/80">
            &ldquo;智能化法律事务管理，让每一位律师都能专注于案件本身。&rdquo;
          </p>
        </blockquote>
      </div>
    </div>
  )
}

export function AuthLayout() {
  return (
    <div className="relative container grid h-svh flex-col items-center justify-center lg:max-w-none lg:grid-cols-2 lg:px-0">
      {/* Theme toggle */}
      <motion.div
        className="fixed top-4 right-4 z-50"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3, duration: 0.3 }}
      >
        <ThemeToggle />
      </motion.div>

      {/* Left: form area */}
      <div className="lg:p-8">
        <div className="mx-auto flex w-full flex-col justify-center space-y-2 py-8 sm:w-[360px] sm:p-8">
          <div className="mb-4 flex items-center justify-center lg:justify-start">
            <Scale className="mr-2 h-6 w-6" />
            <h1 className="text-xl font-medium">法穿AI Copilot</h1>
          </div>
          <Outlet />
        </div>
      </div>

      {/* Right: decorative panel */}
      <AuthDecorativePanel />
    </div>
  )
}

export default AuthLayout

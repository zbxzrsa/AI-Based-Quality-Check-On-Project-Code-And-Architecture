'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { AlertCircle, Check, Loader2, X } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useToast } from '@/hooks/use-toast'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const registerSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  password: z.string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/[0-9]/, 'Password must contain at least one number'),
  confirmPassword: z.string(),
  acceptTerms: z.boolean().refine((val) => val === true, {
    message: 'You must accept the terms and conditions',
  }),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
})

export type RegisterPageFormData = z.infer<typeof registerSchema>

export default function RegisterPageContent() {
  const { toast } = useToast()
  const { register: registerUser, loading } = useAuth()
  const [passwordStrength, setPasswordStrength] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    watch,
    control,
    formState: { errors },
  } = useForm<RegisterPageFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      acceptTerms: false,
    },
  })

  const password = watch('password', '')

  const calculatePasswordStrength = (pwd: string) => {
    let strength = 0
    if (pwd.length >= 8) strength += 25
    if (pwd.length >= 12) strength += 25
    if (/[A-Z]/.test(pwd)) strength += 15
    if (/[a-z]/.test(pwd)) strength += 15
    if (/[0-9]/.test(pwd)) strength += 10
    if (/[^A-Za-z0-9]/.test(pwd)) strength += 10
    return Math.min(strength, 100)
  }

  useEffect(() => {
    setPasswordStrength(calculatePasswordStrength(password))
  }, [password])

  const getPasswordStrengthText = () => {
    if (passwordStrength <= 40) return 'Weak'
    if (passwordStrength < 70) return 'Medium'
    return 'Strong'
  }

  const getPasswordStrengthColor = () => {
    if (passwordStrength < 40) return 'bg-destructive'
    if (passwordStrength < 70) return 'bg-yellow-600'
    return 'bg-green-600'
  }

  const onSubmit = async (data: RegisterPageFormData) => {
    setError(null)

    try {
      await registerUser(data.email, data.password, data.name)
      toast({
        title: 'Registration Successful',
        description: 'Welcome! Redirecting to dashboard...',
      })
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred during registration'
      setError(errorMessage)
      toast({
        variant: 'destructive',
        title: 'Registration Failed',
        description: errorMessage,
      })
    }
  }

  const passwordRequirements = [
    { met: password.length >= 8, text: 'At least 8 characters' },
    { met: /[A-Z]/.test(password), text: 'One uppercase letter' },
    { met: /[a-z]/.test(password), text: 'One lowercase letter' },
    { met: /[0-9]/.test(password), text: 'One number' },
  ]

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-4">
      <Card className="w-full max-w-md" role="main" aria-labelledby="register-title">
        <CardHeader className="space-y-1">
          <div className="mb-4 flex items-center justify-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary" role="img" aria-label="AI Reviewer Logo">
              <span className="text-2xl font-bold text-primary-foreground" aria-hidden="true">AI</span>
            </div>
          </div>
          <CardTitle id="register-title" className="text-center text-2xl">Create an account</CardTitle>
          <CardDescription className="text-center">
            Enter your information to get started
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <div
              role="alert"
              aria-live="assertive"
              className="mb-4 flex items-center gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive"
            >
              <AlertCircle className="h-4 w-4" aria-hidden="true" />
              <span>{error}</span>
            </div>
          )}

          <form noValidate onSubmit={handleSubmit(onSubmit)} className="space-y-4" aria-label="Registration form">
            <div className="space-y-2">
              <Label htmlFor="name">Full Name</Label>
              <Input id="name" type="text" placeholder="John Doe" {...register('name')} disabled={loading} autoComplete="name" />
              {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" placeholder="name@example.com" {...register('email')} disabled={loading} autoComplete="email" />
              {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Create a strong password"
                {...register('password')}
                disabled={loading}
                autoComplete="new-password"
                aria-required="true"
                aria-invalid={errors.password ? 'true' : 'false'}
                aria-describedby={password ? 'password-strength password-requirements' : errors.password ? 'password-error' : undefined}
              />
              {password && (
                <div className="mt-2 space-y-2" id="password-strength" aria-live="polite">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Password strength:</span>
                    <span className={`font-medium ${
                      passwordStrength < 40 ? 'text-destructive' :
                      passwordStrength < 70 ? 'text-yellow-600' :
                      'text-green-600'
                    }`}>
                      {getPasswordStrengthText()}
                    </span>
                  </div>
                  <div
                    className="relative h-2 w-full overflow-hidden rounded-full bg-secondary"
                    role="progressbar"
                    aria-valuenow={passwordStrength}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={`Password strength: ${getPasswordStrengthText()}`}
                  >
                    <div className={`h-full transition-all duration-300 ${getPasswordStrengthColor()}`} style={{ width: `${passwordStrength}%` }} />
                  </div>
                  <div className="space-y-1 pt-1" id="password-requirements" role="list" aria-label="Password requirements">
                    {passwordRequirements.map((req) => (
                      <div key={req.text} className="flex items-center text-xs" role="listitem">
                        {req.met ? (
                          <Check className="mr-2 h-3 w-3 flex-shrink-0 text-green-600" aria-hidden="true" />
                        ) : (
                          <X className="mr-2 h-3 w-3 flex-shrink-0 text-muted-foreground" aria-hidden="true" />
                        )}
                        <span className={req.met ? 'text-green-600' : 'text-muted-foreground'}>{req.text}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {errors.password && (
                <p id="password-error" className="text-sm text-destructive" role="alert">
                  {errors.password.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="Confirm your password"
                {...register('confirmPassword')}
                disabled={loading}
                autoComplete="new-password"
              />
              {errors.confirmPassword && <p className="text-sm text-destructive">{errors.confirmPassword.message}</p>}
            </div>

            <div className="flex items-start space-x-2">
              <Controller
                name="acceptTerms"
                control={control}
                render={({ field }) => (
                  <Checkbox
                    id="acceptTerms"
                    checked={field.value}
                    onCheckedChange={field.onChange}
                    disabled={loading}
                    className="mt-1"
                  />
                )}
              />
              <Label htmlFor="acceptTerms" className="text-sm leading-5">
                I accept the terms and conditions
              </Label>
            </div>
            {errors.acceptTerms && <p className="text-sm text-destructive">{errors.acceptTerms.message}</p>}

            <Button type="submit" className="w-full" disabled={loading} aria-label="Create account">
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating account...
                </>
              ) : (
                'Create account'
              )}
            </Button>

            <p className="text-center text-sm text-muted-foreground">
              Already have an account?{' '}
              <Link href="/login" className="font-medium text-primary hover:underline">
                Sign in
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

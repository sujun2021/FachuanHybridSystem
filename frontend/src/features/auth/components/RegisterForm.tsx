import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2, UserPlus } from 'lucide-react'

import { registerSchema, type RegisterFormData } from '../schemas'
import { useRegisterMutation } from '../hooks/use-auth-mutations'
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

interface RegisterFormProps {
  onSuccess?: (requiresApproval: boolean) => void
  onError?: (error: string) => void
}

export function RegisterForm({ onSuccess, onError }: RegisterFormProps) {
  const form = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      username: '',
      password: '',
      confirmPassword: '',
      real_name: '',
      phone: '',
    },
  })

  const registerMutation = useRegisterMutation()

  const onSubmit = (data: RegisterFormData) => {
    registerMutation.mutate(
      {
        username: data.username,
        password: data.password,
        real_name: data.real_name || undefined,
        phone: data.phone || undefined,
      },
      {
        onSuccess: (response) => {
          onSuccess?.(response.requires_approval)
        },
        onError: (error) => {
          const errorMessage =
            error instanceof Error ? error.message : '注册失败，请重试'
          onError?.(errorMessage)
        },
      }
    )
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-3">
        <FormField
          control={form.control}
          name="username"
          render={({ field }) => (
            <FormItem>
              <FormLabel>用户名</FormLabel>
              <FormControl>
                <Input
                  placeholder="请输入用户名（3-20个字符）"
                  autoComplete="username"
                  disabled={registerMutation.isPending}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>密码</FormLabel>
              <FormControl>
                <Input
                  type="password"
                  placeholder="请输入密码（6-32个字符）"
                  autoComplete="new-password"
                  disabled={registerMutation.isPending}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="confirmPassword"
          render={({ field }) => (
            <FormItem>
              <FormLabel>确认密码</FormLabel>
              <FormControl>
                <Input
                  type="password"
                  placeholder="请再次输入密码"
                  autoComplete="new-password"
                  disabled={registerMutation.isPending}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="real_name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>
                真实姓名
                <span className="ml-1 text-xs text-muted-foreground">（可选）</span>
              </FormLabel>
              <FormControl>
                <Input
                  placeholder="请输入真实姓名"
                  autoComplete="name"
                  disabled={registerMutation.isPending}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="phone"
          render={({ field }) => (
            <FormItem>
              <FormLabel>
                手机号
                <span className="ml-1 text-xs text-muted-foreground">（可选）</span>
              </FormLabel>
              <FormControl>
                <Input
                  type="tel"
                  placeholder="请输入手机号"
                  autoComplete="tel"
                  disabled={registerMutation.isPending}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button className="mt-2" disabled={registerMutation.isPending}>
          {registerMutation.isPending ? (
            <Loader2 className="animate-spin" />
          ) : (
            <UserPlus />
          )}
          注册
        </Button>
      </form>
    </Form>
  )
}

export default RegisterForm

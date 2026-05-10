/** 消息列表组件

  使用 CSS content-visibility: auto 实现浏览器原生虚拟化，
  替代 JS 虚拟化（react-virtuoso），避免 mount/destroy 抖动。
  参考 Open WebUI 的实现方式。
*/

import React, { useEffect, useRef, useMemo } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useWorkbenchStore } from '../stores/workbench-store'
import { MessageBubble, StreamingBubble } from './MessageBubble'

export const MessageList = React.memo(function MessageList() {
  const scrollRef = useRef<HTMLDivElement>(null)
  const sentinelRef = useRef<HTMLDivElement>(null)
  const messages = useWorkbenchStore((s) => s.messages)
  const streamingMessage = useWorkbenchStore((s) => s.streamingMessage)
  const isStreaming = useWorkbenchStore((s) => s.isStreaming)
  const messagesLoading = useWorkbenchStore((s) => s.messagesLoading)
  const currentSession = useWorkbenchStore((s) => s.currentSession)
  const hasMoreMessages = useWorkbenchStore((s) => s.hasMoreMessages)
  const loadingOlder = useWorkbenchStore((s) => s.loadingOlder)
  const loadOlderMessages = useWorkbenchStore((s) => s.loadOlderMessages)
  const prevCountRef = useRef(0)
  const prevSessionIdRef = useRef<number | null>(null)

  const isEmpty = messages.length === 0 && !isStreaming && !messagesLoading

  // 将 flat messages 分组：assistant 消息后的连续 tool 消息归入同一组
  const groupedMessages = useMemo(() => {
    const groups: { type: 'user' | 'system' | 'assistant'; message: typeof messages[0]; toolCalls?: typeof messages }[] = []
    let i = 0
    while (i < messages.length) {
      const msg = messages[i]
      if (msg.role === 'assistant') {
        const toolCalls: typeof messages = []
        let j = i + 1
        while (j < messages.length && messages[j].role === 'tool') {
          toolCalls.push(messages[j])
          j++
        }
        groups.push({ type: 'assistant', message: msg, toolCalls })
        i = j
      } else {
        groups.push({ type: msg.role as 'user' | 'system', message: msg })
        i++
      }
    }
    return groups
  }, [messages])

  // Reset counter when switching sessions
  useEffect(() => {
    if (currentSession?.id !== prevSessionIdRef.current) {
      prevSessionIdRef.current = currentSession?.id ?? null
      prevCountRef.current = 0
    }
  }, [currentSession?.id])

  // Scroll to bottom when messages first load or new messages arrive
  useEffect(() => {
    const prevCount = prevCountRef.current
    prevCountRef.current = messages.length

    if (isEmpty) return

    const isFirstLoad = prevCount === 0 && messages.length > 0
    if (isFirstLoad) {
      setTimeout(() => {
        const el = scrollRef.current
        if (el) el.scrollTop = el.scrollHeight
      }, 50)
    } else {
      const el = scrollRef.current
      if (!el) return
      const threshold = 120
      const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold
      if (isAtBottom) {
        requestAnimationFrame(() => {
          el.scrollTop = el.scrollHeight
        })
      }
    }
  }, [messages, isEmpty])

  // Auto-scroll during streaming
  useEffect(() => {
    if (!streamingMessage) return
    const el = scrollRef.current
    if (!el) return
    requestAnimationFrame(() => {
      el.scrollTop = el.scrollHeight
    })
  }, [streamingMessage])

  // IntersectionObserver for loading older messages on scroll-up
  useEffect(() => {
    if (!hasMoreMessages || loadingOlder) return
    const sentinel = sentinelRef.current
    if (!sentinel) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && hasMoreMessages && !loadingOlder) {
          loadOlderMessages()
        }
      },
      { root: scrollRef.current, threshold: 0.1 },
    )
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [hasMoreMessages, loadingOlder, loadOlderMessages])

  return (
    <ScrollArea ref={scrollRef} className="flex-1 overflow-y-auto">
      {messagesLoading ? (
        <div className="space-y-4 p-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className={`flex gap-3 ${i % 2 === 0 ? 'justify-start' : 'justify-end'}`}>
              {i % 2 === 0 && <div className="size-8 shrink-0 rounded-full bg-muted animate-pulse" />}
              <div className="max-w-[60%] space-y-2">
                <div className="h-4 w-48 rounded bg-muted animate-pulse" />
                <div className="h-4 w-32 rounded bg-muted animate-pulse" />
              </div>
              {i % 2 !== 0 && <div className="size-8 shrink-0 rounded-full bg-muted animate-pulse" />}
            </div>
          ))}
        </div>
      ) : isEmpty ? (
        <div className="flex min-h-[60vh] items-center justify-center text-muted-foreground text-sm">
          <div className="text-center space-y-2">
            <div className="text-4xl">💬</div>
            <p>开始对话吧</p>
          </div>
        </div>
      ) : (
        <div className="space-y-4 p-4">
          {hasMoreMessages && (
            <div ref={sentinelRef} className="flex justify-center py-2">
              {loadingOlder && (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
              )}
            </div>
          )}
          {groupedMessages.map((group) => (
            <div
              key={group.message.id}
              style={{ contentVisibility: 'auto', containIntrinsicSize: 'auto 80px' }}
            >
              <MessageBubble
                message={group.message}
                toolCalls={group.toolCalls}
              />
            </div>
          ))}
          {isStreaming && streamingMessage && <StreamingBubble message={streamingMessage} />}
        </div>
      )}
    </ScrollArea>
  )
})

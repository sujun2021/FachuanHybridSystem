/**
 * useExpressTasks Hook
 * 快递查询任务列表
 */

import { useQuery } from '@tanstack/react-query'
import { expressQueryApi } from '../api'

export function useExpressTasks() {
  return useQuery({
    queryKey: ['express-tasks'],
    queryFn: () => expressQueryApi.list(),
    staleTime: 60 * 1000,
  })
}

export default useExpressTasks

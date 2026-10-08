import { useQuery } from "@tanstack/react-query";
import { getViolations, getMetrics, getAreas, getWorkers, getEdgeStatus } from "@/api/apiClient";

// A placa envia infrações a qualquer momento; o polling mantém todas as telas atualizadas.
const LIVE_INTERVAL = 5000;
const STATUS_INTERVAL = 10000;

export const useViolations = () =>
  useQuery({ queryKey: ["violations"], queryFn: getViolations, refetchInterval: LIVE_INTERVAL });

export const useMetrics = () =>
  useQuery({ queryKey: ["metrics"], queryFn: getMetrics, refetchInterval: LIVE_INTERVAL });

export const useAreas = () =>
  useQuery({ queryKey: ["areas"], queryFn: getAreas, refetchInterval: STATUS_INTERVAL });

export const useWorkers = () => useQuery({ queryKey: ["workers"], queryFn: getWorkers });

export const useEdgeStatus = () =>
  useQuery({ queryKey: ["edge-status"], queryFn: getEdgeStatus, refetchInterval: STATUS_INTERVAL });

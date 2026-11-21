import { apiClient } from "./api";
import { ApiResponse } from "../types";
import {
  AnalyticsSummary,
  TossAnalysisResponse,
  BattingAnalysisResponse,
  TeamRatingAnalysisResponse,
  PlayerPerformanceResponse,
  MatchStatisticsResponse,
  CorrelationMatrixResponse,
  WinPredictionRequest,
  WinPredictionResponse,
} from "../types/analytics";

/**
 * Safely extracts payload data from ApiResponse envelope or bare response.
 */
function unpack<T>(res: { data: ApiResponse<T> | T }): T {
  if (res.data && typeof res.data === "object" && "data" in res.data && res.data.data !== undefined) {
    return res.data.data as T;
  }
  return res.data as T;
}

export const analyticsService = {
  getSummary: async (): Promise<AnalyticsSummary> => {
    const res = await apiClient.get<ApiResponse<AnalyticsSummary>>("/api/analytics/summary");
    return unpack<AnalyticsSummary>(res);
  },

  getTossAnalysis: async (): Promise<TossAnalysisResponse> => {
    const res = await apiClient.get<ApiResponse<TossAnalysisResponse>>("/api/analytics/toss-analysis");
    return unpack<TossAnalysisResponse>(res);
  },

  getBattingAnalysis: async (): Promise<BattingAnalysisResponse> => {
    const res = await apiClient.get<ApiResponse<BattingAnalysisResponse>>("/api/analytics/batting-analysis");
    return unpack<BattingAnalysisResponse>(res);
  },

  getTeamRatingAnalysis: async (): Promise<TeamRatingAnalysisResponse> => {
    const res = await apiClient.get<ApiResponse<TeamRatingAnalysisResponse>>("/api/analytics/team-rating");
    return unpack<TeamRatingAnalysisResponse>(res);
  },

  getPlayerPerformance: async (): Promise<PlayerPerformanceResponse> => {
    const res = await apiClient.get<ApiResponse<PlayerPerformanceResponse>>("/api/analytics/player-performance");
    return unpack<PlayerPerformanceResponse>(res);
  },

  getMatchStatistics: async (): Promise<MatchStatisticsResponse> => {
    const res = await apiClient.get<ApiResponse<MatchStatisticsResponse>>("/api/analytics/match-statistics");
    return unpack<MatchStatisticsResponse>(res);
  },

  getCorrelationMatrix: async (): Promise<CorrelationMatrixResponse> => {
    const res = await apiClient.get<ApiResponse<CorrelationMatrixResponse>>("/api/analytics/correlation-matrix");
    return unpack<CorrelationMatrixResponse>(res);
  },

  predictWin: async (req: WinPredictionRequest): Promise<WinPredictionResponse> => {
    const res = await apiClient.post<ApiResponse<WinPredictionResponse>>("/api/analytics/predict-win", req);
    return unpack<WinPredictionResponse>(res);
  },

  generateDemoData: async (count: number = 15): Promise<{ message: string; matches_generated: number; total_matches: number }> => {
    const res = await apiClient.post<ApiResponse<{ message: string; matches_generated: number; total_matches: number }>>(
      `/api/analytics/generate-demo-data?count=${count}`
    );
    return unpack<{ message: string; matches_generated: number; total_matches: number }>(res);
  },
};

import { apiClient } from "./api";
import { ApiResponse, PaginatedResponse } from "../types";
import { MatchHistoryItem, MatchHistoryDetail } from "../types/history";

export const historyService = {
  /**
   * Fetches paginated completed matches from SQLite match archives.
   */
  async getMatchHistory(
    page: number = 1,
    pageSize: number = 10
  ): Promise<PaginatedResponse<MatchHistoryItem>> {
    try {
      const response = await apiClient.get<PaginatedResponse<MatchHistoryItem>>("/api/history", {
        params: { page, page_size: pageSize },
      });
      const data = response.data;
      console.log(`Loaded ${data.total} matches (page ${data.page}/${data.total_pages})`);
      return data;
    } catch (error) {
      console.error("Failed to load match history from SQLite backend:", error);
      throw error;
    }
  },

  /**
   * Fetches the complete authoritative scorecard for a historical match.
   */
  async getMatchDetail(matchId: number): Promise<MatchHistoryDetail> {
    try {
      const response = await apiClient.get<ApiResponse<MatchHistoryDetail>>(`/api/history/${matchId}`);
      return response.data.data;
    } catch (error) {
      console.error(`Failed to load details for match ${matchId}:`, error);
      throw error;
    }
  },
};

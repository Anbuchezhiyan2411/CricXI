import { apiClient } from "./api";
import { ApiResponse, DraftStateResponse, Player } from "../types";

export interface MakePickRequest {
  user_id: string;
  player_id: number;
  batting_position: number;
}

export const draftService = {
  /**
   * Initializes / starts the 11-round draft engine for the room.
   */
  async startDraft(roomCode: string): Promise<DraftStateResponse> {
    const response = await apiClient.post<ApiResponse<DraftStateResponse>>(
      `/api/draft/${roomCode.trim().toUpperCase()}/start`
    );
    return response.data.data;
  },

  /**
   * Retrieves full real-time draft state for reconnection and initial sync.
   */
  async getDraftState(roomCode: string, userId?: string): Promise<DraftStateResponse> {
    const params = userId ? { user_id: userId } : {};
    const response = await apiClient.get<ApiResponse<DraftStateResponse>>(
      `/api/draft/${roomCode.trim().toUpperCase()}/state`,
      { params }
    );
    return response.data.data;
  },

  /**
   * Submits a player draft pick at a designated batting slot.
   */
  async makePick(
    roomCode: string,
    payload: MakePickRequest
  ): Promise<DraftStateResponse> {
    const response = await apiClient.post<ApiResponse<DraftStateResponse>>(
      `/api/draft/${roomCode.trim().toUpperCase()}/pick`,
      payload
    );
    return response.data.data;
  },

  /**
   * Fetches the current round's candidate player pool.
   */
  async getPool(roomCode: string): Promise<Player[]> {
    const response = await apiClient.get<ApiResponse<Player[]>>(
      `/api/draft/${roomCode.trim().toUpperCase()}/pool`
    );
    return response.data.data;
  },
};


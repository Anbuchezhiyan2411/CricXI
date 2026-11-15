import { apiClient } from "./api";
import {
  ApiResponse,
  TossCallRequest,
  TossDecisionRequest,
  TossStateResponse,
} from "../types";

export const tossService = {
  /**
   * Initializes or fetches the toss state for the specified room.
   */
  async initToss(roomCode: string, userId?: string): Promise<TossStateResponse> {
    const params = userId ? { user_id: userId } : {};
    const response = await apiClient.post<ApiResponse<TossStateResponse>>(
      `/api/toss/${roomCode.trim().toUpperCase()}/init`,
      null,
      { params }
    );
    return response.data.data;
  },

  /**
   * Retrieves the current toss state for the specified room.
   */
  async getTossState(roomCode: string, userId?: string): Promise<TossStateResponse> {
    const params = userId ? { user_id: userId } : {};
    const response = await apiClient.get<ApiResponse<TossStateResponse>>(
      `/api/toss/${roomCode.trim().toUpperCase()}/state`,
      { params }
    );
    return response.data.data;
  },

  /**
   * Designated caller submits HEADS or TAILS call.
   */
  async makeCall(
    roomCode: string,
    payload: TossCallRequest
  ): Promise<TossStateResponse> {
    const response = await apiClient.post<ApiResponse<TossStateResponse>>(
      `/api/toss/${roomCode.trim().toUpperCase()}/call`,
      payload
    );
    return response.data.data;
  },

  /**
   * Toss winner submits pitch decision (BAT or BOWL).
   */
  async makeDecision(
    roomCode: string,
    payload: TossDecisionRequest
  ): Promise<TossStateResponse> {
    const response = await apiClient.post<ApiResponse<TossStateResponse>>(
      `/api/toss/${roomCode.trim().toUpperCase()}/decision`,
      payload
    );
    return response.data.data;
  },
};


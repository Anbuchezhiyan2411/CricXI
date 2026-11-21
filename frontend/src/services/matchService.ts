import { apiClient } from "./api";
import {
  ApiResponse,
  LiveMatchStateResponse,
  SimulationControlRequest,
} from "../types";

export const matchService = {
  /**
   * Initializes or fetches the live T20 match for the specified room.
   */
  async initMatch(
    roomCode: string,
    autoStart = true
  ): Promise<LiveMatchStateResponse> {
    const code = roomCode.trim().toUpperCase();
    const response = await apiClient.post<ApiResponse<LiveMatchStateResponse>>(
      `/api/matches/${code}/init`,
      null,
      { params: { auto_start: autoStart } }
    );
    return response.data.data;
  },

  /**
   * Retrieves authoritative match state, figures, commentary, and scorecards.
   */
  async getMatchState(roomCode: string): Promise<LiveMatchStateResponse> {
    const code = roomCode.trim().toUpperCase();
    const response = await apiClient.get<ApiResponse<LiveMatchStateResponse>>(
      `/api/matches/${code}/state`
    );
    return response.data.data;
  },

  /**
   * Rapidly simulates the match to completion in the background and returns the final scorecard.
   */
  async simulateMatch(roomCode: string): Promise<LiveMatchStateResponse> {
    const code = roomCode.trim().toUpperCase();
    const response = await apiClient.post<ApiResponse<LiveMatchStateResponse>>(
      `/api/matches/${code}/simulate`
    );
    return response.data.data;
  },

  /**
   * Manually steps simulation by one ball (for manual testing/playback).
   */
  async stepDelivery(roomCode: string): Promise<LiveMatchStateResponse> {
    const code = roomCode.trim().toUpperCase();
    const response = await apiClient.post<ApiResponse<LiveMatchStateResponse>>(
      `/api/matches/${code}/step`
    );
    return response.data.data;
  },

  /**
   * Sends play, pause, resume, or speed change controls.
   */
  async controlSimulation(
    roomCode: string,
    req: SimulationControlRequest
  ): Promise<LiveMatchStateResponse> {
    const code = roomCode.trim().toUpperCase();
    const response = await apiClient.post<ApiResponse<LiveMatchStateResponse>>(
      `/api/matches/${code}/control`,
      req
    );
    return response.data.data;
  },
};


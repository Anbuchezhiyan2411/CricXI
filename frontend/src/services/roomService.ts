import { apiClient } from "./api";
import { ApiResponse, PlayAgainResponse, Room, RoomValidateResponse } from "../types";

export const roomService = {
  /**
   * Creates a new multiplayer room with host registration.
   */
  async createRoom(username: string): Promise<Room> {
    const response = await apiClient.post<ApiResponse<Room>>("/api/rooms/create", {
      username: username.trim(),
    });
    return response.data.data;
  },

  /**
   * Joins an existing room with 6-character room code.
   */
  async joinRoom(roomCode: string, username: string, userId?: string): Promise<Room> {
    const response = await apiClient.post<ApiResponse<Room>>("/api/rooms/join", {
      room_code: roomCode.trim().toUpperCase(),
      username: username.trim(),
      user_id: userId,
    });
    return response.data.data;
  },

  /**
   * Leaves a room. Destroys the room if no players remain.
   */
  async leaveRoom(roomCode: string, userId: string): Promise<{ room_destroyed: boolean; room?: Room }> {
    const response = await apiClient.post<ApiResponse<{ room_destroyed: boolean; room?: Room }>>("/api/rooms/leave", {
      room_code: roomCode.trim().toUpperCase(),
      user_id: userId,
    });
    return response.data.data;
  },

  /**
   * Fetches the current room state by room code.
   */
  async getRoom(roomCode: string): Promise<Room> {
    const response = await apiClient.get<ApiResponse<Room>>(`/api/rooms/${roomCode.trim().toUpperCase()}`);
    return response.data.data;
  },

  /**
   * Pre-validates if a room code exists, is valid, joinable, or available for reconnect.
   */
  async validateRoom(roomCode: string, username?: string, userId?: string): Promise<RoomValidateResponse> {
    const params = new URLSearchParams();
    if (username) params.append("username", username.trim());
    if (userId) params.append("user_id", userId.trim());
    const query = params.toString() ? `?${params.toString()}` : "";
    const response = await apiClient.get<ApiResponse<RoomValidateResponse>>(
      `/api/rooms/validate/${roomCode.trim().toUpperCase()}${query}`
    );
    return response.data.data;
  },

  /**
   * Host starts the game once both players are ready.
   */
  async startGame(roomCode: string, userId: string): Promise<Room> {
    const response = await apiClient.post<ApiResponse<Room>>("/api/rooms/start", {
      room_code: roomCode.trim().toUpperCase(),
      user_id: userId,
    });
    return response.data.data;
  },

  /**
   * Starts a fresh rematch for both players.
   */
  async playAgain(roomCode: string, userId: string): Promise<PlayAgainResponse> {
    const response = await apiClient.post<ApiResponse<PlayAgainResponse>>(
      `/api/rooms/${roomCode.trim().toUpperCase()}/play-again`,
      {
        user_id: userId,
      }
    );
    return response.data.data;
  },
};

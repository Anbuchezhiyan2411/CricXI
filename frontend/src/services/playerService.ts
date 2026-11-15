import { apiClient } from "./api";
import { FilterOptions, PaginatedResponse, Player } from "../types";

export interface PlayerFilters {
  country?: string;
  decade?: number;
  role?: string;
  search?: string;
  page?: number;
  pageSize?: number;
}

export const playerService = {
  /**
   * Fetches filter options (countries, decades, roles).
   */
  async getFilterOptions(): Promise<FilterOptions> {
    const response = await apiClient.get<FilterOptions>("/api/players/meta/filters");
    return response.data;
  },

  /**
   * Fetches paginated players with optional query filters.
   */
  async getPlayers(filters: PlayerFilters = {}): Promise<PaginatedResponse<Player>> {
    const params: Record<string, string | number> = {};
    if (filters.country) params.country = filters.country;
    if (filters.decade) params.decade = filters.decade;
    if (filters.role) params.role = filters.role;
    if (filters.search) params.search = filters.search;
    if (filters.page) params.page = filters.page;
    if (filters.pageSize) params.page_size = filters.pageSize;

    const response = await apiClient.get<PaginatedResponse<Player>>("/api/players", { params });
    return response.data;
  },

  /**
   * Fetches a single player by ID.
   */
  async getPlayerById(playerId: number): Promise<Player> {
    const response = await apiClient.get<Player>(`/api/players/${playerId}`);
    return response.data;
  },

  /**
   * Fetches players for a country and decade draft round.
   */
  async getPlayersByCountryAndDecade(country: string, decade: number): Promise<Player[]> {
    const response = await apiClient.get<Player[]>(`/api/players/country/${country}/decade/${decade}`);
    return response.data;
  },
};


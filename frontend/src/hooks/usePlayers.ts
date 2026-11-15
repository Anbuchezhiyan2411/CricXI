import { useState, useEffect, useCallback } from "react";
import { playerService, PlayerFilters } from "../services/playerService";
import { FilterOptions, Player } from "../types";

export function usePlayers(initialFilters: PlayerFilters = {}) {
  const [players, setPlayers] = useState<Player[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [filters, setFilters] = useState<PlayerFilters>(initialFilters);
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchFilters = useCallback(async () => {
    try {
      const opts = await playerService.getFilterOptions();
      setFilterOptions(opts);
    } catch (err: any) {
      console.warn("Could not load filter metadata:", err.message);
    }
  }, []);

  const fetchPlayers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await playerService.getPlayers(filters);
      setPlayers(response.items);
      setTotal(response.total);
      setTotalPages(response.total_pages);
    } catch (err: any) {
      setError(err.message || "Failed to load players");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchFilters();
  }, [fetchFilters]);

  useEffect(() => {
    fetchPlayers();
  }, [fetchPlayers]);

  const updateFilters = (newFilters: Partial<PlayerFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters, page: newFilters.page ?? 1 }));
  };

  return {
    players,
    total,
    totalPages,
    filters,
    filterOptions,
    loading,
    error,
    updateFilters,
    refresh: fetchPlayers,
  };
}


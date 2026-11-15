import axios from "axios";
import { API_BASE_URL } from "../utils/constants";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || "An unexpected error occurred.";
    console.error("API Error:", message);
    return Promise.reject(new Error(message));
  }
);


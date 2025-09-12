import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "/api/v1/",
  withCredentials: true,
});

export async function getTracks() {
  return api.get(`tracks/`).then((response) => {
    return response.data.results || response.data;
  });
}

export default api;
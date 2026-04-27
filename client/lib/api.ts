import {
  getToken,
} from "@/lib/auth";
import { dispatchBackendDown, dispatchBackendUp } from "@/components/layout/connection-banner";
import type {
  AgentRun,
  ChartData,
  DashboardData,
  MessageResponse,
  MLModel,
  ModelsOverview,
  ModelAccuracyData,
  PaginatedTransactions,
  Portfolio,
  TickerSearchResult,
  TransactionFilters,
  User,
  UserRole,
} from "@/lib/types";

const API_PREFIX = "/api/v1";

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const hasBody = options.body !== undefined;
  if (hasBody) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${API_PREFIX}${path}`, {
      ...options,
      headers,
      credentials: "same-origin",
      body: hasBody ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    // Network error — backend is likely cold-starting or unreachable
    dispatchBackendDown();
    throw new ApiError("Cannot reach the server. It may be starting up, please wait.", 0);
  }

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.clear();
      document.cookie = "token=; max-age=0; path=/";
      document.cookie = "role=; max-age=0; path=/";
      document.cookie = "email=; max-age=0; path=/";
      window.location.href = "/login";
      return undefined as T;
    }

    // 503 = Render cold-start; signal the connection banner
    if (response.status === 503 || response.status === 0) {
      dispatchBackendDown();
    }
    let message = `Request failed (${response.status})`;
    const text = await response.text();
    if (text) {
      try {
        const data = JSON.parse(text) as { detail?: string; error?: string; message?: string };
        message = data.detail ?? data.error ?? data.message ?? text;
      } catch {
        message = text;
      }
    }
    throw new ApiError(message, response.status);
  }

  // Successful response — dismiss any "backend starting" banner
  dispatchBackendUp();

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function login(email: string, password: string) {
  return request<{ token: string; role: UserRole; email: string }>("/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

export async function getMe() {
  return request<User>("/auth/me");
}

export async function getPortfolios() {
  return request<Portfolio[]>("/portfolios");
}

export async function getPortfolio(portfolioId: string) {
  return request<Portfolio>(`/portfolios/${portfolioId}`);
}

export async function createPortfolio(payload: {
  name: string;
  description?: string;
  starting_capital: number;
  tickers: string[];
}) {
  return request<Portfolio>("/portfolios", {
    method: "POST",
    body: payload,
  });
}

export async function updatePortfolio(
  portfolioId: string,
  payload: {
    name?: string;
    description?: string;
    is_active?: boolean;
  }
) {
  return request<Portfolio>(`/portfolios/${portfolioId}`, {
    method: "PATCH",
    body: payload,
  });
}

export async function deletePortfolio(portfolioId: string) {
  return request<MessageResponse>(`/portfolios/${portfolioId}`, {
    method: "DELETE",
  });
}

export async function addTickers(portfolioId: string, tickers: string[]) {
  return request<MessageResponse>(`/portfolios/${portfolioId}/tickers`, {
    method: "POST",
    body: { tickers },
  });
}

export async function removeTicker(portfolioId: string, ticker: string) {
  return request<MessageResponse>(`/portfolios/${portfolioId}/tickers/${ticker}`, {
    method: "DELETE",
  });
}

export async function getDashboard(portfolioId: string) {
  return request<DashboardData>(`/dashboard/${portfolioId}`);
}

export async function getChartData(portfolioId: string, period = "1M") {
  const params = new URLSearchParams({ period });
  return request<ChartData>(`/dashboard/${portfolioId}/chart?${params.toString()}`);
}

export async function getTransactions(
  portfolioId: string,
  filters: TransactionFilters = {}
) {
  const params = new URLSearchParams();

  if (filters.limit !== undefined) params.set("limit", String(filters.limit));
  if (filters.offset !== undefined) params.set("offset", String(filters.offset));
  if (filters.ticker) params.set("ticker", filters.ticker);
  if (filters.action) params.set("action", filters.action);
  if (filters.search) params.set("search", filters.search);
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);

  const query = params.toString();
  const suffix = query ? `?${query}` : "";

  return request<PaginatedTransactions>(
    `/portfolios/${portfolioId}/transactions${suffix}`
  );
}

export async function searchTickers(query: string) {
  const params = new URLSearchParams({ q: query });
  return request<TickerSearchResult[]>(`/market/search?${params.toString()}`);
}

export async function getModels(options: { portfolioId?: string } = {}) {
  const params = new URLSearchParams();
  if (options.portfolioId) {
    params.set("portfolio_id", options.portfolioId);
  }

  return request<MLModel[]>(`/models${params.size ? `?${params.toString()}` : ""}`);
}

export async function trainTicker(ticker: string) {
  return request<MessageResponse>(`/models/train/${ticker.toUpperCase()}`, {
    method: "POST",
  });
}

export async function retrainAll(portfolioId?: string) {
  const params = new URLSearchParams();
  if (portfolioId) {
    params.set("portfolio_id", portfolioId);
  }

  return request<MessageResponse>(
    `/models/retrain-all${params.size ? `?${params.toString()}` : ""}`,
    {
      method: "POST",
    }
  );
}

export async function getModelsOverview(portfolioId?: string) {
  const params = new URLSearchParams();
  if (portfolioId) {
    params.set("portfolio_id", portfolioId);
  }

  return request<ModelsOverview>(
    `/models/overview${params.size ? `?${params.toString()}` : ""}`
  );
}

export async function getModelAccuracy(ticker: string, modelType?: string) {
  const params = new URLSearchParams();
  if (modelType) params.set("model_type", modelType);
  const query = params.toString();
  return request<ModelAccuracyData>(
    `/models/${ticker.toUpperCase()}/accuracy${query ? `?${query}` : ""}`
  );
}

export async function triggerAgentRun(portfolioId: string) {
  return request<AgentRun>(`/agent/${portfolioId}/run`, {
    method: "POST",
  });
}

export async function getAgentRuns(portfolioId: string) {
  return request<AgentRun[]>(`/agent/${portfolioId}/runs`);
}

export async function pauseAgent(portfolioId: string) {
  return request<MessageResponse>(`/agent/${portfolioId}/pause`, {
    method: "POST",
  });
}

export async function resumeAgent(portfolioId: string) {
  return request<MessageResponse>(`/agent/${portfolioId}/resume`, {
    method: "POST",
  });
}

export async function getUsers() {
  return request<User[]>("/admin/users");
}

export async function createUser(email: string, password: string) {
  return request<MessageResponse>("/admin/users", {
    method: "POST",
    body: { email, password },
  });
}

export async function updateUser(
  userId: string,
  payload: { email?: string; password?: string }
) {
  return request<MessageResponse>(`/admin/users/${userId}`, {
    method: "PATCH",
    body: payload,
  });
}

export async function deleteUser(userId: string) {
  return request<MessageResponse>(`/admin/users/${userId}`, {
    method: "DELETE",
  });
}

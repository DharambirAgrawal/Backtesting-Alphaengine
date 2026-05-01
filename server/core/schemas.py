import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class APIModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={Decimal: float, uuid.UUID: str},
        protected_namespaces=(),
    )


class MessageResponse(APIModel):
    message: str


class LoginRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=1)


class LoginResponse(APIModel):
    token: str
    role: Literal["admin", "user"]
    email: EmailStr


class UserCreateRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserUpdateRequest(APIModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)


class UserOut(APIModel):
    id: uuid.UUID
    email: EmailStr
    role: Literal["admin", "user"]
    is_active: bool
    created_at: datetime


class PortfolioCreateRequest(APIModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    starting_capital: float = Field(gt=0)
    tickers: list[str] = Field(default_factory=list, max_length=50)


class PortfolioUpdateRequest(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    is_active: bool | None = None


class CashAdjustmentRequest(APIModel):
    amount: float = Field(gt=0)
    note: str | None = None


class AddTickersRequest(APIModel):
    tickers: list[str] = Field(min_length=1, max_length=50)


class PortfolioOut(APIModel):
    id: uuid.UUID
    name: str
    description: str | None
    starting_capital: float
    current_cash: float
    holdings_value: float
    total_value: float
    profit_loss: float
    profit_loss_pct: float
    is_active: bool
    tickers: list[str]
    created_at: datetime


class HoldingOut(APIModel):
    ticker: str
    shares: float
    avg_buy_price: float
    current_price: float
    value: float
    profit_loss: float
    profit_loss_pct: float


class TransactionOut(APIModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    ticker: str
    action: Literal["BUY", "SELL", "HOLD"]
    shares: float
    price_at_trade: float
    total_value: float
    llm_reasoning: str
    tools_called: dict[str, Any]
    executed_at: datetime


class PaginatedTransactionsOut(APIModel):
    transactions: list[TransactionOut]
    total: int
    limit: int
    offset: int


class AgentRunOut(APIModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    run_type: str | None
    session: str | None
    summary: str | None
    trades_made: int
    total_pl: float
    started_at: datetime
    completed_at: datetime | None
    status: Literal["running", "done", "failed", "skipped"]


class AgentRunTickerDetailOut(APIModel):
    ticker: str
    action: Literal["BUY", "SELL", "HOLD"] | str
    llm_reasoning: str
    tools_called: dict[str, Any]
    transaction: TransactionOut | None = None
    summary_line: str | None = None


class AgentRunDetailOut(AgentRunOut):
    evaluations: list[AgentRunTickerDetailOut]
    held_all_positions: bool = False


class PerformanceStatsOut(APIModel):
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate: float
    total_trades: int
    profitable_trades: int
    best_trade: dict[str, Any]
    worst_trade: dict[str, Any]


class DashboardOut(APIModel):
    portfolio: PortfolioOut
    performance: PerformanceStatsOut
    holdings: list[HoldingOut]
    recent_transactions: list[TransactionOut]
    agent_runs: list[AgentRunOut]
    next_run: str | None


class ChartDataOut(APIModel):
    labels: list[str]
    total_value: list[float]
    cash: list[float]
    holdings: list[float]


class ModelOut(APIModel):
    id: uuid.UUID
    ticker: str
    model_type: Literal["lstm", "xgboost"]
    accuracy: float
    training_rows: int
    trained_at: datetime
    is_active: bool


class ModelAccuracyOut(APIModel):
    dates: list[str]
    predicted: list[float]
    actual: list[float]
    rolling_accuracy: list[float] | None = None


class ModelPortfolioReferenceOut(APIModel):
    id: uuid.UUID
    name: str
    is_active: bool


class ModelCoverageTickerOut(APIModel):
    ticker: str
    portfolios: list[ModelPortfolioReferenceOut]
    trained_model_types: list[Literal["lstm", "xgboost"]]
    missing_model_types: list[Literal["lstm", "xgboost"]]
    coverage_pct: float
    is_fully_trained: bool
    last_trained_at: datetime | None = None


class ModelOverviewSummaryOut(APIModel):
    tracked_tickers: int
    referenced_portfolios: int
    trained_model_count: int
    fully_trained_tickers: int
    missing_model_count: int


class ModelOverviewOut(APIModel):
    summary: ModelOverviewSummaryOut
    available_model_types: list[Literal["lstm", "xgboost"]]
    coverage: list[ModelCoverageTickerOut]


class ModelRetrainFailureOut(APIModel):
    ticker: str
    error: str


class ModelRetrainAllOut(APIModel):
    message: str
    total_tickers: int
    trained_count: int
    failed_count: int
    failed: list[ModelRetrainFailureOut]


class TickerSearchResultOut(APIModel):
    ticker: str
    name: str
    exchange: str
    type: str


class PriceDataOut(APIModel):
    ticker: str
    price: float
    change: float
    change_pct: float
    timestamp: str


class PriceHistoryBarOut(APIModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class NewsItemOut(APIModel):
    title: str
    source: str
    url: str
    published_at: str
    sentiment: float | None = None

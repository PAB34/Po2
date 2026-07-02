from pydantic import BaseModel


class MarketVariablePoint(BaseModel):
    period: str
    value: float
    label: str | None = None
    source: str | None = None


class MarketVariableSeries(BaseModel):
    code: str
    label: str
    unit: str
    market: str
    family: str
    periodicity: str
    points: list[MarketVariablePoint]


class MarketIndicesVariablesOut(BaseModel):
    year_from: int
    year_to: int
    series: list[MarketVariableSeries]

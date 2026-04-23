from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple, Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from getData import build_sql_database

#from logging_db import log_interaction
from datetime import datetime
import matplotlib.pyplot as plt

load_dotenv()


class ChartEngine:

    @staticmethod
    def detect_chart_type(question: str) -> str:
        q = (question or "").lower()

        if "pie" in q:
            return "pie"
        if "bar" in q:
            return "bar"
        if any(x in q for x in ["line", "trend", "over time", "monthly"]):
            return "line"

        return "bar"

    @staticmethod
    def build_title(question: str, chart_type: str) -> str:
        q = question.lower()

        if "plastics" in q:
            return "Monthly Revenue Trend — Plastics (Last 12 Months)"
        if "line of business" in q and "share" in q:
            return "Revenue Share by Line of Business"
        if "business unit" in q:
            return "Revenue by Business Unit"
        if "customer" in q:
            return "Revenue by Customer"

        if chart_type == "pie":
            return "Revenue Distribution (%)"
        if chart_type == "bar":
            return "Revenue by Category"
        if chart_type == "line":
            return "Revenue Trend Over Time"

        return "Revenue Analysis"

    @staticmethod
    def axis_labels(chart_type: str):
        return {
            "x": "Month" if chart_type == "line" else "Category",
            "y": "Revenue ($)"
        }

    @staticmethod
    def human_format():
        def fmt(x, pos):
            if x >= 1_000_000:
                return f"${x/1_000_000:.1f}M"
            elif x >= 1_000:
                return f"${x/1_000:.0f}K"
            return f"${x:.0f}"
        return fmt
    
    
    @staticmethod
    def clean_series_name(name: str):
        if not name:
            return "Total"
        return str(name).replace("Outsource - ", "").strip()
    
    @staticmethod
    def shorten_label(label, max_len=25):
        if len(label) > max_len:
            return label[:max_len] + "..."
        return label
    
    @staticmethod
    def get_palette():
        # Power BI–style palette
        return [
            "#4E79A7",  # blue
            "#F28E2B",  # orange
            "#E15759",  # red
            "#76B7B2",  # teal
            "#59A14F",  # green
            "#EDC948",  # yellow
            "#B07AA1",  # purple
            "#FF9DA7",  # pink
            "#9C755F",  # brown
            "#BAB0AC"   # gray
        ]
        
    @staticmethod
    def generate_insight(rows):
        if not rows:
            return ""

        # sort descending
        sorted_rows = sorted(rows, key=lambda r: r["value"], reverse=True)

        top = sorted_rows[0]
        total = sum(r["value"] for r in rows)

        pct = (top["value"] / total) * 100 if total else 0

        return f"Top contributor: {top['label']} ({pct:.1f}% of total)"    


def normalize_prompt(question: str) -> str:
    if not question:
        return question

    q = question.lower()

    if "plastics" in q:
        return question.replace("Plastics", "Outsource - Plastics").replace("plastics", "Outsource - Plastics")

    if "chemical" in q:
        return question.replace("Chemical", "Outsource - Chemical").replace("chemical", "Outsource - Chemical")

    mappings = {
        "dry bulk": "Dry Bulk - Trucking",
        "liquid bulk": "Liquid Bulk - Trucking",
        "bulk": "Dry Bulk - Trucking",
    }

    for key, value in mappings.items():
        if key in q:
            question = question.replace(key, value)
            question = question.replace(key.capitalize(), value)

    return question


def user_explicitly_requested_chart(question: str) -> bool:
    q = (question or "").lower()
    return any(word in q for word in ["chart", "graph", "plot", "visualize", "line graph", "bar chart", "pie chart"])


@dataclass(frozen=True)
class DatasetSpec:
    key: str
    display_name: str
    description: str
    sql_database: SQLDatabase
    allowed_objects: Sequence[str]
    guidance: str | None = None


@dataclass
class _DatasetRuntime:
    spec: DatasetSpec
    agent: Any


class CustomerChatbot:
    def __init__(self, datasets: Sequence[DatasetSpec], charts_dir: str) -> None:
        if not datasets:
            raise ValueError("At least one dataset specification is required.")

        self.max_iterations = int(os.getenv("AGENT_MAX_ITERATIONS", "12"))
        self.verbose = os.getenv("AGENT_VERBOSE", "true").lower() in {"1", "true", "yes", "on"}
        self.llm = self._build_llm()
        self.charts_dir = Path(charts_dir)
        self.charts_dir.mkdir(parents=True, exist_ok=True)

        self.dataset_map: Dict[str, _DatasetRuntime] = {}
        for spec in datasets:
            self.dataset_map[spec.key.lower()] = _DatasetRuntime(
                spec=spec,
                agent=self._build_agent(spec.sql_database),
            )

        self.default_dataset_key = datasets[0].key.lower()

        self.max_history = int(os.getenv("MEMORY_TURNS", "6"))
        self.histories: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

        self._last_sql_by_session: Dict[str, str] = {}

    # -------------------------
    # LLM / Agent
    # -------------------------

    def _build_llm(self) -> ChatOpenAI:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
        )

    def _build_agent(self, database: SQLDatabase):
        return create_sql_agent(
            llm=self.llm,
            db=database,
            verbose=self.verbose,
            max_iterations=self.max_iterations,
            agent_type="openai-tools",
            return_intermediate_steps=True,
        )

    # -------------------------
    # Dataset selection
    # -------------------------

    def _select_dataset(self, question: str) -> _DatasetRuntime:
        if len(self.dataset_map) == 1:
            return next(iter(self.dataset_map.values()))

        options = "\n".join(f"- {k}: {rt.spec.description}" for k, rt in self.dataset_map.items())
        prompt = (
            "Select the dataset key that best matches the question.\n"
            f"Datasets:\n{options}\n\n"
            f"Question: {question}\n"
            "Respond with only the dataset key."
        )

        try:
            response = self.llm.invoke(prompt)
            choice = (getattr(response, "content", "") or "").strip().lower()
        except Exception:
            return self.dataset_map[self.default_dataset_key]

        return self.dataset_map.get(choice, self.dataset_map[self.default_dataset_key])

    # -------------------------
    # Instructions
    # -------------------------

    def _build_instructions(self, spec: DatasetSpec, wants_chart: bool) -> str:
        object_hint = ", ".join(spec.allowed_objects) if spec.allowed_objects else "authorized tables/views"

        chart_instructions = (
            "The user explicitly asked for a chart. "
            "If the request is chartable:\n"
            "- For simple charts, return TWO columns: label and value.\n"
            "- For breakdowns (by Business Unit, Customer, Line of Business), return THREE columns: label, value, series.\n"
            "label must be text/date. "
            "value must be numeric. "
            "For monthly trends, use YYYY-MM for label. "
            "For monthly revenue trends, return label and value. "
            "If the trend is broken down by Business Unit, Customer, or Line of Business, return label, value, and series. "
        ) if wants_chart else (
            "Do NOT prepare chart-oriented output unless the user explicitly asks for a chart, graph, plot, or visualization. "
        )

        base = (
            f"You are a SQL data retrieval agent for {spec.display_name}. "
            f"Only issue read-only SELECT statements against {object_hint}. "
            "Never modify data. "
            "Never use SELECT *. "
            "Only select the minimum columns needed. "
            "Return compact aggregated results whenever possible. "

            "\nCRITICAL TIME-SERIES RULES:\n"
            "- For any request like 'over time', 'trend', 'by month', or 'monthly', ALWAYS aggregate.\n"
            "- NEVER return raw row-level data for time-series requests.\n"
            "- Default to the LAST 12 MONTHS when no time range is specified.\n"
            "- If the user says 'last N months', interpret it as the previous N full calendar months unless they explicitly ask for current month or MTD.\n"
            "- ALWAYS limit time-series output to a maximum of 24 periods.\n"
            "- ALWAYS order time periods chronologically ascending.\n"
            "- For monthly trends, return label and value.\n"
            "- If broken down by Business Unit, Customer, or Line of Business, return label, value, and series.\n"

            "\nCRITICAL OUTPUT SIZE RULES:\n"
            "- Never return more than 50 rows.\n"
            "- Prefer aggregated output over detailed output.\n"
            "- If a query would be large, reduce it automatically.\n"

            "\nCRITICAL COLUMN RULES:\n"
            "- Division ALWAYS maps to [Line of Business].\n"
            "- NEVER use [Business Unit] for division queries.\n"
            "- If user says 'Plastics', you MUST use [Line of Business] LIKE '%Outsource - Plastics%'.\n"

            "\nCHART RULES:\n"
            f"- {chart_instructions}\n"
            "- If the user did not explicitly ask for a chart, answer in text only.\n"
        )

        if spec.guidance:
            base += f"\nAdditional rules:\n{spec.guidance}\n"

        return base

    # -------------------------
    # Data extraction
    # -------------------------

    def _extract_chart_rows(self, result: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        rows = None

        try:
            steps = result.get("intermediate_steps") or []
            for step in reversed(steps):
                if isinstance(step, tuple) and len(step) >= 2:
                    observation = step[1]
                    if isinstance(observation, list) and observation:
                        rows = observation
                        break
        except Exception:
            rows = None

        if rows is None:
            rows = None

        if not isinstance(rows, list):
            return None

        clean_rows: List[Dict[str, Any]] = []
        for r in rows[:24]:
            if not isinstance(r, dict):
                continue

            vals = list(r.values())
            label = r.get("label", vals[0] if len(vals) > 0 else None)
            value = r.get("value", vals[1] if len(vals) > 1 else None)
            series = r.get("series", "Total")

            if label is None or value is None:
                continue

            label = str(label).strip()
            if not label:
                continue

            try:
                value = float(value)
            except Exception:
                continue

            clean_rows.append({
                "label": label,
                "value": value,
                "series": series
            })

        return clean_rows or None

    def _build_chart_spec(self, rows, question):

        if not rows:
            return None

        chart_type = ChartEngine.detect_chart_type(question)
        title = ChartEngine.build_title(question, chart_type)
        labels = ChartEngine.axis_labels(chart_type)
        
        

        has_series = any(r.get("series") not in (None, "", "Total") for r in rows)

        if chart_type == "pie":
            return {
                "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                "data": {"values": rows[:50]},
                "title": title,
                "width": 700,
                "height": 380,
                "mark": {"type": "arc", "innerRadius": 40},
                "encoding": {
                    "theta": {"field": "value", "type": "quantitative"},
                    "color": {"field": "label", "type": "nominal"},
                    "tooltip": [
                        {"field": "label", "type": "nominal"},
                        {"field": "value", "type": "quantitative", "format": "$,.2f"}
                    ]
                }
            }

        x_type = "temporal" if chart_type == "line" else "nominal"

        encoding = {
            "x": {
                "field": "label",
                "type": x_type,
                "title": labels["x"],
                "axis": {"labelAngle": -35}
            },
            "y": {
                "field": "value",
                "type": "quantitative",
                "title": labels["y"],
                "axis": {"format": "$~s"}
            },
            "tooltip": [
                {"field": "label", "type": x_type},
                {"field": "value", "type": "quantitative", "format": "$,.2f"}
            ]
        }

        if has_series:
            encoding["color"] = {"field": "series", "type": "nominal"}
            encoding["tooltip"].insert(1, {"field": "series", "type": "nominal"})

        return {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "data": {"values": rows[:50]},
            "title": title,
            "width": 700,
            "height": 380,
            "mark": {"type": "line", "point": True} if chart_type == "line" else {"type": "bar"},
            "encoding": encoding
        }

    # -------------------------
    # PNG chart generation
    # -------------------------

    def _sanitize_session_id(self, session_id: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", session_id or "session")
        return cleaned[:80]

    def _save_chart_png(self, rows, question, session_id):

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.ticker import FuncFormatter
        except:
            return None

        if not rows:
            return None

        chart_type = ChartEngine.detect_chart_type(question)
        title = ChartEngine.build_title(question, chart_type)
        labels = ChartEngine.axis_labels(chart_type)
        
        fig, ax = plt.subplots(figsize=(8, 6))

        filename = f"{session_id}_{uuid.uuid4().hex[:8]}.png"
        path = self.charts_dir / filename

        

        formatter = FuncFormatter(ChartEngine.human_format())

        if chart_type == "pie":

            # 🔥 STEP 1: REMOVE existing "Other"
            rows = [r for r in rows if str(r["label"]).lower() != "other"]

            # 🔥 STEP 2: take top 5 (cleaner)
            top = sorted(rows, key=lambda r: r["value"], reverse=True)[:5]

            # 🔥 STEP 3: group remaining
            others = sum(r["value"] for r in rows[5:])

            if others > 0:
                top.append({"label": "Other", "value": others})

            values = [r["value"] for r in top]
            colors = ChartEngine.get_palette()

            total = sum(values)

            labels_with_pct = []
            for r in top:
                pct = (r["value"] / total) * 100
                label = ChartEngine.shorten_label(
                    ChartEngine.clean_series_name(r["label"]),
                    30
                )

                # 👉 ONLY small slices get % next to label
                if pct <= 5:
                    label = f"{label} ({pct:.1f}%)"
                else:
                    label = label

                labels_with_pct.append(label)

            def autopct_func(pct):
                return f"{pct:.1f}%" if pct > 5 else ""

            ax.pie(
                values,
                labels=labels_with_pct,
                autopct=autopct_func,
                startangle=90,
                colors=[colors[i % len(colors)] for i in range(len(values))],
                wedgeprops=dict(width=0.45),
                labeldistance=1.1,   
                pctdistance=0.7 
            )

            ax.set_title(title)

        elif chart_type == "line":
            grouped = defaultdict(list)

            for r in rows:
                series_name = ChartEngine.clean_series_name(r.get("series", "Total"))
                grouped[series_name].append((r["label"], r["value"]))

            colors = ChartEngine.get_palette()

            for i, (k, pts) in enumerate(grouped.items()):
                def safe_parse(x):
                    try:
                        return datetime.strptime(str(x), "%Y-%m")
                    except:
                        return str(x)

                pts = sorted(pts, key=lambda x: safe_parse(x[0]))
                x = [p[0] for p in pts]
                y = [p[1] for p in pts]
                ax.plot(x, y, marker="o", linewidth=2, label=k, color=colors[i % len(colors)])

            ax.set_title(title)
            ax.set_xlabel(labels["x"])
            ax.set_ylabel(labels["y"])
            ax.yaxis.set_major_formatter(formatter)
            if len(grouped) > 1:
                ax.legend(title="Business Unit")

        else:
            x = [
                ChartEngine.shorten_label(
                    ChartEngine.clean_series_name(r["label"]), 30
                )
                for r in rows[:15]
            ]
            y = [r["value"] for r in rows[:15]]

            colors = ChartEngine.get_palette()

            ax.bar(x, y, color=colors[:len(x)])
            ax.set_title(title)
            ax.set_xlabel(labels["x"])
            ax.set_ylabel(labels["y"])
            ax.yaxis.set_major_formatter(formatter)

        if chart_type != "pie":
            plt.xticks(rotation=45, ha="right", fontsize=9)
        ax.grid(axis="y", linestyle="--", alpha=0.3)
        ax.set_axisbelow(True)

        fig.tight_layout()
        fig.savefig(path, dpi=160)
        plt.close(fig)

        return filename

    def _build_chart_url(self, public_base_url: str, filename: str) -> Optional[str]:
        if not filename:
            return None

        if public_base_url:
            return f"{public_base_url.rstrip('/')}/charts/{filename}"

        return f"/charts/{filename}"

    # -------------------------
    # Main answer
    # -------------------------

    def answer(self, session_id: str, message: str, public_base_url: str = "") -> dict:
        question = (message or "").strip()
        normalized_question = normalize_prompt(question)
        wants_chart = user_explicitly_requested_chart(question)

        print(f"[ORIGINAL] {question}")
        print(f"[NORMALIZED] {normalized_question}")
        print(f"[WANTS_CHART] {wants_chart}")

        if not question:
            return {"reply": "Please provide a question.", "vega_spec": None, "chart_url": None}

        history = self.histories[session_id][-self.max_history:]
        history_text = "\n".join(f"User: {q}\nAssistant: {a}" for q, a in history)

        dataset_runtime = self._select_dataset(normalized_question)
        instructions = self._build_instructions(dataset_runtime.spec, wants_chart=wants_chart)

        try:
            result: Dict[str, Any] = dataset_runtime.agent.invoke(
                {
                    "input": f"{instructions}\n\nConversation:\n{history_text}\n\nQuestion: {normalized_question}"
                }
            )
        except Exception as exc:
            return {
                "reply": f"Error processing request: {exc}",
                "vega_spec": None,
                "chart_url": None,
            }

        output = result.get("output")
        reply = output.strip() if isinstance(output, str) else "No response."

        executed_sql = None
        if executed_sql:
            cleaned = executed_sql.strip().rstrip(";")
            self._last_sql_by_session[session_id] = cleaned

        chart_spec = None
        chart_url = None

        if wants_chart:
            rows = self._extract_chart_rows(result)
            chart_spec = self._build_chart_spec(rows, question)

            if rows:
                filename = self._save_chart_png(rows, question, session_id)
                if filename:
                    chart_url = self._build_chart_url(public_base_url, filename)

            print(f"[DEBUG] CHART ROWS SAMPLE: {rows[:3] if rows else 'NONE'}")
            print(f"[DEBUG] CHART GENERATED: {'YES' if chart_spec else 'NO'}")
            print(f"[DEBUG] CHART URL: {chart_url}")

        #log_interaction(question=question, answer=reply)

        self.histories[session_id].append((question, reply))
        self.histories[session_id] = self.histories[session_id][-self.max_history:]

        return {
            "reply": reply,
            "vega_spec": chart_spec if wants_chart else None,
            "chart_url": chart_url,
        }

    def get_last_sql(self, session_id: str) -> Optional[str]:
        return self._last_sql_by_session.get(session_id)
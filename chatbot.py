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

#from logging_db import log_interaction
from datetime import datetime
import matplotlib.pyplot as plt

from nba_live import (
    get_top_scorers,
    get_top_rebounders,
    get_top_assist_leaders,
    get_player_stats,
    get_nba_standings,
    get_team_record,
    get_games_today,
    get_scoreboard,
    get_team_roster,
    get_team_leader,
    compare_players,
)

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

        if "points" in q or "scorer" in q:
            return "Points Per Player"
        if "assists" in q:
            return "Assists Per Player"
        if "rebounds" in q:
            return "Rebounds Per Player"
        if "team" in q and ("wins" in q or "best" in q):
            return "Team Wins Comparison"
        if "trend" in q or "over time" in q:
            return "Performance Trend"

        if chart_type == "pie":
            return "Stat Distribution (%)"
        if chart_type == "bar":
            return "Basketball Stats Comparison"
        if chart_type == "line":
            return "Performance Over Time"

        return "Basketball Analysis"

    @staticmethod
    def axis_labels(question: str, chart_type: str):
        q = question.lower()

        # X-axis
        if chart_type == "line":
            x_label = "Time"
        elif "team" in q or "standings" in q:
            x_label = "Team"
        else:
            x_label = "Player"

        # Y-axis
        if "points" in q or "scorer" in q:
            y_label = "Points Per Game (PPG)"
        elif "assists" in q:
            y_label = "Assists Per Game (APG)"
        elif "rebounds" in q:
            y_label = "Rebounds Per Game (RPG)"
        elif "wins" in q:
            y_label = "Wins"
        elif "losses" in q:
            y_label = "Losses"
        else:
            y_label = "Value"

        return {
            "x": x_label,
            "y": y_label,
        }

    @staticmethod
    def human_format(question: str):
        q = question.lower()

        def fmt(x, pos):
            if any(word in q for word in [
                "points", "scorer", "assists", "rebounds",
                "ppg", "apg", "rpg"
            ]):
                return f"{x:.1f}"

            if any(word in q for word in [
                "salary", "revenue", "earnings", "price"
            ]):
                if x >= 1_000_000:
                    return f"${x/1_000_000:.1f}M"
                elif x >= 1_000:
                    return f"${x/1_000:.0f}K"
                return f"${x:.0f}"

            return f"{x:,.0f}"

        return fmt
    
    
    @staticmethod
    def clean_series_name(name: str):
        if not name:
            return "Total"
        return str(name).strip()
    
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

        self.max_iterations = int(os.getenv("AGENT_MAX_ITERATIONS", "5"))
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
            timeout=30,
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
        chart_instructions = (
            "The user asked for a chart.\n"
            "Focus on generating a SQL query that returns 2 columns:\n"
            "- First column: label (player name or team)\n"
            "- Second column: numeric value (points, assists, etc.)\n"
        )

        return (
            "You are a basketball analytics AI assistant.\n\n"

            "You MUST:\n"
            "- Only generate SQL SELECT queries\n"
            "- Use the 'players' and 'teams' tables\n"
            "- Never use SELECT *\n"
            "- Only select needed columns\n"
            "- Prefer aggregated or sorted results\n"
            "- Limit results to 10–20 rows max\n\n"
            "- If the SQL query returns multiple rows, include ALL rows in the final answer.\n"

            "Basketball Rules:\n"
            "- Points = points_per_game\n"
            "- Rebounds = rebounds_per_game\n"
            "- Assists = assists_per_game\n"
            "- Team performance = wins and losses\n\n"

            "Examples:\n"
            "- 'top scorers' → ORDER BY points_per_game DESC\n"
            "- 'best teams' → ORDER BY wins DESC\n"
            "- 'top assists' → ORDER BY assists_per_game DESC\n\n"

            f"{chart_instructions}\n"

            "If the user asks a basketball question, generate the correct SQL query and return the result."
    )

    # -------------------------
    # Data extraction
    # -------------------------

    def _extract_chart_rows(self, result) -> list[tuple[str, float]]:
        """
        Extract chart rows from:
        1. SQL result tuples in the output
        2. Markdown tables in the output
        """

        output = result.get("output", "")
        rows = []

        # ----------------------------------------------------------
        # 1. Try to parse Python tuple output:
        # ('Luka Doncic', 33.9)
        # ----------------------------------------------------------
        tuple_pattern = r"\('([^']+)',\s*([\d.]+)\)"
        matches = re.findall(tuple_pattern, output)

        for label, value in matches:
            rows.append({
                "label": label,
                "value": float(value)
            })

        if rows:
            return rows

        # ----------------------------------------------------------
        # 2. Try to parse markdown table rows:
        # | Luka Doncic | 33.9 |
        # ----------------------------------------------------------
        table_pattern = r"\|\s*([^|]+?)\s*\|\s*([\d.]+)\s*\|"
        matches = re.findall(table_pattern, output)

        for label, value in matches:
            label = label.strip()

            # Skip header rows
            if label.lower() in [
                "player name",
                "team",
                "label",
                "name",
            ]:
                continue

            rows.append({
                "label": label,
                "value": float(value)
            })

        return rows

    def _build_chart_spec(self, rows, question):

        if not rows:
            return None

        chart_type = ChartEngine.detect_chart_type(question)
        title = ChartEngine.build_title(question, chart_type)
        labels = ChartEngine.axis_labels(question, chart_type)
        
        

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
        labels = ChartEngine.axis_labels(question, chart_type)
        
        fig, ax = plt.subplots(figsize=(8, 6))

        filename = f"{session_id}_{uuid.uuid4().hex[:8]}.png"
        path = self.charts_dir / filename

        

        formatter = FuncFormatter(ChartEngine.human_format(question))

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
                ax.legend(title="Series")

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

        q = question.lower()

        # -----------------------------------
        # Live NBA Data: Top Scorers
        # -----------------------------------
        if "top scorers" in q or "scoring leaders" in q:
            players = get_top_scorers(10)

            lines = ["🏀 Top 10 NBA Scorers (Live Data):", ""]

            for i, player in enumerate(players, start=1):
                lines.append(
                    f"{i}. {player['player']} ({player['team']}) - {player['value']} PPG"
                )

            return {
                "reply": "\n".join(lines),
                "vega_spec": None,
                "chart_url": None,
            }
            
            
        # -----------------------------------
        # Live NBA Data: Top Rebounders
        # -----------------------------------
        if "top rebounders" in q or "rebound leaders" in q:
            players = get_top_rebounders(10)

            lines = ["🏀 Top 10 NBA Rebound Leaders (Live Data):", ""]

            for i, player in enumerate(players, start=1):
                lines.append(
                    f"{i}. {player['player']} ({player['team']}) - {player['value']} RPG"
                )

            return {
                "reply": "\n".join(lines),
                "vega_spec": None,
                "chart_url": None,
            }   
            
            
        # -----------------------------------
        # Live NBA Data: Assist Leaders
        # -----------------------------------
        if (
            "top assists" in q
            or "assist leaders" in q
            or "top assist leaders" in q
        ):
            players = get_top_assist_leaders(10)

            lines = ["🏀 Top 10 NBA Assist Leaders (Live Data):", ""]

            for i, player in enumerate(players, start=1):
                lines.append(
                    f"{i}. {player['player']} ({player['team']}) - {player['value']} APG"
                )

            return {
                "reply": "\n".join(lines),
                "vega_spec": None,
                "chart_url": None,
            }  
            
            
        # -----------------------------------
        # Live NBA Data: Standings
        # -----------------------------------
        if (
            "standings" in q
            or "best record" in q
            or "first in the west" in q
            or "first in the east" in q
        ):
            standings = get_nba_standings(10)

            # Handle conference-specific requests
            if "west" in q:
                standings = [t for t in standings if t["conference"] == "West"][:10]
                title = "🏀 Western Conference Standings:"
            elif "east" in q:
                standings = [t for t in standings if t["conference"] == "East"][:10]
                title = "🏀 Eastern Conference Standings:"
            else:
                title = "🏀 Top 10 NBA Teams by Record:"

            lines = [title, ""]

            for team in standings:
                lines.append(
                    f"{team['rank']}. {team['team']} — "
                    f"{team['wins']}-{team['losses']} "
                    f"({team['win_pct']}%)"
                )

            return {
                "reply": "\n".join(lines),
                "vega_spec": None,
                "chart_url": None,
            }
            
            
        # -----------------------------------
        # Live NBA Data: Team Record
        # -----------------------------------
        if "record" in q and "best record" not in q:
            # Remove common words to isolate the team name
            team_name = (
                question.lower()
                .replace("what is the", "")
                .replace("what's the", "")
                .replace("what is", "")
                .replace("show me", "")
                .replace("record", "")
                .replace("of", "")
                .replace("?", "")
                .strip()
                .title()
            )

            team = get_team_record(team_name)

            if not team:
                return {
                    "reply": f"Could not find a team named {team_name}.",
                    "vega_spec": None,
                    "chart_url": None,
                }

            reply = f"""
        🏀 {team['team']}

        Record: {team['wins']}-{team['losses']}
        Win Percentage: {team['win_pct']}%
        Conference: {team['conference']}
        Conference Rank: {team['rank']}
        """.strip()

            return {
                "reply": reply,
                "vega_spec": None,
                "chart_url": None,
            }  
            
            
        # -----------------------------------
        # Live NBA Data: Games Today
        # -----------------------------------
        if (
            "who plays tonight" in q
            or "games today" in q
            or "games tonight" in q
            or "today's games" in q
            or "todays games" in q
            or "schedule today" in q
        ):
            games = get_games_today()

            if not games:
                return {
                    "reply": "🏀 There are no NBA games scheduled today.",
                    "vega_spec": None,
                    "chart_url": None,
                }

            reply = "🏀 Today's NBA Games:\n\n"

            for i, game in enumerate(games, 1):
                reply += f"{i}. {game['away']} at {game['home']}\n"

            return {
                "reply": reply.strip(),
                "vega_spec": None,
                "chart_url": None,
            }
            
            
            
        # --------------------------------
        # Live NBA Data: Team Roster
        # --------------------------------
        if (
            "roster" in q
            or "who is on the" in q
            or "who plays for" in q
        ):
            team_name = (
                question.lower()
                .replace("show me the", "")
                .replace("show", "")
                .replace("the", "")
                .replace("roster", "")
                .replace("who is on", "")
                .replace("who's on", "")
                .replace("who plays for", "")
                .strip()
                .title()
            )

            players = get_team_roster(team_name)

            if not players:
                return {
                    "reply": f"Could not find roster for {team_name}.",
                    "vega_spec": None,
                    "chart_url": None,
                }

            lines = [f"🏀 {team_name} Roster:", ""]

            for i, player in enumerate(players, start=1):
                lines.append(f"{i}. {player}")

            return {
                "reply": "\n".join(lines),
                "vega_spec": None,
                "chart_url": None,
            } 
            
            
               
        # --------------------------------
        # Live NBA Data: Team Leaders
        # --------------------------------
        if (
            "leading scorer" in q
            or "leading rebounder" in q
            or "leading assister" in q
            or "most points on" in q
            or "most rebounds on" in q
            or "most assists on" in q
        ):
            stat = "PTS"

            if "rebound" in q:
                stat = "REB"
            elif "assist" in q:
                stat = "AST"

            # Clean question to isolate team name
            team_name = (
                question.lower()
                .replace("who is the", "")
                .replace("who's the", "")
                .replace("leading scorer", "")
                .replace("leading rebounder", "")
                .replace("leading assister", "")
                .replace("most points on", "")
                .replace("most rebounds on", "")
                .replace("most assists on", "")
                .replace("for", "")
                .replace("on", "")
                .replace("?", "")
                .strip()
                .title()
            )

            leader = get_team_leader(team_name, stat)

            if not leader:
                return {
                    "reply": f"Could not find team leader data for {team_name}.",
                    "vega_spec": None,
                    "chart_url": None,
                }

            stat_label = {
                "PTS": "points",
                "REB": "rebounds",
                "AST": "assists",
            }[leader["stat"]]

            reply = (
                f"🏀 {leader['player']} leads the {leader['team']} "
                f"with {leader['value']} {stat_label} per game."
            )

            return {
                "reply": reply,
                "vega_spec": None,
                "chart_url": None,
            }
            
            
        # --------------------------------
        # Live NBA Data: Compare Players
        # --------------------------------
        if "compare" in q or " vs " in q:
            player1 = None
            player2 = None

            # Format: "Compare LeBron James and Kevin Durant"
            if "compare" in q and " and " in q:
                cleaned = (
                    question
                    .replace("Compare", "")
                    .replace("compare", "")
                    .strip()
                )
                parts = cleaned.split(" and ", 1)

                if len(parts) == 2:
                    player1 = parts[0].strip()
                    player2 = parts[1].strip()

            # Format: "LeBron James vs Kevin Durant"
            elif " vs " in q:
                # Use original question to preserve capitalization,
                # but split on lowercase for consistency.
                parts = re.split(r"\s+vs\s+", question, flags=re.IGNORECASE)

                if len(parts) == 2:
                    player1 = parts[0].strip()
                    player2 = parts[1].strip()

            if player1 and player2:
                comparison = compare_players(player1, player2)

                if not comparison:
                    return {
                        "reply": "Could not compare those players.",
                        "vega_spec": None,
                        "chart_url": None,
                    }

                p1 = comparison["player1"]
                p2 = comparison["player2"]

                reply = f"""
        🏀 Player Comparison

        {p1['player']} ({p1['team']})
        • PPG: {p1['points']}
        • RPG: {p1['rebounds']}
        • APG: {p1['assists']}
        • FG%: {p1['fg_pct']}%
        • 3PT%: {p1['three_pct']}%
        • FT%: {p1['ft_pct']}%

        {p2['player']} ({p2['team']})
        • PPG: {p2['points']}
        • RPG: {p2['rebounds']}
        • APG: {p2['assists']}
        • FG%: {p2['fg_pct']}%
        • 3PT%: {p2['three_pct']}%
        • FT%: {p2['ft_pct']}%
        """.strip()

                return {
                    "reply": reply,
                    "vega_spec": None,
                    "chart_url": None,
                }       
            
        # -----------------------------------
        # Live NBA Data: Player Stats
        # -----------------------------------
        if "stats" in q:
            player_name = (
                question.lower()
                .replace("what are", "")
                .replace("what is", "")
                .replace("show me", "")
                .replace("show", "") 
                .replace("'s", "")
                .replace("stats", "")
                .replace("?", "")
                .strip()
                .title()
            )

            stats = get_player_stats(player_name)

            if not stats:
                return {
                    "reply": f"Could not find stats for {player_name}.",
                    "vega_spec": None,
                    "chart_url": None,
                }

            reply = f"""
        🏀 {stats['player']} ({stats['team']}) — {stats['season']}

        Games Played: {stats['games']}
        Points: {stats['points']} PPG
        Rebounds: {stats['rebounds']} RPG
        Assists: {stats['assists']} APG
        FG%: {stats['fg_pct']}%
        3PT%: {stats['three_pct']}%
        FT%: {stats['ft_pct']}%
        """.strip()

            return {
                "reply": reply,
                "vega_spec": None,
                "chart_url": None,

                # Data for React player card
                "player_id": stats["player_id"],
                "player_name": stats["player"],
                "team_id": stats["team_id"],
                "team_name": stats["team"],
                "points_per_game": stats["points"],
            }

        # -----------------------------------
        # Debug Logging
        # -----------------------------------
        print(f"[ORIGINAL] {question}")
        print(f"[NORMALIZED] {normalized_question}")
        print(f"[WANTS_CHART] {wants_chart}")

        # -----------------------------------
        # Empty Question Check
        # -----------------------------------
        if not question:
            return {
                "reply": "Please provide a question.",
                "vega_spec": None,
                "chart_url": None,
            }

        # -----------------------------------
        # Conversation History
        # -----------------------------------
        history = self.histories[session_id][-self.max_history:]
        history_text = "\n".join(
            f"User: {q}\nAssistant: {a}" for q, a in history
        )

        # -----------------------------------
        # Select Dataset
        # -----------------------------------
        dataset_runtime = self._select_dataset(normalized_question)

        # -----------------------------------
        # Build Instructions
        # -----------------------------------
        instructions = self._build_instructions(
            dataset_runtime.spec,
            wants_chart=wants_chart,
        )

        # -----------------------------------
        # Run SQL Agent
        # -----------------------------------
        try:
            result: Dict[str, Any] = dataset_runtime.agent.invoke(
                {
                    "input": (
                        f"{instructions}\n\n"
                        f"Conversation:\n{history_text}\n\n"
                        f"Question: {normalized_question}"
                    )
                }
            )

            print("[DEBUG FULL RESULT]", result)

        except Exception as exc:
            return {
                "reply": f"Error processing request: {exc}",
                "vega_spec": None,
                "chart_url": None,
            }

        # -----------------------------------
        # Extract Reply
        # -----------------------------------
        output = result.get("output")
        reply = output.strip() if isinstance(output, str) else "No response."

        # -----------------------------------
        # Save Last SQL (optional)
        # -----------------------------------
        executed_sql = None
        if executed_sql:
            cleaned = executed_sql.strip().rstrip(";")
            self._last_sql_by_session[session_id] = cleaned

        # -----------------------------------
        # Chart Generation
        # -----------------------------------
        chart_spec = None
        chart_url = None

        if wants_chart:
            rows = self._extract_chart_rows(result)
            chart_spec = self._build_chart_spec(rows, question)

            if rows:
                filename = self._save_chart_png(rows, question, session_id)
                if filename:
                    chart_url = self._build_chart_url(
                        public_base_url,
                        filename
                    )

            print(
                f"[DEBUG] CHART ROWS SAMPLE: "
                f"{rows[:3] if rows else 'NONE'}"
            )
            print(
                f"[DEBUG] CHART GENERATED: "
                f"{'YES' if chart_spec else 'NO'}"
            )
            print(f"[DEBUG] CHART URL: {chart_url}")

        # -----------------------------------
        # Save Conversation History
        # -----------------------------------
        self.histories[session_id].append((question, reply))
        self.histories[session_id] = self.histories[session_id][-self.max_history:]

        # -----------------------------------
        # Final Response
        # -----------------------------------
        return {
            "reply": reply,
            "vega_spec": chart_spec if wants_chart else None,
            "chart_url": chart_url,
        }

    def get_last_sql(self, session_id: str) -> Optional[str]:
        return self._last_sql_by_session.get(session_id)
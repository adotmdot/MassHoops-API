from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.base import create_sql_agent

load_dotenv()

# =====================================================
# HELPERS
# =====================================================

def normalize_prompt(question: str) -> str:
    return (question or "").strip()


def user_explicitly_requested_chart(question: str) -> bool:

    q = (question or "").lower()

    return any(
        word in q
        for word in [
            "chart",
            "graph",
            "plot",
            "visualize",
            "bar chart",
            "line graph",
            "pie chart",
        ]
    )


def is_basketball_related(question: str) -> bool:

    q = (question or "").lower()

    basketball_words = [
        "nba",
        "wnba",
        "basketball",
        "hoops",
        "player",
        "players",
        "team",
        "teams",
        "coach",
        "coaching",
        "defense",
        "offense",
        "pick and roll",
        "zone",
        "man to man",
        "screen",
        "spacing",
        "shooting",
        "dribbling",
        "passing",
        "rebounding",
        "assist",
        "points",
        "scoring",
        "dunk",
        "layup",
        "free throw",
        "three pointer",
        "crossover",
        "post up",
        "fast break",
        "transition",
        "isolation",
        "iso",
        "mvp",
        "finals",
        "playoffs",
        "draft",
        "rookie",
        "all star",
        "hall of fame",
        "goat",
        "lebron",
        "jordan",
        "kobe",
        "curry",
        "durant",
        "giannis",
        "jokic",
        "shaq",
        "magic",
        "bird",
        "lakers",
        "celtics",
        "warriors",
        "bulls",
        "knicks",
        "heat",
        "spurs",
        "nuggets",
        "suns",
        "mavericks",
        "clippers",
        "bucks",
        "sixers",
        "76ers",
        "raptors",
        "thunder",
        "timberwolves",
        "pacers",
        "cavaliers",
        "nets",
        "pistons",
        "rockets",
        "grizzlies",
        "pelicans",
        "hawks",
        "hornets",
        "magic",
        "kings",
        "jazz",
        "trail blazers",
        "wizards",
        "fantasy basketball",
        "scouting",
        "analytics",
        "true shooting",
        "usage rate",
        "plus minus",
        "player efficiency",
        "per",
        "salary cap",
        "trade",
        "contract",
    ]

    return any(word in q for word in basketball_words)


def is_live_data_request(question: str) -> bool:

    q = (question or "").lower()

    live_phrases = [
        "today's games",
        "todays games",
        "games tonight",
        "who plays tonight",
        "live scores",
        "current standings",
        "nba standings",
        "today's scores",
        "todays scores",
        "injury report",
        "latest injury",
        "latest injuries",
        "current record",
        "current stats",
        "live stats",
        "box score",
        "score right now",
        "who won tonight",
        "schedule today",
        "today schedule",
        "today's schedule",
    ]

    return any(
        phrase in q
        for phrase in live_phrases
    )


# =====================================================
# CHART ENGINE
# =====================================================

class ChartEngine:

    @staticmethod
    def detect_chart_type(question: str) -> str:

        q = (question or "").lower()

        if "pie" in q:
            return "pie"

        if any(
            x in q
            for x in [
                "line",
                "trend",
                "over time",
                "monthly",
            ]
        ):
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

        if "team" in q and (
            "wins" in q or "best" in q
        ):
            return "Team Wins Comparison"

        if chart_type == "pie":
            return "Basketball Stat Distribution"

        if chart_type == "line":
            return "Basketball Trend"

        return "Basketball Stats Comparison"

    @staticmethod
    def axis_labels(question: str, chart_type: str):

        q = question.lower()

        if chart_type == "line":
            x_label = "Time"

        elif "team" in q:
            x_label = "Team"

        else:
            x_label = "Player"

        if "points" in q or "scorer" in q:
            y_label = "Points Per Game"

        elif "assists" in q:
            y_label = "Assists Per Game"

        elif "rebounds" in q:
            y_label = "Rebounds Per Game"

        elif "wins" in q:
            y_label = "Wins"

        else:
            y_label = "Value"

        return {
            "x": x_label,
            "y": y_label,
        }


# =====================================================
# DATASET MODELS
# =====================================================

@dataclass(frozen=True)
class DatasetSpec:
    key: str
    display_name: str
    description: str
    sql_database: SQLDatabase
    allowed_objects: Optional[Sequence[str]] = None
    guidance: Optional[str] = None


@dataclass
class _DatasetRuntime:
    spec: DatasetSpec
    agent: Any


# =====================================================
# MAIN CHATBOT
# =====================================================

class CustomerChatbot:

    def __init__(
        self,
        datasets: Sequence[DatasetSpec],
        charts_dir: str,
    ) -> None:

        if not datasets:
            raise ValueError(
                "At least one dataset specification is required."
            )

        self.max_iterations = int(
            os.getenv("AGENT_MAX_ITERATIONS", "5")
        )

        self.verbose = (
            os.getenv("AGENT_VERBOSE", "true").lower()
            in {
                "1",
                "true",
                "yes",
                "on",
            }
        )

        self.llm = self._build_llm()

        self.charts_dir = Path(charts_dir)

        self.charts_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.dataset_map: Dict[str, _DatasetRuntime] = {}

        for spec in datasets:

            self.dataset_map[spec.key.lower()] = (
                _DatasetRuntime(
                    spec=spec,
                    agent=self._build_agent(
                        spec.sql_database
                    ),
                )
            )

        self.default_dataset_key = (
            datasets[0].key.lower()
        )

        self.max_history = int(
            os.getenv("MEMORY_TURNS", "6")
        )

        self.histories: Dict[
            str,
            List[Tuple[str, str]]
        ] = defaultdict(list)

        self._last_sql_by_session: Dict[
            str,
            str
        ] = {}

    # =====================================================
    # LLM
    # =====================================================

    def _build_llm(self) -> ChatOpenAI:

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured."
            )

        return ChatOpenAI(
            model=os.getenv(
                "OPENAI_MODEL",
                "gpt-4o-mini",
            ),
            temperature=0.3,
            timeout=45,
            streaming=True,
        )

    # =====================================================
    # SQL AGENT
    # =====================================================

    def _build_agent(
        self,
        database: SQLDatabase,
    ):

        return create_sql_agent(
            llm=self.llm,
            db=database,
            verbose=self.verbose,
            max_iterations=self.max_iterations,
            agent_type="openai-tools",
            return_intermediate_steps=True,
        )

    def _select_dataset(
        self,
        question: str,
    ) -> _DatasetRuntime:

        return self.dataset_map[
            self.default_dataset_key
        ]

    # =====================================================
    # KNOWLEDGE PROMPT
    # =====================================================

    def _build_knowledge_prompt(
        self,
        question: str,
        history_text: str,
    ) -> str:

        return f"""
You are MassHoops AI, a premium basketball intelligence assistant.

You think like:
- NBA analyst
- Basketball coach
- Scout
- Historian
- Strategist

Specialties:
- NBA history
- Player comparisons
- Coaching concepts
- Basketball strategy
- Team building
- Scouting
- Analytics
- Salary cap discussions

Rules:
- Be conversational and insightful.
- Avoid generic answers.
- Use headings and bullets when useful.
- Keep answers structured and readable.
- Sound intelligent but natural.
- Never invent live NBA data.

Conversation history:
{history_text}

User question:
{question}

Answer:
""".strip()

    # =====================================================
    # MAIN ANSWER
    # =====================================================

    def answer(
        self,
        session_id: str,
        message: str,
        public_base_url: str = "",
    ) -> dict:

        question = normalize_prompt(message)

        if not question:

            return {
                "reply": (
                    "Please ask me a basketball question."
                ),
                "vega_spec": None,
                "chart_url": None,
            }

        history = self.histories[
            session_id
        ][-self.max_history:]

        history_text = "\n".join(
            f"User: {q}\nAssistant: {a}"
            for q, a in history
        )

        # =================================================
        # LIVE DATA GUARD
        # =================================================

        if is_live_data_request(question):

            reply = (
                "🏀 I currently focus on basketball knowledge, "
                "strategy, player analysis, and historical "
                "discussion rather than live NBA data."
            )

            self.histories[session_id].append(
                (question, reply)
            )

            return {
                "reply": reply,
                "vega_spec": None,
                "chart_url": None,
            }

        # =================================================
        # BASKETBALL KNOWLEDGE
        # =================================================

        if is_basketball_related(question):

            try:

                prompt = (
                    self._build_knowledge_prompt(
                        question,
                        history_text,
                    )
                )

                response = self.llm.invoke(prompt)

                reply = (
                    getattr(
                        response,
                        "content",
                        None,
                    )
                    or str(response)
                    or "No response generated."
                ).strip()

                self.histories[session_id].append(
                    (question, reply)
                )

                self.histories[session_id] = (
                    self.histories[session_id][
                        -self.max_history:
                    ]
                )

                return {
                    "reply": reply,
                    "vega_spec": None,
                    "chart_url": None,
                }

            except Exception as exc:

                print(
                    f"[ERROR] Basketball response failed: {exc}"
                )

                return {
                    "reply": (
                        "MassHoops AI had trouble generating "
                        "that response."
                    ),
                    "vega_spec": None,
                    "chart_url": None,
                }

        # =================================================
        # FALLBACK
        # =================================================

        reply = (
            "🏀 I focus on basketball-related questions."
        )

        return {
            "reply": reply,
            "vega_spec": None,
            "chart_url": None,
        }

    # =====================================================
    # STREAMING ANSWER
    # =====================================================

    async def stream_answer(
        self,
        session_id: str,
        message: str,
    ):

        question = normalize_prompt(message)

        if not question:

            yield "Please ask me a basketball question."
            return

        history = self.histories[
            session_id
        ][-self.max_history:]

        history_text = "\n".join(
            f"User: {q}\nAssistant: {a}"
            for q, a in history
        )

        # =================================================
        # LIVE DATA GUARD
        # =================================================

        if is_live_data_request(question):

            live_reply = (
                "🏀 I can discuss basketball knowledge, "
                "strategy, player analysis, and history, "
                "but live NBA data is not connected."
            )

            self.histories[session_id].append(
                (question, live_reply)
            )

            yield live_reply
            return

        # =================================================
        # BASKETBALL KNOWLEDGE STREAMING
        # =================================================

        if is_basketball_related(question):

            try:

                prompt = (
                    self._build_knowledge_prompt(
                        question,
                        history_text,
                    )
                )

                stream = self.llm.stream(prompt)

                full_reply = ""

                for chunk in stream:

                    content = getattr(
                        chunk,
                        "content",
                        "",
                    )

                    if content:

                        full_reply += content

                        yield content

                self.histories[session_id].append(
                    (question, full_reply)
                )

                self.histories[session_id] = (
                    self.histories[session_id][
                        -self.max_history:
                    ]
                )

            except Exception as exc:

                print(
                    f"[ERROR] Streaming failed: {exc}"
                )

                yield (
                    "MassHoops AI encountered an error "
                    "while streaming the response."
                )

            return

        # =================================================
        # FALLBACK
        # =================================================

        fallback = (
            "🏀 I focus on basketball-related questions."
        )

        yield fallback

    # =====================================================
    # LAST SQL
    # =====================================================

    def get_last_sql(
        self,
        session_id: str,
    ) -> Optional[str]:

        return self._last_sql_by_session.get(
            session_id
        )
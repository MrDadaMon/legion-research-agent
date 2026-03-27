import os
from datetime import datetime
from pathlib import Path

from src.storage.database import Database


class PreferenceStore:
    """Manages human-readable preferences.md synced with SQLite.

    preferences.md format:
    # Legion Preferences

    ## Preferences

    ### Topic: {topic}
    - **Approach:** {approach}
      - Preferred over: {rejected_approach}
      - Reason: {reason}
      - Stored: {date}
      - Source: content #{source_content_id}

    ## Rejections

    ### Topic: {topic}
    - **Rejected:** {approach}
      - Reason: {reason}
      - Stored: {date}
      - Source: content #{source_content_id}
    """

    def __init__(self, knowledge_dir: str = "knowledge", db: Database | None = None):
        self.preferences_path = os.path.join(knowledge_dir, "preferences.md")
        self.db = db

    async def load(self) -> str:
        """Load and return the preferences.md content."""
        if os.path.exists(self.preferences_path):
            with open(self.preferences_path, 'r', encoding='utf-8') as f:
                return f.read()
        return self._generate_empty()

    async def save(self, preferences: list[dict], rejections: list[dict]) -> None:
        """Save preferences and rejections to preferences.md.

        Groups by topic, separates preferences from rejections.
        """
        Path(self.preferences_path).parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# Legion Preferences",
            "",
            "## Preferences",
            "",
        ]

        prefs_by_topic: dict[str, list[dict]] = {}
        for pref in preferences:
            topic = pref['topic']
            if topic not in prefs_by_topic:
                prefs_by_topic[topic] = []
            prefs_by_topic[topic].append(pref)

        if not prefs_by_topic:
            lines.append("_No preferences stored._")
        else:
            for topic, prefs in sorted(prefs_by_topic.items()):
                lines.append(f"### Topic: {topic}")
                for pref in prefs:
                    lines.append(f"- **Approach:** {pref['approach']}")
                    if pref.get('reason'):
                        lines.append(f"  - Reason: {pref['reason']}")
                    date = pref.get('created_at', 'unknown')
                    if isinstance(date, str) and len(date) > 10:
                        date = date[:10]
                    lines.append(f"  - Stored: {date}")
                    if pref.get('source_content_id'):
                        lines.append(f"  - Source: content #{pref['source_content_id']}")
                    lines.append("")

        lines.extend(["", "## Rejections", ""])

        rejects_by_topic: dict[str, list[dict]] = {}
        for rej in rejections:
            topic = rej['topic']
            if topic not in rejects_by_topic:
                rejects_by_topic[topic] = []
            rejects_by_topic[topic].append(rej)

        if not rejects_by_topic:
            lines.append("_No rejections stored._")
        else:
            for topic, rejs in sorted(rejects_by_topic.items()):
                lines.append(f"### Topic: {topic}")
                for rej in rejs:
                    lines.append(f"- **Rejected:** {rej['approach']}")
                    if rej.get('reason'):
                        lines.append(f"  - Reason: {rej['reason']}")
                    date = rej.get('created_at', 'unknown')
                    if isinstance(date, str) and len(date) > 10:
                        date = date[:10]
                    lines.append(f"  - Stored: {date}")
                    if rej.get('source_content_id'):
                        lines.append(f"  - Source: content #{rej['source_content_id']}")
                    lines.append("")

        with open(self.preferences_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def _generate_empty(self) -> str:
        return """# Legion Preferences

## Preferences
_No preferences stored._

## Rejections
_No rejections stored._
"""

    async def sync_from_db(self) -> None:
        """Sync preferences.md from SQLite database."""
        if self.db is None:
            return

        preferences = await self.db.get_preferences(preference_type='prefer')
        rejections = await self.db.get_rejections()
        await self.save(preferences, rejections)

    async def sync_to_db(self) -> None:
        """Parse preferences.md and update SQLite.

        For v1, this is one-way (db -> md). User edits to md
        are not automatically synced back to db.
        """
        pass
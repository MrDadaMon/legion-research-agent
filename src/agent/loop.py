import asyncio
from dataclasses import dataclass, field

from src.config import DB_PATH, KNOWLEDGE_DIR, POLL_INTERVAL
from src.storage import Database, MarkdownStore, SyncManager


@dataclass
class AgentState:
    inbox: asyncio.Queue = field(default_factory=asyncio.Queue)
    iteration: int = 0
    running: bool = True


async def run_agent(poll_interval: float = POLL_INTERVAL):
    db = Database(db_path=DB_PATH)
    markdown_store = MarkdownStore(knowledge_dir=KNOWLEDGE_DIR)
    sync_manager = SyncManager(db, markdown_store)
    state = AgentState()

    # Import surfacing handlers
    from src.agent.handlers.surfacing_handler import (
        is_surface_query,
        extract_surface_topic,
        surface_content,
        find_proactive_surfacing,
        format_surfaced_item,
    )
    # Import rejection warnings (lazy to avoid circular imports)
    try:
        from src.agent.handlers.warning_handler import check_for_rejection_warnings
        has_warning_handler = True
    except ImportError:
        has_warning_handler = False

    try:
        while state.running:
            try:
                item = state.inbox.get_nowait()
                if item is not None:
                    from src.agent.handlers import process_content
                    await process_content(item, sync_manager)
            except asyncio.QueueEmpty:
                pass

            # NOTE: For v1, surfacing is triggered when user sends a message
            # that gets processed. The actual surfacing integration point
            # is in the message handling layer, not here in the polling loop.
            #
            # This loop handles background tasks. User messages come through
            # inbox items processed above.

            state.iteration += 1
            await asyncio.sleep(poll_interval)
    except asyncio.CancelledError:
        state.running = False
    except KeyboardInterrupt:
        state.running = False
    finally:
        await db.close()

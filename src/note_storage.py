"""Module which contains database-related tools."""

import datetime
import json
import os
from types import TracebackType
from typing import Dict, List

import asyncpg


class NoteStorage:
    """An asynchronous interface for convenient operations with notes created inside the skill."""

    QUERIES: Dict[str, str] = json.load(open(os.getenv('SQL_QUERIES_PATH')))

    def __init__(self, user_id: str) -> None:
        self.conn: asyncpg.Connection | None = None
        self.user_id: str = user_id

    # These dunder methods are implemented for a custom context manager
    async def __aenter__(self) -> 'NoteStorage':
        # Note that all sensitive info (including username, password etc.) is stored in env and loads automatically
        self.conn = await asyncpg.connect()
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None,
                        exc_val: BaseException | None,
                        exc_tb: TracebackType | None) -> None:
        if self.conn:
            await self.conn.close()

    async def _execute(self, query_id: str, args: tuple | str | datetime.date | None = None) \
            -> List[asyncpg.Record] | None:
        """An inner method which properly executes a query by automatically retrieving its text/passing user_id
        variable"""

        # To make sure only current user's notes are affected, each query must have user_id as its first variable
        query = self.QUERIES[query_id]

        full_args = [self.user_id]

        # Depending on args value, we need to pack these arguments into full_args differently
        if isinstance(args, str):
            full_args.append(args)
        elif isinstance(args, tuple):
            full_args.extend(args)

        return await self.conn.fetch(query, *full_args)

    async def select_notes(self, title: str | None = None, date: datetime.date | None = None) -> List[asyncpg.Record]:
        """Select notes related to a specific user. Returns a list of `Record` with a following form:
        [full_note, short_note, title, date]"""

        if title is None and date is None:
            return await self._execute('select_all_notes')
        elif title is None:
            return await self._execute('select_notes_by_date', date)
        elif date is None:
            return await self._execute('select_notes_by_title', title)

        # If both title and date are provided, only a single note should be retrieved as we cannot have two notes
        # with same titles and dates
        return await self._execute('select_single_note', (title, date))

    async def delete_notes(self, title: str | None = None, date: datetime.date | None = None) -> None:
        """Delete notes related to a specific user. Bear in mind that this is an irreversible action.
        A developer probably should receive user confirmation before going on to delete any information."""

        if title is None and date is None:
            await self._execute('delete_all_notes')
        elif title is None:
            await self._execute('delete_notes_by_date', date)
        elif date is None:
            await self._execute('delete_notes_by_title', title)
        else:
            await self._execute('delete_single_note', (title, date))

    async def insert_new_note(self, title: str, text: str) -> None:
        """Add newly created note to the database."""

        date = datetime.date.today()
        await self._execute("insert_new_note", (title, date, text))

    async def add_short_note_form(self, title: str, date: datetime.date, text: str) -> None:
        """Update existing note entry with its short form."""

        await self._execute('add_short_form', (title, date, text))

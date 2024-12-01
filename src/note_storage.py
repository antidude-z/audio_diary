import asyncpg
import json
import os
from typing import Union

class NoteStorage:
    QUERIES: dict[str, str] = json.load(open(os.getenv('SQL_QUERIES_PATH')))

    def __init__(self, user_id: str) -> None:
        self.conn = None
        self.user_id = user_id

    # These dunder methods are implemented for a custom context manager
    async def __aenter__(self):
        # Note that all sensitive info (including username, password etc.) is stored in env and loads automatically
        self.conn = await asyncpg.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.conn.close()

    async def execute(self, query_id: str, args: Union[tuple, str]=None) -> Union[list, None]:
        # To make sure only current user's notes are affected, each query must have user_id as its first var
        query = self.QUERIES[query_id]

        full_args = [self.user_id]

        # Depending on args value, we need to pack these arguments into full_args differently
        if isinstance(args, str):
            full_args.append(args)
        elif isinstance(args, tuple):
            full_args.extend(args)

        return await self.conn.fetch(query, *full_args)

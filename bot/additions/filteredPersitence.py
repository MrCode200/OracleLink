from telegram.ext import PicklePersistence


class FilteredPersistence(PicklePersistence):
    def __init__(self, blacklist_keys: list[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.blacklist_keys: list[str] = blacklist_keys or []

    async def flush(self) -> None:
        for user_id, data in self.user_data.items():
            for key in self.blacklist_keys:
                data.pop(key, None)
        await super().flush()

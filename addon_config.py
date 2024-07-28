import json

from aqt import mw
import logging
from typing import Dict, Any


class AddonConfig:
    def __init__(self, logger: logging.Logger):
        self.logger: logging.Logger = logger
        self.logger.debug("__init__")
        self.raw: Dict[str, Any] = mw.addonManager.getConfig(__name__)
        self._init_decks_update()

    def _save(self):
        self.logger.debug("_save")
        mw.addonManager.writeConfig(__name__, self.raw)

    def _init_decks_update(self):
        self.logger.debug("_init_decks_update")
        self._add_new_decks_to_add_on_config()
        self._update_decks_in_add_on_config()
        self._remove_old_decks_from_add_on_config()
        self._save()

    def _add_new_decks_to_add_on_config(self):
        if "decks" not in self.raw:
            self.raw["decks"] = {}
        self.logger.debug(self.raw)
        self.logger.debug(mw.col.decks.all_names_and_ids())
        for deck in mw.col.decks.all_names_and_ids():
            d_id = str(deck.id)
            if d_id not in self.raw["decks"]:
                self.raw["decks"][d_id] = {
                    "name": deck.name,
                    "enabled": False,
                    "primary_mode": "note",
                    "secondary_mode": "none"
                }

    def _update_decks_in_add_on_config(self):
        for deck in mw.col.decks.all_names_and_ids():
            d_id = str(deck.id)
            if d_id in self.raw["decks"]:
                if self.raw["decks"][d_id]["name"] != deck.name:
                    self.logger.debug(
                        f"Deck ID: {d_id} has been renamed from '{self.raw['decks'][d_id]['name']}' to '{deck.name}'")
                    self.raw["decks"][d_id]["name"] = deck.name
            else:
                self.logger.warning(f"Deck ID {d_id} not found in the configuration.")

    def _remove_old_decks_from_add_on_config(self):
        anki_deck_ids = [str(deck.id) for deck in mw.col.decks.all_names_and_ids()]
        addon_decks = list(self.raw["decks"].keys())

        for addon_deck_id in addon_decks:
            if addon_deck_id not in anki_deck_ids:
                self.logger.debug(
                    f"Deck: {self.raw['decks'][addon_deck_id]['name']} has been removed from addon config.")
                del self.raw["decks"][addon_deck_id]

    def get_deck_state(self, did: str, key: str):
        self.logger.debug(f"get_deck_state did {did} key {key}")
        if did in self.raw["decks"] and key in self.raw["decks"][did]:
            return self.raw["decks"][did][key]
        else:
            self.logger.error(f"get_deck_state error")
            return None

    def set_deck_state(self, did: str, key: str, value):
        self.logger.debug(f"set_deck_state did {did} key {key} value {value}")
        if did in self.raw["decks"]:
            self.raw["decks"][did][key] = value
            self._save()
        else:
            self.logger.error(f"set_deck_state error")

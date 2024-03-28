import logging
import os
from aqt.reviewer import Reviewer
from anki.cards import Card
from typing import Literal
from aqt import mw
from aqt import gui_hooks
from logging.handlers import RotatingFileHandler
from .manager import Manager

logger = logging.getLogger(__name__)
FORMAT = "%(asctime)s [%(filename)s][%(funcName)s:%(lineno)s][%(levelname)s]: %(message)s"
logFilePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "auto_time_suggestion.log")
file_handler = RotatingFileHandler(logFilePath, maxBytes=10 * 1024 * 1024, backupCount=3)
formatter = logging.Formatter(FORMAT)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)

logger.info("#")
logger.info("################################### ADD-ON STARTED #################################################")
logger.info("#")

add_on_config: dict = {}


def get_all_included_decks_ids(deck_names: dict) -> list:
    filtered_keys = {key: value for key, value in deck_names.items() if value}
    result: list = []
    decks = mw.col.decks.all()
    for deck in decks:
        if deck["name"] in filtered_keys.keys():
            result.append(deck["id"])
    return result


def reviewer_will_init_answer_buttons(buttons_tuple: tuple[bool, Literal[1, 2, 3, 4]], reviewer: Reviewer, card: Card):
    global add_on_config
    included_decks_ids: list = get_all_included_decks_ids(add_on_config["includedDecks"])
    logger.debug(f"included_decks_ids {included_decks_ids}")
    if card.odid not in included_decks_ids:
        logger.debug(f"Not included Deck ID: {card.did}")
        return buttons_tuple

    m1 = Manager(card, add_on_config, logger)
    buttons = m1.get_buttons()
    if buttons is None:
        return buttons_tuple
    else:
        return buttons


def reviewer_did_answer_card(reviewer: Reviewer, card: Card, ease: Literal[1, 2, 3, 4]):
    logger.debug(f"User pressed button: {ease}. Auto button was: {Reviewer._defaultEase}")


def profile_did_open():
    global add_on_config
    add_on_config = mw.addonManager.getConfig(__name__)
    if add_on_config["logging_level"] == "DEBUG":
        logger.setLevel(logging.DEBUG)
        logger.debug(f"Logging has been set to DEBUG level.")
    if add_on_config["logging_level"] == "INFO":
        logger.setLevel(logging.INFO)
        logger.info(f"Logging has been set to INFO level.")
    logger.debug(f"Loaded add-on config from file: {add_on_config}")


gui_hooks.profile_did_open.append(profile_did_open)
gui_hooks.reviewer_will_init_answer_buttons.append(reviewer_will_init_answer_buttons)
gui_hooks.reviewer_did_answer_card.append(reviewer_did_answer_card)

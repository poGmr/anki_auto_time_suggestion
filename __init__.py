import logging
import os
from aqt.reviewer import Reviewer
from anki.cards import Card
from typing import Literal
from aqt import gui_hooks
from aqt import mw
from logging.handlers import RotatingFileHandler
from .manager import Manager
from .addon_config import AddonConfig


def initialize_logger():
    result = logging.getLogger(__name__)
    if not result.handlers:
        log_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "auto_time_suggestion.log")
        file_handler = RotatingFileHandler(log_file_path, maxBytes=10 * 1024 * 1024, backupCount=3)
        log_format = "%(asctime)s [%(levelname)s]: %(message)s"
        formatter = logging.Formatter(log_format)
        file_handler.setFormatter(formatter)
        result.addHandler(file_handler)
        result.setLevel(logging.INFO)
    return result


def _default_ease_1() -> int:
    return 1


def _default_ease_2() -> int:
    return 2


def _default_ease_3() -> int:
    return 3


def _default_ease_4() -> int:
    return 4


CARD_TYPE_MAP = {
    0: "new",
    1: "learning",
    2: "review",
    3: "relearning"
}
CARD_QUEUE_MAP = {
    -3: "suspended",
    -2: "buried",
    -1: "user buried",
    0: "new",
    1: "learning",
    2: "review",
    3: "day learning"
}


def reviewer_will_init_answer_buttons(buttons_tuple: tuple[bool, Literal[1, 2, 3, 4]], reviewer: Reviewer, card: Card):
    global add_on_config
    c_type = card.type
    c_queue = card.queue
    logger.debug(f"[{card.id}] c_type {c_type} c_queue {c_queue} card.did {card.did} card.odid {card.odid}")

    if card.odid == 0:
        did = str(card.did)
    else:
        did = str(card.odid)

    if not add_on_config.get_deck_state(did=did, key="enabled"):
        logger.debug(f"[{card.id}] Deck ID {did} is not included in add-on.")
        reviewer._defaultEase = _default_ease_3
        return buttons_tuple
    primary_mode = add_on_config.get_deck_state(did=did, key="primary_mode")
    secondary_mode = add_on_config.get_deck_state(did=did, key="secondary_mode")
    m1 = Manager(card, primary_mode, secondary_mode, logger)
    decision = m1.get_decision()
    b1 = (1, 'Again')
    b2 = (2, 'Hard')
    b3 = (3, 'Good')
    b4 = (4, 'Easy')
    if decision == 1:
        b1 = (1, "<b><u>AGAIN</u></b>")
        reviewer._defaultEase = _default_ease_1
    if decision == 2:
        b2 = (2, "<b><u>HARD</u></b>")
        reviewer._defaultEase = _default_ease_2
    if decision == 3:
        b3 = (3, "<b><u>GOOD</u></b>")
        reviewer._defaultEase = _default_ease_3
    if decision == 4:
        b4 = (4, "<b><u>EASY</u></b>")
        reviewer._defaultEase = _default_ease_4
    return b1, b2, b3, b4


def reviewer_did_answer_card(reviewer: Reviewer, card: Card, ease: Literal[1, 2, 3, 4]):
    deck = mw.col.decks.get(did=card.did)
    card_type_name = CARD_TYPE_MAP.get(card.type, "unknown")
    card_queue_name = CARD_QUEUE_MAP.get(card.queue, "unknown")
    logger_output = f"[{deck['name']}][{card_type_name}][{card_queue_name}] User pressed button: {ease}."
    logger_output += f" Auto button was: {reviewer._defaultEase()}"
    logger.info(logger_output)


def profile_did_open():
    global add_on_config
    logger.info("#")
    logger.info("################################### ADD-ON STARTED #################################################")
    logger.info("#")
    add_on_config = AddonConfig(logger=logger)


logger = initialize_logger()
add_on_config: AddonConfig
gui_hooks.profile_did_open.append(profile_did_open)
gui_hooks.reviewer_will_init_answer_buttons.append(reviewer_will_init_answer_buttons)
gui_hooks.reviewer_did_answer_card.append(reviewer_did_answer_card)

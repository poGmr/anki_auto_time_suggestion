import logging
import os
from aqt.reviewer import Reviewer
from anki.cards import Card
from typing import Literal
from statistics import quantiles, mean, mode, median
from aqt import mw
from aqt import gui_hooks
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)
FORMAT = "%(asctime)s [%(filename)s][%(funcName)s:%(lineno)s][%(levelname)s]: %(message)s"
logFilePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "auto_time_suggestion.log")
file_handler = RotatingFileHandler(logFilePath, maxBytes=1e6, backupCount=3)
formatter = logging.Formatter(FORMAT)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)

logger.info("#")
logger.info("################################### ADD-ON STARTED #################################################")
logger.info("#")


class Manager:
    def __init__(self, card: Card, add_on_config: dict):
        self.add_on_config = add_on_config
        self.card = card
        self.note = self.card.note()
        self.reviews_times = self.get_reviews_times()
        self.reviews_times = self.clean_up_reviews_times()
        self.low_quantile, self.high_quantile = self.get_quantiles()

    def save_raw_data(self, data, model_id, card_ord):
        filename = f"{model_id}_{card_ord}.txt"
        with open(filename, mode="w", encoding="utf-8") as file:
            for line in data:
                file.write(str(line) + "\n")
        logger.debug(f"Saved data to file {filename}")

    def get_reviews_times(self):
        card_ord = self.card.ord  # 0,1,2 Type of cards, EN->PL, PL->EN, EN->Write, etc,
        model_id = self.note.note_type()["id"]  # Words, Grammar, Spelling, etc.
        logger.debug(f"Card ID: {self.card.id}, Note type model id: {model_id}, Card type ID: {card_ord}")
        query = f"""
                SELECT revlog.time
                FROM revlog
                JOIN cards ON revlog.cid=cards.id
                JOIN notes ON cards.nid=notes.id
                WHERE notes.mid='{model_id}' AND cards.ord='{card_ord}' AND
                revlog.ease!='1' AND
                revlog.type='1'
                """
        result = mw.col.db.list(query)
        if add_on_config["dump_data"]:
            self.save_raw_data(result, model_id, card_ord)
        return result

    def clean_up_reviews_times(self):
        reviews_times = self.reviews_times.copy()
        reviews_times_n = len(reviews_times)
        if reviews_times_n < 20:
            logger.debug(f"reviews_times has too few elements: {reviews_times_n}")
            return
        debug_output = "Before clean up: "
        debug_output += f"n {reviews_times_n} "
        debug_output += f"min {min(reviews_times)} "
        debug_output += f"mean {round(mean(reviews_times))} "
        debug_output += f"mode {mode(reviews_times)} "
        debug_output += f"median {round(median(reviews_times))} "
        debug_output += f"max {max(reviews_times)}"
        logger.debug(debug_output)
        first_5_per = int(0.05 * reviews_times_n)
        last_5_per = int(0.95 * reviews_times_n)
        reviews_times.sort()
        reviews_times = reviews_times[first_5_per:last_5_per]
        reviews_times_n = len(reviews_times)
        debug_output = "After clean up:  "
        debug_output += f"n {reviews_times_n} "
        debug_output += f"min {min(reviews_times)} "
        debug_output += f"mean {round(mean(reviews_times))} "
        debug_output += f"mode {mode(reviews_times)} "
        debug_output += f"median {round(median(reviews_times))} "
        debug_output += f"max {max(reviews_times)}"
        logger.debug(debug_output)
        return reviews_times

    def get_quantiles(self):
        reviews_times_n = len(self.reviews_times)
        if reviews_times_n < 4:
            logger.debug(f"reviews_times has too few elements: {reviews_times_n}")
            return
        quantiles_times = [round(q) for q in quantiles(self.reviews_times, n=4)]
        low_quantile = quantiles_times[0]
        high_quantile = quantiles_times[2]
        logger.debug(
            f"quantiles_times: {quantiles_times}, low_quantile: {low_quantile}, high_quantile: {high_quantile}")
        return low_quantile, high_quantile

    def _defaultEase_1(self) -> int:
        return 1

    def _defaultEase_2(self) -> int:
        return 2

    def _defaultEase_3(self) -> int:
        return 3

    def _defaultEase_4(self) -> int:
        return 4

    def get_buttons(self):
        again_b = (1, 'Again')
        hard_b = (2, 'Hard')
        good_b = (3, 'Good')
        easy_b = (4, 'Easy')
        reviews_times_n = len(self.reviews_times)
        if reviews_times_n < 100:
            logger.debug(f"reviews_times has too few elements: {reviews_times_n}")
            return again_b, hard_b, good_b, easy_b
        c_time_taken = int(self.card.time_taken())
        c_type = self.card.type
        c_queue = self.card.queue
        logger.debug(f"Card time taken: {c_time_taken}, card type: {c_type}, card queue: {c_queue}")
        if c_type in (0, 2) and c_queue in (0, 2):
            if c_time_taken > self.high_quantile:
                hard_b = (2, "<b><u>HARD</u></b>")
                Reviewer._defaultEase = self._defaultEase_2
            if self.low_quantile <= c_time_taken <= self.high_quantile:
                good_b = (3, "<b><u>GOOD</u></b>")
                Reviewer._defaultEase = self._defaultEase_3
            if c_time_taken < self.low_quantile:
                easy_b = (4, "<b><u>EASY</u></b>")
                Reviewer._defaultEase = self._defaultEase_4

        if c_type in (1, 3) and c_queue in (1, 3):
            if c_time_taken > self.high_quantile:
                again_b = (1, "<b><u>AGAIN</u></b>")
                Reviewer._defaultEase = self._defaultEase_1
            if c_time_taken <= self.high_quantile:
                good_b = (3, "<b><u>GOOD</u></b>")
                Reviewer._defaultEase = self._defaultEase_3

        return again_b, hard_b, good_b, easy_b


add_on_config: dict = {}


def reviewer_will_init_answer_buttons(buttons_tuple: tuple[bool, Literal[1, 2, 3, 4]], reviewer: Reviewer, card: Card):
    manager = Manager(card=card, add_on_config=add_on_config)
    buttons = manager.get_buttons()
    return buttons


def reviewer_did_answer_card(reviewer: Reviewer, card: Card, ease: Literal[1, 2, 3, 4]):
    logger.debug(f"User pressed button: {ease}. Auto button was: {Reviewer._defaultEase()}")


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

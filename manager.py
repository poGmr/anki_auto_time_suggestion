from statistics import quantiles, mean, mode, median
from anki.cards import Card
from aqt import mw
import logging


class Manager:
    def __init__(self, card: Card, primary_mode, secondary_mode: str, logger: logging.Logger):
        self.logger: logging.Logger = logger
        self.card = card
        self.note = self.card.note()
        self.primary_mode = primary_mode
        self.secondary_mode = secondary_mode
        self.current_mode = primary_mode
        # self.get_card_review_times()
        # self.notes_review_times = self.get_notes_review_times()
        # self.notes_review_times = self.clean_up_notes_review_times()
        # self.low_quantile, self.high_quantile = self.get_quantiles()

    def get_review_times(self):
        card_ord = self.card.ord  # 0,1,2 Type of cards, EN->PL, PL->EN, EN->Write, etc,
        model_id = self.note.note_type()["id"]  # Words, Grammar, Spelling, etc.
        self.logger.debug(
            f"[{self.card.id}] Card ID: {self.card.id}, Note type model id: {model_id}, Card type ID: {card_ord}, Selected mode: {self.current_mode}")
        if self.current_mode == "card":
            query = f"""
                    SELECT revlog.time
                    FROM revlog
                    JOIN cards ON revlog.cid=cards.id
                    JOIN notes ON cards.nid=notes.id
                    WHERE notes.mid='{model_id}' AND
                    cards.ord='{card_ord}' AND
                    revlog.ease>'0' AND
                    revlog.type='1' AND
                    revlog.cid='{self.card.id}'
                    """
        if self.current_mode == "note":
            query = f"""
                    SELECT revlog.time
                    FROM revlog
                    JOIN cards ON revlog.cid=cards.id
                    JOIN notes ON cards.nid=notes.id
                    WHERE notes.mid='{model_id}' AND
                    cards.ord='{card_ord}' AND
                    revlog.ease>'0' AND
                    revlog.type='1'
                    """
        if self.current_mode == "none":
            return []
        result = sorted(mw.col.db.list(query))
        if result is None:
            return []
        return result

    def clean_up_review_times(self, review_times):
        review_times_n = len(review_times)
        debug_output = f"[{self.card.id}] Before clean up: "
        debug_output += f"n {review_times_n} "
        debug_output += f"min {min(review_times)} "
        debug_output += f"mean {round(mean(review_times))} "
        debug_output += f"mode {mode(review_times)} "
        debug_output += f"median {round(median(review_times))} "
        debug_output += f"max {max(review_times)}"
        self.logger.debug(debug_output)
        first_5_per = int(0.05 * review_times_n)
        last_5_per = int(0.95 * review_times_n)
        review_times.sort()
        reviews_times = review_times[first_5_per:last_5_per]
        reviews_times_n = len(reviews_times)
        debug_output = f"[{self.card.id}] After clean up:  "
        debug_output += f"n {reviews_times_n} "
        debug_output += f"min {min(reviews_times)} "
        debug_output += f"mean {round(mean(reviews_times))} "
        debug_output += f"mode {mode(reviews_times)} "
        debug_output += f"median {round(median(reviews_times))} "
        debug_output += f"max {max(reviews_times)}"
        self.logger.debug(debug_output)
        return reviews_times

    def get_quantiles(self, reviews_times):
        reviews_times_n = len(reviews_times)
        quantiles_times = [round(q) for q in quantiles(reviews_times, n=4)]
        low_quantile = quantiles_times[0]
        high_quantile = quantiles_times[2]
        self.logger.debug(
            f"[{self.card.id}] quantiles_times: {quantiles_times}, low_quantile: {low_quantile}, high_quantile: {high_quantile}")
        return low_quantile, high_quantile

    def get_decision(self) -> int:
        reviews_times = self.get_review_times()
        if len(reviews_times) < 20:
            self.logger.debug(
                f"[{self.card.id}] Not enough cards' reviews: {len(reviews_times)} - switching to '{self.secondary_mode}' mode")
            self.current_mode = self.secondary_mode
            reviews_times = self.get_review_times()
        if self.current_mode == "none":
            return 3
        c_time_taken = int(self.card.time_taken())
        c_type = self.card.type
        c_queue = self.card.queue
        self.logger.debug(
            f"[{self.card.id}] Card time taken: {c_time_taken}, card type: {c_type}, card queue: {c_queue}")
        reviews_times = self.clean_up_review_times(reviews_times)
        low_quantile, high_quantile = self.get_quantiles(reviews_times)
        if c_type in (0, 2) and c_queue in (0, 2, 4):
            if c_time_taken > high_quantile:
                self.logger.debug(f"[{self.card.id}] Decision taken: 2")
                return 2
            if low_quantile <= c_time_taken <= high_quantile:
                self.logger.debug(f"[{self.card.id}] Decision taken: 3")
                return 3
            if c_time_taken < low_quantile:
                self.logger.debug(f"[{self.card.id}] Decision taken: 4")
                return 4

        if c_type in (1, 3) and c_queue in (1, 3):
            if c_time_taken > high_quantile:
                self.logger.debug(f"[{self.card.id}] Decision taken: 1")
                return 1
            if c_time_taken <= high_quantile:
                self.logger.debug(f"[{self.card.id}] Decision taken: 3")
                return 3

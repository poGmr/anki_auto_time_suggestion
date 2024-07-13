from statistics import quantiles, mean, mode, median
from anki.cards import Card
from aqt import mw


class Manager:
    def __init__(self, card: Card, logger):
        self.logger = logger
        self.card = card
        self.note = self.card.note()
        self.get_card_review_times()
        self.notes_review_times = self.get_notes_review_times()
        self.notes_review_times = self.clean_up_notes_review_times()
        self.low_quantile, self.high_quantile = self.get_quantiles()

    def get_notes_review_times(self):
        card_ord = self.card.ord  # 0,1,2 Type of cards, EN->PL, PL->EN, EN->Write, etc,
        model_id = self.note.note_type()["id"]  # Words, Grammar, Spelling, etc.
        self.logger.debug(f"Card ID: {self.card.id}, Note type model id: {model_id}, Card type ID: {card_ord}")
        query = f"""
                SELECT revlog.time
                FROM revlog
                JOIN cards ON revlog.cid=cards.id
                JOIN notes ON cards.nid=notes.id
                WHERE notes.mid='{model_id}' AND cards.ord='{card_ord}' AND
                revlog.ease>'0' AND
                revlog.type='1'
                """
        result = mw.col.db.list(query)
        if result is None:
            return []
        return result

    def get_card_review_times(self):
        card_ord = self.card.ord  # 0,1,2 Type of cards, EN->PL, PL->EN, EN->Write, etc,
        model_id = self.note.note_type()["id"]  # Words, Grammar, Spelling, etc.
        self.logger.debug(f"Card ID: {self.card.id}, Note type model id: {model_id}, Card type ID: {card_ord}")
        query = f"""
                SELECT revlog.time
                FROM revlog
                JOIN cards ON revlog.cid=cards.id
                JOIN notes ON cards.nid=notes.id
                WHERE notes.mid='{model_id}' AND
                cards.ord='{card_ord}' AND
                revlog.cid='{self.card.id}' AND
                revlog.ease>'0' AND
                revlog.type='1'
                """
        result = sorted(mw.col.db.list(query))
        self.logger.debug(f"Card ID times: {result}")
        debug_output = "Card stats:  "
        debug_output += f"n {len(result)} "
        debug_output += f"min {min(result)} "
        debug_output += f"mean {round(mean(result))} "
        debug_output += f"mode {mode(result)} "
        debug_output += f"median {round(median(result))} "
        debug_output += f"max {max(result)}"
        self.logger.debug(debug_output)
        if result is None:
            return []
        return result

    def clean_up_notes_review_times(self):
        notes_review_times = self.notes_review_times.copy()
        notes_review_times_n = len(notes_review_times)
        if notes_review_times_n < 20:
            self.logger.debug(f"reviews_times has too few elements: {notes_review_times_n}")
            return []
        debug_output = "Before clean up: "
        debug_output += f"n {notes_review_times_n} "
        debug_output += f"min {min(notes_review_times)} "
        debug_output += f"mean {round(mean(notes_review_times))} "
        debug_output += f"mode {mode(notes_review_times)} "
        debug_output += f"median {round(median(notes_review_times))} "
        debug_output += f"max {max(notes_review_times)}"
        self.logger.debug(debug_output)
        first_5_per = int(0.05 * notes_review_times_n)
        last_5_per = int(0.95 * notes_review_times_n)
        notes_review_times.sort()
        reviews_times = notes_review_times[first_5_per:last_5_per]
        reviews_times_n = len(reviews_times)
        debug_output = "After clean up:  "
        debug_output += f"n {reviews_times_n} "
        debug_output += f"min {min(reviews_times)} "
        debug_output += f"mean {round(mean(reviews_times))} "
        debug_output += f"mode {mode(reviews_times)} "
        debug_output += f"median {round(median(reviews_times))} "
        debug_output += f"max {max(reviews_times)}"
        self.logger.debug(debug_output)
        return reviews_times

    def get_quantiles(self):
        notes_review_times_n = len(self.notes_review_times)
        if notes_review_times_n < 4:
            self.logger.debug(f"reviews_times has too few elements: {notes_review_times_n}")
            return None, None
        quantiles_times = [round(q) for q in quantiles(self.notes_review_times, n=4)]
        low_quantile = quantiles_times[0]
        high_quantile = quantiles_times[2]
        self.logger.debug(
            f"quantiles_times: {quantiles_times}, low_quantile: {low_quantile}, high_quantile: {high_quantile}")
        return low_quantile, high_quantile

    def get_decision(self, mode: str) -> int:
        reviews_times_n = len(self.notes_review_times)
        if reviews_times_n < 100:
            self.logger.debug(f"reviews_times has too few elements: {reviews_times_n}")
            return 3
        c_time_taken = int(self.card.time_taken())
        c_type = self.card.type
        c_queue = self.card.queue
        self.logger.debug(f"Card time taken: {c_time_taken}, card type: {c_type}, card queue: {c_queue}")
        if c_type in (0, 2) and c_queue in (0, 2, 4):
            if c_time_taken > self.high_quantile:
                return 2
            if self.low_quantile <= c_time_taken <= self.high_quantile:
                return 3
            if c_time_taken < self.low_quantile:
                return 4

        if c_type in (1, 3) and c_queue in (1, 3):
            if c_time_taken > self.high_quantile:
                return 1
            if c_time_taken <= self.high_quantile:
                return 3

import random
from typing import List, Optional

from opustrainer.modifiers import Modifier
from opustrainer.modifiers.placeholders import get_random_unicode_words


class NoiseModifier(Modifier):
    """Adds noise during training. Nonsensitcal string on the source and on the target

       Usage:
       ```yaml
       modifiers:
       - Noise: 0.01
         min_words: 2
         max_words: 5
         max_word_length: 4
        ```
    """
    min_word_length: int
    max_word_length: int
    max_words: int

    def __init__(self, probability: float=0.0, min_word_legnth: int=2,
        max_word_length: int=5, max_words: int=4):
        super().__init__(probability)
        self.min_word_length = min_word_legnth
        self.max_word_length = max_word_length
        self.max_words = max_words

    def __call__(self, line: str) -> Optional[str]:
        """Generates a random noise line"""
        if self.probability < random.random():
            random_words: List[str] = get_random_unicode_words(self.min_word_length, self.max_word_length, self.max_words)
            newline: str = " ".join(random_words)
            # Check if we have a 3rd field, which we assume is alignment
            if line.count('\t') == 2:
                # Generate alignments, in case
                alignments: str = " ".join(f"{i}-{i}" for i, _ in enumerate(random_words))
                line = line + "\n" + newline + "\t" + newline + "\t" + alignments
            else:
                line = line + "\n" + newline + "\t" + newline
        return line

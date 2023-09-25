import random
import re
from typing import Dict, Literal, Tuple

import typo
from opustrainer.modifiers import Modifier


def add_random_space_with_alignment(
    string: str, alignment_str: str, include_edges=False
) -> Tuple[str, str]:
    """Add a space to a random point in the string"""
    possible_insertions = [m.start() for m in re.finditer(r"\S", string)]

    if include_edges:
        possible_insertions += [len(string)]  # also at end
    else:
        possible_insertions = possible_insertions[1:]  # not at beginning

    if not possible_insertions:
        return string, alignment_str

    index = random.choice(possible_insertions)
    augmented_string = string[:index] + " " + string[index:]

    # Find positions of space-like segments that would not cause de-alignment
    space_spans = list(re.finditer(r"^\s*|\s+|$", string[: index + 1]))
    keep_alignment_indices = [m.end() for m in space_spans]
    word_index = len(keep_alignment_indices) - 2

    augmented_alignment_str = alignment_str
    if index not in keep_alignment_indices:
        assert len(augmented_string.split()) - len(string.split()) == 1
        augmented_alignment = []

        for align in alignment_str.split():
            src, trg = [int(index) for index in align.split("-", maxsplit=1)]
            if src <= word_index:
                augmented_alignment.append(f"{src}-{trg}")
            if src >= word_index:
                # src += 1
                augmented_alignment.append(f"{src+1}-{trg}")

        augmented_alignment_str = " ".join(augmented_alignment)
    return augmented_string, augmented_alignment_str


def skip_random_space_with_alignment(
    string: str, alignment_str: str, include_edges=False
) -> Tuple[str, str]:
    possible_removals = re.finditer(r"(?<!^)\s(?!$)", string)

    if include_edges:
        possible_removals = re.finditer(r"\s", string)

    possible_removals = [m.start() for m in possible_removals]

    if not possible_removals:
        return string, alignment_str

    index = random.choice(possible_removals)
    augmented_string = string[:index] + string[index + 1 :]

    word_spans = list(re.finditer(r"(?<=\S)\s\S", string))
    word_index = None
    for i, match in enumerate(word_spans):
        if index == match.start():
            word_index = i
            break

    augmented_alignment_str = alignment_str
    if word_index is not None:
        augmented_alignment = []
        for align in alignment_str.split():
            src, trg = [int(index) for index in align.split("-", maxsplit=1)]
            if src <= word_index:
                augmented_alignment.append(f"{src}-{trg}")
            else:
                augmented_alignment.append(f"{src-1}-{trg}")
        augmented_alignment_str = " ".join(augmented_alignment)

    return augmented_string, augmented_alignment_str


def missing_char_with_alignment(string: str, alignment_str: str):
    possible_removals = [m.start() for m in re.finditer(r"\S", string)]

    # Do not remove only possible char
    if len(possible_removals) <= 1:
        return string, alignment_str

    index = random.choice(possible_removals)
    augmented_string = string[:index] + string[index + 1 :]

    word_spans = list(re.finditer(r"\S+", string))

    # Find word_index if a single-char word was removed
    word_index = None
    for i, match in enumerate(word_spans):
        start, end = match.span()
        if index > end:
            continue
        if start <= index:
            if end - start == 1:
                word_index = i
            break

    augmented_alignment_string = alignment_str
    if word_index is not None:
        augmented_alignment = []
        # Reassign alignment to a random-neighbour
        neighbours = []
        if word_index != 0:
            neighbours.append(-1)
        if word_index != len(word_spans):
            neighbours.append(0)
        r = random.choice(neighbours)

        for align in alignment_str.split():
            src, trg = [int(index) for index in align.split("-", maxsplit=1)]
            if src == word_index:
                augmented_alignment.append(f"{src+r}-{trg}")
            else:
                offset = 0 if src < word_index else -1
                augmented_alignment.append(f"{src+offset}-{trg}")
        augmented_alignment_string = " ".join(augmented_alignment)

    return augmented_string, augmented_alignment_string


def random_space_with_alignment(
    action: Literal["random_space", "skipped_space"], strval: str, alignments: str
) -> Tuple[str, str]:
    """Special version of typo's random_space and skipped_space that also
    updates alignment info.

    action: add | remove
      whether to add or remove a random space

    strval: str
      input text

    alignments: str
      string of space split m-n pairs

    """
    print(strval, alignments)
    # all the locations where there are non-space characters.

    locations = [m.start() for m in re.finditer(r"\S", strval)]
    # print(locations)

    if len(locations) == 0:
        return strval, alignments

    # Select character after which to add a space
    char_index = locations[random.randint(0, len(locations) - 1)]
    print(f"Char_index: {char_index}; {strval[char_index]}")

    # Figure out which word that character falls in
    word_index = sum(1 for _ in re.finditer(r"\s+", strval[:char_index]))

    print(f"Word_index: {word_index}")

    # Insert space
    if action == "random_space":
        strval = strval[:char_index] + " " + strval[char_index:]
    else:
        strval = strval[: char_index - 1] + strval[char_index:]

    # Fix up alignments
    fixed_alignments = []
    for alignment in alignments.split(" "):
        # Splits the a-b pairs into tuples
        src, trg = [int(index) for index in alignment.split("-", maxsplit=1)]

        # Alignments before the introduced space stay as-is. Intentionally, if
        # the mapping is about word_index itself, we apply both to duplicate
        # the mapping.
        if src <= word_index:
            fixed_alignments.append(f"{src}-{trg}")

        # Alignments after the space are shifted by 1
        if (
            action == "random_space"
            and src >= word_index
            or action == "skipped_space"
            and src > word_index
        ):
            src += 1 if action == "random_space" else -1
            fixed_alignments.append(f"{src}-{trg}")

    return strval, " ".join(fixed_alignments)


class TypoModifier(Modifier):
    # modifier name, and probability it is applied on a considered
    # sentence. Each modifier can either be applied once or not at all
    # for a considered sentence. The default probability for each is 10%.
    modifiers = {
        "char_swap": 0.1,
        "missing_char": 0.1,
        "extra_char": 0.1,
        "nearby_char": 0.1,
        "similar_char": 0.1,
        "skipped_space": 0.1,
        "random_space": 0.1,
        "repeated_char": 0.1,
        "unichar": 0.1,
    }

    column: int

    probabilities: Dict[str, float]

    def __init__(self, probability: float, **probabilities: float):
        """
        Apply typo modifiers to the input. If no specific typo modifiers are
        mentioned, it will default to applying them all with a 0.1 probability
        each. If modifiers are mentioned in the configuration, only the
        modifiers mentioned will be used. All probabilities have to be in the
        0.0 .. 1.0 range.

        args:
            probability: float
                probability a line will be modified

            char_swap: float
                Swaps two random consecutive word characters in the string.

            missing_char: float
                Skips a random word character in the string.

            extra_char: float
                Adds an extra, keyboard-neighbor, letter next to a random word character.

            nearby_char: float
                Replaces a random word character with keyboard-neighbor letter.

            similar_char: float
                Replaces a random word character with another visually similar character.

            skipped_space: float
                Skips a random space from the string.

            random_space: float
                Adds a random space in the string.

            repeated_char: float
                Repeats a random word character.

            unichar: float
                Replaces a random consecutive repeated letter with a single letter.
        """
        super().__init__(probability)

        for mod, mod_prob in probabilities.items():
            if mod not in self.modifiers:
                raise ValueError(f"Unknown typo modifier: {mod}")
            if mod_prob < 0.0 or mod_prob > 1.0:
                raise ValueError(
                    f"Typo modifier {mod} has a probability out of the 0.0..1.0 range"
                )

        self.probabilities = probabilities or self.modifiers

    def __call__(self, line: str) -> str:
        fields = line.split("\t")

        # TODO: The StrErrer constructor calls random.seed(None), which isn't
        # great for reproducibility. Not sure whether getrandbits() is a good
        # workaround though.
        data = typo.StrErrer(fields[0], seed=random.getrandbits(32))

        has_alignment_info = len(fields) > 2

        for modifier, probability in self.probabilities.items():
            if probability > random.random():
                # Introducing spaces with alignment information is a problem.
                if has_alignment_info and modifier in (
                    "random_space",
                    "skipped_space",
                    "missing_char",
                ):
                    # import sys
                    # print(modifier, file=sys.stderr)
                    if modifier == "random_space":
                        func = add_random_space_with_alignment
                    elif modifier == "skipped_space":
                        func = skip_random_space_with_alignment
                    elif modifier == "missing_char":
                        func = missing_char_with_alignment

                    # import sys
                    # print(modifier, fields[0],fields[1], fields[2], file=sys.stderr)
                    data.result, fields[2] = func(data.result, fields[2])
                    # data.result, fields[2] = random_space_with_alignment(modifier, data.result, fields[2])
                    # print(modifier,data.result,fields[1], fields[2], data.result.split(), file=sys.stderr)
                else:
                    wordcount = len(data.result.split())
                    getattr(data, modifier)()
                    assert (
                        len(data.result.split()) == wordcount
                        or not has_alignment_info
                    ), f"Modifier {modifier} changed the word count ({wordcount} -> {len(data.result.split(' '))}) while alignment info was not updated\n{fields[0]}\n{data.result}"

        fields[0] = data.result

        return "\t".join(fields)

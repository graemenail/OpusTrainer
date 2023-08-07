import random
import unittest
import tempfile

from textwrap import dedent

from opustrainer.modifiers.placeholders import PlaceholderTagModifier
from opustrainer.trainer import CurriculumLoader
from opustrainer import logger


class TestTagger(unittest.TestCase):
  def setUp(self):
    random.seed(1)

  def test_tagger_tagging(self):
    """Default mode is tagging, and will hint the target word in the source input"""
    tagger = PlaceholderTagModifier(probability=1)
    tagger.print_alignments = True
    output = tagger('Hello world\tHallo Welt\t0-0 1-1')
    self.assertEqual(output, '__source__ Hello __target__ Hallo __done__ __source__ world __target__ Welt __done__\tHallo Welt\t1-0 3-0 6-1 8-1')
    #                         ^0         ^1    ^2         ^3    ^4       ^5         ^6    ^7         ^8   ^9        ^0    ^1

  def test_tagger_replace(self):
    """Replace mode is the same as tagging mode, except that the target word
    will be random noise, teaching the model to just copy it as is."""
    tagger = PlaceholderTagModifier(probability=0.25, replace=1)
    tagger.print_alignments = True
    output = tagger('Hello world\tHallo Welt\t0-0 1-1')
    self.assertEqual(output, '''__source__ Hello __target__ িৡহ __done__ world\tিৡহ Welt\t1-0 3-0 5-1''')
    #                           ^0         ^1    ^2         ^3   ^4       ^5      ^0   ^1

  def test_tagger_augment(self):
    """Augment mode will add random noise without tags to both source and target
    sentence, teaching the model to copy strings it doesn't understand."""
    tagger = PlaceholderTagModifier(probability=1, augment=1)
    tagger.print_alignments = True
    output = tagger('Hello world\tHallo Welt\t0-0 1-1')
    self.assertEqual(output, '''Hello িৡহ world ЇӤӕѣѮ қӃӄЀҲ\tHallo িৡহ Welt ЇӤӕѣѮ қӃӄЀҲ\t0-0 1-1 2-2 3-3 4-4''')

  def test_retokenize(self):
    """Pass the spm vocab to the placeholder tag generator so that it can
    retokenize the input, and update the alignments accordingly."""
    tagger = PlaceholderTagModifier(
      probability=0.25,
      custom_detok_src='en',
      custom_detok_trg='zh',
      spm_vocab='contrib/test-data/vocab.zhen.spm')
    
    output = tagger('\t'.join([
      'This is a simple test statement 🤣 .',
      #^0   ^1 ^2 ^3    ^4   ^5        ^6 ^7
      '这 是 一个 简单 的 测试 语 句 🤣 。',
      #^0 ^1 ^2  ^3   ^4 ^5   ^6 ^7 ^8 ^9
      '0-0 1-1 2-2 3-3 3-4 4-5 5-6 5-7 6-8 7-9',
    ]))
    self.assertEqual(output.split('\t'), [
      '__source__ This __target__ 这 __done__ is a simple test statement 🤣.',
      # [][__source__][This][ ][__target__][这][ ][__done__][ is][ a][ simple][ test][ statement][ ] []  []  []  [🤣][.]
      #^0 ^1          ^2    ^3 ^4          ^5  ^6 ^7        ^8   ^9  ^10       ^11    ^12         ^13 ^14 ^15 ^16 ^17 ^18 
      # Note the empty [] tokens before the special tokens: these are the spaces
      # that are not part of the special marker tokens. It depends on how the
      # spm vocab is trained.
      '这是一个简单的测试语句 🤣 。',
      #[这][是][一][个][简][单][的][测][试][语][句] [ ] []  []  []  [🤣][ 。]
      #^0  ^1  ^2  ^3 ^4  ^5  ^6  ^7  ^8  ^9  ^10 ^11 ^12 ^13 ^14 ^15  ^16
      '2-0 5-0 8-1 9-2 9-3 10-4 10-5 10-6 11-7 11-8 12-9 12-10 17-15 18-16',
      # 0-0 [This]      [这]    2-0
      #     [这]        [这]    5-0
      # 1-1 [is]        [是]    8-1
      # 2-2 [a]         [一个]  9-2 9-3
      # 3-3 [simple]    [简单]  10-4 10-5
      # 3-4 [simple]    [的]    10-6
      # 4-5 [test]      [测试]  11-7 11-8
      # 5-6 [statement] [语]    12-9
      # 5-7 [statement] [句]    12-10 (13-11)
      # 6-8 [🤣]        [🤣]   (14-12 15-13 16-14) 17-15
      # 7-9 [.]         [。]    18-16
    ])

  def test_retokenize_on_non_trigger(self):
    """Pass the spm vocab to the placeholder tag generator so that it can
    retokenize the input, even if probability is 0."""
    tagger = PlaceholderTagModifier(
      probability=0.0,
      custom_detok_src='en',
      custom_detok_trg='zh',
      spm_vocab='contrib/test-data/vocab.zhen.spm')
    
    output = tagger('\t'.join([
      'This is a simple test statement 🤣 .',
      '这 是 一个 简单 的 测试 语 句 🤣 。',
      '0-0 1-1 2-2 3-3 3-4 4-5 5-6 5-7 6-8 7-9',
    ]))
    self.assertEqual(output.split('\t'), [
      'This is a simple test statement 🤣.',
      #[This][ is][ a][ simple][ test][ statement][ ] [] [] [] [🤣][.]
      #^0    ^1   ^2  ^3       ^4     ^5          ^6  ^7 ^8 ^9 ^10 ^11 
      '这是一个简单的测试语句 🤣 。',
      #[这][是][一][个][简][单][的][测][试][语][句] [ ] []  []  []  [🤣][ 。]
      #^0  ^1  ^2  ^3 ^4  ^5  ^6  ^7  ^8  ^9  ^10 ^11 ^12 ^13 ^14 ^15  ^16
      '0-0 1-1 2-2 2-3 3-4 3-5 3-6 4-7 4-8 5-9 5-10 10-15 11-16',
    ])

  def test_tagger_zh_src(self):
    '''Tests the tagger with zh on the source side'''
    tagger = PlaceholderTagModifier(probability=0.6, custom_detok_src='zh')
    with open('contrib/test-data/clean.zhen.10', 'r', encoding='utf-8') as myinput, \
         open('contrib/test-data/clean.zhen.ref.06.4.src', 'r', encoding='utf-8') as reference:
        for line in myinput:
          test = tagger(line)
          ref = reference.readline()[:-1]
          self.assertEqual(test, ref)
  
  def test_tagger_zh_trg(self):
    '''Tests the tagger with zh on the target side'''
    tagger = PlaceholderTagModifier(probability=0.6, custom_detok_src=None, custom_detok_trg='zh')
    with open('contrib/test-data/clean.enzh.10', 'r', encoding='utf-8') as myinput, \
         open('contrib/test-data/clean.enzh.ref.06.4.trg', 'r', encoding='utf-8') as reference:
        for line in myinput:
          test = tagger(line)
          ref = reference.readline()[:-1]
          self.assertEqual(test, ref)

  def test_tagger_no_zh(self):
    '''Tests the tagger without zh detokenizer'''
    tagger = PlaceholderTagModifier(probability=0.6)
    with open('contrib/test-data/clean.enzh.10', 'r', encoding='utf-8') as myinput, \
         open('contrib/test-data/clean.enzh.ref.06.4.none', 'r', encoding='utf-8') as reference:
        for line in myinput:
          test = tagger(line)
          ref = reference.readline()[:-1]
          self.assertEqual(test, ref)

  def test_tagger_zh_src_augment_replace(self):
    '''Tests the tagger with zh on the source side'''
    tagger = PlaceholderTagModifier(probability=0.6, custom_detok_src='zh', custom_detok_trg=None,
                                     augment=0.4, replace=0.4)
    with open('contrib/test-data/clean.zhen.10', 'r', encoding='utf-8') as myinput, \
         open('contrib/test-data/clean.zhen.ref.06.4.04.04.src', 'r', encoding='utf-8') as reference:
        for line in myinput:
          test = tagger(line)
          ref = reference.readline()[:-1]
          self.assertEqual(test, ref)

  def test_warn_if_tag_modifier_is_not_last(self):
    with self.assertLogs(level='WARNING') as logger_ctx:
      loader = CurriculumLoader()
      loader.load(dedent("""
        datasets: {}
        stages: []
        seed: 1
        modifiers:
          - Tags: 1.0
          - UpperCase: 1.0
      """))
    self.assertRegex(logger_ctx.output[0], r"Tags modifier should to be the last modifier to be applied")

  def test_warn_if_alignment_is_missing(self):
    tagger = PlaceholderTagModifier()
    with self.assertLogs(logger, level='WARNING') as logger_ctx:
      self.assertEqual(
        tagger('Hello world\tHallo welt\t'),
        'Hello world\tHallo welt')
    self.assertRegex(logger_ctx.output[0], r'empty alignment field')

  def test_warn_if_alignment_is_missing(self):
    tagger = PlaceholderTagModifier()
    with self.assertLogs(level='WARNING') as logger_ctx:
      self.assertEqual(
        tagger('Hello world\tHallo welt\t0-0 1-2'),
        'Hello world\tHallo welt')
    self.assertRegex(logger_ctx.output[0], r'invalid alignments')


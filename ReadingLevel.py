'''

Tools for interpreting the reading level of a chunk of text.

Created on Feb 20, 2011

@author: Everett Wetchler (evee746)
'''

import gflags
FLAGS = gflags.FLAGS
gflags.DEFINE_string('syllable_dict', 'cmudict.0.7a.txt',
                     'Path to the cmu syllable dictionary file.')

class SyllableDict(object):
  def __init__(self, filename=FLAGS.syllable_dict):
    lines = open(filename).read().splitlines()
    self.word_to_syllables = {}
    for line in lines:
      parts = line.split()
      if len(parts) < 2: continue
      word = parts[0].lower()
      if not (word[0] and word[0].isalpha() and word[-1].isalpha()):
        # Ignore punctuation-ey and other malformatted words
        continue
      if '(' in word:
        # Some alternative pronunciations of FOO are followed by a
        # line that has FOO(1) -- we can just ignore these
        continue
      # Drop hyphens, apostrophes, etc. The same will happen when we
      # process profiles.
      word = "".join([x for x in word if x.isalpha()])
      if not word:
        continue
      syllables = sum(1 for x in parts[1:] if x[-1:].isdigit())
      self.word_to_syllables[word] = syllables
    counts = {}
    for word,syllables in self.word_to_syllables.iteritems():
      counts.setdefault(len(word),[]).append(syllables)
    self.word_length_to_estimated_syllables = {}
    for k,v in counts.iteritems():
      # This is for unknown words, so we can estimate based on the average
      # number of syllables for words of the same length. However,
      # if a word's not in the dictionary, it's probably a proper noun or
      # something goofy, so we don't want to give them credit for using too
      # fancy of a word. Pick an arbitrary modest cap, e.g. 3 syllables.
      self.word_length_to_estimated_syllables[k] = int(
          round(min(3, sum(v)*1.0/len(v))))
    print "Read syllable dictionary of %d words" % len(self.word_to_syllables)
    print self.word_length_to_estimated_syllables
  def __getitem__(self, word):
    word = word.lower()
    if not word: return 0
    return self.word_to_syllables.get(word,
        self.word_length_to_estimated_syllables.get(len(word), 3))
  def d(self):
    return self.word_to_syllables

_SYLLABLE_DICT = SyllableDict()

def _CleanWord(word):
  "Drops all non-alphabetical characters from a word."
  return "".join([x for x in word.lower() if x.isalpha()])

SENTENCE_ENDERS = ".!\n?"
def _SplitIntoSentences(text):
  text = text + "."
  sentences = []
  start = 0
  idx = 0
  while idx < len(text):
    if text[idx] in SENTENCE_ENDERS:
      if start != idx:
        sentences.append(text[start:idx])
      start = idx+1
    idx += 1
  return sentences

# Flesch Reading Ease Score:
# 90-100    easily understandable by an average 11 year old student
# 60-70     easily understandable by 13 to 15 year old students
# 0-30      best understood by university graduates
def ReadingEase(words_per_sentence, syllables_per_word):
  return 206.835 - 1.015*words_per_sentence - 84.6*syllables_per_word

# Flesch-Kincaid GradeLevel
def GradeLevel(words_per_sentence, syllables_per_word):
  return 0.39*words_per_sentence + 11.8*syllables_per_word - 15.59

class TextScores(object):
  def __init__(self, text, printinfo=False):
    sentences = _SplitIntoSentences(text)
    self.words = []
    self.sentences = []
    self.syllables = []
    for raw_sentence in sentences:
      sent = []
      for raw_word in raw_sentence.split():
        word = _CleanWord(raw_word)
        if word:
          sylls = _SYLLABLE_DICT[word]
          self.syllables.append(sylls)
          self.words.append(word)
          sent.append(word)
      if sent:
        self.sentences.append(sent)
    self.total_words = len(self.words)
    self.total_sentences = len(self.sentences)
    self.total_syllables = sum(self.syllables)
    if not self.sentences or not self.words:
      # Essay is effectively empty
      self.empty = True
      self.words_per_sentence = -1
      self.syllables_per_word = -1
      self.ease = -1
      self.level = -1
      self.cleaned_text = ""
    else:
      self.empty = False
      self.words_per_sentence = len(self.words)*1.0/len(self.sentences)
      self.syllables_per_word = self.total_syllables*1.0/len(self.words)
      self.ease = ReadingEase(self.words_per_sentence, self.syllables_per_word)
      self.ease = max(0, 10*int(round(self.ease/10.0)))  # Round to nearest 10
      self.level = GradeLevel(self.words_per_sentence, self.syllables_per_word)
      self.level = max(0, int(round(self.level)))  # Round to nearest grade
      self.cleaned_text = ". ".join([" ".join([w for w in s])
                                     for s in self.sentences])

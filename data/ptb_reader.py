# Copyright 2015 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================


"""Utilities for parsing PTB text files."""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
import os
import tensorflow as tf


def _read_words(filename):
  with tf.gfile.GFile(filename, "r") as f:
    return f.read().decode("utf-8").replace("\n", "<eos>").split()


def _read_chars(filename):
  with tf.gfile.GFile(filename, "r") as f:
    return f.read().decode("utf-8").replace("\n", "<eos>").replace(
        "<eos>", "+")


def _build_vocab(filename):
  data = _read_words(filename)

  counter = collections.Counter(data)
  count_pairs = sorted(counter.items(), key=lambda x: (-x[1], x[0]))

  words, _ = list(zip(*count_pairs))
  word_to_id = dict(zip(words, range(len(words))))
  return word_to_id


def _build_char(filename):
  data = _read_chars(filename)
  counter = collections.Counter(data)
  count_pairs = sorted(counter.items(), key=lambda x: (-x[1], x[0]))

  chars, _ = list(zip(*count_pairs))
  char_to_id = dict(zip(chars, range(len(chars))))
  return char_to_id


def _build_vocab_existing(filename):
  with open(filename, 'r') as f:
    wlist = [ll.strip('\n').split(',') for ll in f.readlines()]
  wlist = map(lambda x: (x[0], int(x[1]) - 1), wlist)
  word_to_id = dict(wlist)
  return word_to_id


def _file_to_word_ids(filename, word_to_id):
  data = _read_words(filename)
  return [word_to_id[word] for word in data if word in word_to_id]


def _file_to_char_ids(filename, char_to_id):
  data = _read_chars(filename)
  return [char_to_id[char] for char in data if char in char_to_id]


def ptb_raw_data(data_path=None, level="word"):
  """Load PTB raw data from data directory "data_path".

  Reads PTB text files, converts strings to integer ids,
  and performs mini-batching of the inputs.

  The PTB dataset comes from Tomas Mikolov's webpage:

  http://www.fit.vutbr.cz/~imikolov/rnnlm/simple-examples.tgz

  Args:
    data_path: string path to the directory where simple-examples.tgz has
      been extracted.

  Returns:
    tuple (train_data, valid_data, test_data, vocabulary)
    where each of the data objects can be passed to PTBIterator.
  """

  # trainval_path = os.path.join(data_path, "ptb.train+valid.txt")

  if level != "word" and level != "char":
    raise Exception("Unknown level")

  if level == "word":
    encode = _file_to_word_ids
    build = _build_vocab
  else:
    encode = _file_to_char_ids
    build = _build_char

  train_path = os.path.join(data_path, "ptb.train.txt")
  valid_path = os.path.join(data_path, "ptb.valid.txt")
  test_path = os.path.join(data_path, "ptb.test.txt")

  # Use training + validation + testing set to build vocabulary!
  dictionary = build(train_path)
  train_data = encode(train_path, dictionary)
  valid_data = encode(valid_path, dictionary)
  test_data = encode(test_path, dictionary)
  vocabulary = len(dictionary)
  return train_data, valid_data, test_data, vocabulary


def ptb_producer(raw_data, batch_size, num_steps, name=None):
  """Iterate on the raw PTB data.

  This chunks up raw_data into batches of examples and returns Tensors that
  are drawn from these batches.

  Args:
    raw_data: one of the raw data outputs from ptb_raw_data.
    batch_size: int, the batch size.
    num_steps: int, the number of unrolls.
    name: the name of this operation (optional).

  Returns:
    A pair of Tensors, each shaped [batch_size, num_steps]. The second element
    of the tuple is the same data time-shifted to the right by one.

  Raises:
    tf.errors.InvalidArgumentError: if batch_size or num_steps are too high.
  """
  # with tf.name_scope(name, "PTBProducer", [raw_data, batch_size,
  # num_steps]):
  with tf.name_scope("PTBProducer"):
    raw_data = tf.convert_to_tensor(
        raw_data, name="raw_data", dtype=tf.int32)

    data_len = tf.size(raw_data)
    batch_len = data_len // batch_size
    rd = tf.slice(raw_data, [0], [batch_size * batch_len])
    data = tf.reshape(rd, [batch_size, batch_len])

    epoch_size = (batch_len - 1) // num_steps
    # assertion = tf.assert_positive(
    #     epoch_size,
    #     message="epoch_size == 0, decrease batch_size or num_steps")
    # with tf.control_dependencies([assertion]):
    epoch_size = tf.identity(epoch_size, name="epoch_size")

    i = tf.train.range_input_producer(epoch_size, shuffle=False).dequeue()
    x = tf.slice(data, [0, i * num_steps], [batch_size, num_steps])
    y = tf.slice(data, [0, i * num_steps + 1], [batch_size, num_steps])
    return x, y

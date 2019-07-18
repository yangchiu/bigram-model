import spacy
import os
import numpy as np
from keras.preprocessing.text import Tokenizer
from keras.utils import to_categorical
from keras.models import Sequential
from keras.layers import Dense, LSTM, Embedding
from pickle import dump, load

save_dir = 'lstm_text_generation/'
if not os.path.exists(save_dir):
    os.makedirs(save_dir)

filename = 'moby_dick_four_chapters.txt' # 'melville-moby_dick.txt'


class NovelData():

    def __init__(self, save_dir, filename):
        print(f'* calling {NovelData.__init__.__name__}')

        self.tokenized_corpus = None
        self.get_corpus(save_dir, filename)

        # 25 training words + 1 target word
        self.seq_len = 25 + 1
        self.sequences = []
        self.generate_sequences()

        self.tokenizer = None
        self.indexed_sequences = []
        self.vocab_size = 0
        self.word2idx()

        self.train_steps = 25
        self.target_len = 1
        self.x = None
        self.y = None
        self.x_y_split()

    def get_corpus(self, save_dir, filename):
        print(f'* calling {NovelData.get_corpus.__name__}')

        with open(os.path.join(save_dir, filename)) as f:
            corpus = f.read()

        # have to run "python -m spacy download en" first
        nlp = spacy.load('en_core_web_sm', disable=['parser', 'tagger', 'ner'])
        # if you don't change max_length manually,
        # you may encounter this error:
        # ValueError: [E088] Text of length 1198622 exceeds maximum of 1000000. The v2.x parser and NER models
        # require roughly 1GB of temporary memory per 100,000 characters in the input. This means long texts may
        # cause memory allocation errors. If you're not using the parser or NER, it's probably safe to increase
        # the `nlp.max_length` limit. The limit is in number of characters, so you can check whether your inputs
        # are too long by checking `len(text)`.
        nlp.max_length = 1198623
        # corpus would be tokenized after nlp() operation
        self.tokenized_corpus = nlp(corpus)
        # remove punctuations
        self.tokenized_corpus = [
            token.text.lower() for token in self.tokenized_corpus
            if token.text not in '\n\n \n\n\n!"-#$%&()--.*+,-/:;<=>?@[\\]^_`{|}~\t\n '
        ]
        print(f'=> length of tokenized corpus = {len(self.tokenized_corpus)}')

    def generate_sequences(self):
        print(f'* calling {NovelData.generate_sequences.__name__}')

        for i in range(self.seq_len, len(self.tokenized_corpus)):
            seq = self.tokenized_corpus[i-self.seq_len:i]
            self.sequences.append(seq)

        print(f'=> generate {len(self.sequences)} sequences')

    def word2idx(self):
        print(f'* calling {NovelData.word2idx.__name__}')

        self.tokenizer = Tokenizer()
        self.tokenizer.fit_on_texts(self.sequences)
        # !!! the index starts from "1", instead of "0" !!!
        # print self.tokenizer.index_word to evaluate this
        #
        # so if you want to convert the indexed values into one-hot encoded,
        # the number of classes should be len + 1, with empty class 0
        self.indexed_sequences = self.tokenizer.texts_to_sequences(self.sequences)

        self.vocab_size = len(self.tokenizer.word_counts)
        print(f'=> vocab size = {self.vocab_size}')

        # convert train sequences to numpy array
        self.indexed_sequences = np.array(self.indexed_sequences)
        print(f'=> sequences shape = {self.indexed_sequences.shape}')

    def x_y_split(self):
        print(f'* calling {NovelData.x_y_split.__name__}')

        self.x = self.indexed_sequences[:, :-self.target_len]
        self.y = self.indexed_sequences[:, -self.target_len]
        # one-hot encoding
        self.y = to_categorical(self.y, num_classes=self.vocab_size+1)


if __name__ == '__main__':

    novel_data = NovelData(save_dir, filename)
    # because the index starts from "1", instead of "0"
    # a word is mapped to 1 ~ 17527
    # nothing is mapped to 0
    vocab_size = novel_data.vocab_size + 1
    steps = novel_data.train_steps

    # model
    model = Sequential()
    model.add(
        Embedding(input_dim=vocab_size,
                  output_dim=32,
                  input_length=novel_data.train_steps)
    )
    # units: dimensionality of the output space.
    # return_sequences: whether to return the last output in the output sequence, or the full sequence.
    model.add(LSTM(units=150,
                   return_sequences=True))
    # only keep the last output
    model.add(LSTM(units=150))
    # units: dimensionality of the output space.
    model.add(Dense(units=150, activation='relu'))
    model.add(Dense(units=vocab_size, activation='softmax'))

    # loss, optimizer, metric
    model.compile(
        # if your targets are one-hot encoded, use categorical_crossentropy.
        # if your targets are integers, use sparse_categorical_crossentropy.
        loss='categorical_crossentropy',
        optimizer='adam',
        metrics=['accuracy']
    )
    model.summary()

    model.fit(novel_data.x, novel_data.y, epochs=300, verbose=1)

    model.save(os.path.join(save_dir, 'model.h5'))
    dump(novel_data.tokenizer, open(os.path.join(save_dir, 'tokenizer'), 'wb'))






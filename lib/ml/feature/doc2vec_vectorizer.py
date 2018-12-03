import nltk
import numpy
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from sklearn.base import TransformerMixin


def _tokenize(doc):
    # assuming that this is used in a feature extractor that
    # performs tokenization, stemming, stop word filtering etc.
    # before this call
    return nltk.word_tokenize(doc)


def _get_tagged_docs(docs):
    for i, doc in enumerate(docs):
        words = _tokenize(doc)
        yield TaggedDocument(words, [i])


class Doc2VecVectorizer(TransformerMixin):
    def __init__(self, *args, **kwargs):
        self._model = Doc2Vec(*args, **kwargs)

    def fit(self, docs):
        tagged_docs = _get_tagged_docs(docs)
        self._model.build_vocab(tagged_docs)
        self._model.train(
            tagged_docs,
            total_examples=self._model.corpus_count,
            epochs=self._model.iter
        )
        return self

    def transform(self, docs):
        vectors = []
        for doc in docs:
            words = _tokenize(doc)
            vector = self._model.infer_vector(words)
            vectors.append(vector)
        return numpy.array(vectors)

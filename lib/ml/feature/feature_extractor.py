import os

from scipy import sparse
from sklearn.externals import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

from archii import config
from archii.ml.path import Path
from archii.ml.persistable import Persistable


def get_stop_words(lang):
    if lang == 'en':
        return "english"
    elif lang == 'da':
        stop_word_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "stop_words/danish.txt"
        )
        with open(stop_word_path, 'r') as f:
            return [line for line in f]
    else:
        return []


class FeatureExtractor(Persistable):

    @staticmethod
    def load(language):
        path = Path.feature_extractor(language)
        return joblib.load(path)

    def __init__(self, language):
        path = Path.feature_extractor(language)
        super().__init__(path)
        fe_config = config.get().ml_config. \
            feature_extractor_configs[language.code]
        self.ngram_range = fe_config.ngram_range
        self.document_cutting = fe_config.cut
        self.tokenizer = fe_config.tokenizer(language)
        self.fitted_on_all_data = False
        self.custom_features = fe_config.custom_features
        stop_words = get_stop_words(language.code)
        self.title_vectorizer = TfidfVectorizer(stop_words=stop_words,
                                                ngram_range=(1, 1),
                                                min_df=fe_config.title_min_df,
                                                max_df=fe_config.title_max_df)

        if fe_config.vectorizer == "tfidf":
            self.vectorizer = TfidfVectorizer(stop_words=stop_words,
                                              ngram_range=fe_config.ngram_range,
                                              min_df=0.01)
        else:
            # Completely user-supplied vectorizer...
            self.vectorizer = fe_config.vectorizer

    def _preprocess(self, docs):
        texts = [doc.text for doc in docs]
        result = []
        for text in texts:
            tokens = self.tokenizer.tokenize(text)
            if self.document_cutting:
                tokens = tokens[:self.document_cutting]
            result.append(" ".join(tokens))
        return result

    def fit_transform(self, docs, titles=None):
        preprocessed_texts = self._preprocess(docs)
        tfidf_vectors = self.vectorizer.fit_transform(preprocessed_texts)
        title_vectors = self.title_vectorizer.fit_transform(titles)
        vectors = sparse.hstack([tfidf_vectors, title_vectors])
        vectors = self._add_custom_features(vectors, docs)
        return vectors

    def transform(self, docs, titles=None):
        preprocessed_texts = self._preprocess(docs)
        tfidf_vectors = self.vectorizer.transform(preprocessed_texts)
        title_vectors = self.title_vectorizer.transform(titles)
        vectors = sparse.hstack([tfidf_vectors, title_vectors])
        vectors = self._add_custom_features(vectors, docs)
        return vectors

    def fit(self, docs, titles=None):
        preprocessed_texts = self._preprocess(docs)
        self.title_vectorizer.fit(titles)
        self.vectorizer.fit(preprocessed_texts)

    @staticmethod
    def exists(language):
        return os.path.isfile(Path.feature_extractor(language))

    def _add_custom_features(self, vectors, docs):
        if self.custom_features is None:
            return vectors
        for custom_feature in self.custom_features:
            column = []
            for doc in docs:
                feature = custom_feature(doc)
                column.append([feature])
            vectors = sparse.hstack([vectors, column])
        return vectors

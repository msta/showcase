import os
from datetime import datetime

from sklearn.externals import joblib

class Prediction:
    @property
    def probability(self):
        return self.probabilities[self.label]

    def __init__(self, label, probabilities, classifier_id):
        self.label = label
        self.probabilities = probabilities
        self.classifier_id = classifier_id

    def __eq__(self, other):
        if not isinstance(other, Prediction):
            return False
        return self.__dict__ == other.__dict__


class Classifier(Persistable):
    @staticmethod
    def load(entity):
        raise NotImplementedError

    def __init__(self, feature_extractor, model, uuid, path):
        super().__init__(path)
        self.feature_extractor = feature_extractor
        self.model = model
        self.uuid = uuid
        self.fitted_on_all_data = False

    def fit(self, documents, labels, titles=None):
        vectors = self.feature_extractor.transform(documents, titles)
        self.model.fit(vectors, labels)

    def predict(self, docs, titles=None):
        vectors = self.feature_extractor.transform(docs, titles)
        labels = self.model.predict(vectors)
        try:
            classes = self.model.classes_
        except AttributeError:
            classes = self.model.best_estimator_.classes_
        probabilities = self.model.predict_proba(vectors)
        probabilities = [{c: p for c, p in zip(classes, ps)}
                         for ps in probabilities]
        return [Prediction(label, ps, self.uuid)
                for label, ps in zip(labels, probabilities)]


class CategoryClassifier(Classifier):
    def __init__(self, category):
        model = config.get().ml_config.classifier_configs[category.index].model
        feature_extractor = FeatureExtractor.load(category.language)
        path = Path.classifier(category)
        uuid = ':'.join(
            [category.language.code,
             category.index,
             datetime.utcnow().isoformat()]
        )
        super().__init__(feature_extractor, model, uuid, path)

    @staticmethod
    def load(category):
        path = Path.classifier(category)
        return joblib.load(path)

    @staticmethod
    def exists(category):
        path = Path.classifier(category)
        return os.path.isfile(path)


class RootClassifier(Classifier):
    @staticmethod
    def load(language):
        path = Path.root_classifier(language)
        return joblib.load(path)

    def __init__(self, language):
        feature_extractor = FeatureExtractor.load(language)
        path = Path.root_classifier(language)
        uuid = ':'.join([language.code, datetime.utcnow().isoformat()])
        model = config.get().ml_config.classifier_configs[language.index].model
        super().__init__(feature_extractor, model, uuid, path)

    @staticmethod
    def exists(language):
        path = Path.root_classifier(language)
        return os.path.isfile(path)


class ClassifierCache:
    def __init__(self):
        self.root_classifier_cache = Cache(
            RootClassifier,
            key_function=lambda l: l.index
        )
        self.category_classifier_cache = Cache(
            CategoryClassifier,
            key_function=lambda c: c.index
        )

import os

import pandas
from sklearn.externals import joblib
from sklearn.model_selection import StratifiedKFold, train_test_split

from archii.database import label
from archii.ml.classification.validation_split import ValidationSplit
from archii.ml.path import Path
from archii.ml.persistable import Persistable
from archii import config


def _filter_too_few_labels(documents, labels):
    data = pandas.DataFrame(
        {
            'documents': documents,
            'categories': labels
        }
    )
    too_few = data.categories.value_counts() < config.get().ml_config.folds
    for l in too_few[too_few].index:
        data = data[data.categories != l]
    return data.documents, data.categories


def _split(language, folds, sample_size=None):
    documents = language.validated_documents
    labels = [label.leaf_label(doc) for doc in documents]
    if sample_size is not None:
        documents, _, labels, _ = train_test_split(
            documents,
            labels,
            test_size=1.0 - sample_size,
            stratify=labels
        )
    documents, labels = _filter_too_few_labels(documents, labels)
    splitter = StratifiedKFold(n_splits=folds)
    validation_splits = []
    splits = enumerate(splitter.split(documents, labels))
    for split_count, (train_indices, test_indices) in splits:
        train_docs = documents.iloc[train_indices]
        test_docs = documents.iloc[test_indices]
        train_ids, test_ids = (
            set(doc.id for doc in train_docs),
            set(doc.id for doc in test_docs)
        )
        validation_split = ValidationSplit(
            language,
            train_ids,
            test_ids,
            split_count + 1
        )
        validation_splits.append(validation_split)
    return validation_splits


class CrossValidationSplit(Persistable):
    @staticmethod
    def load(language):
        path = Path.cross_validation_split(language)
        return joblib.load(path)

    def __init__(self, language, folds=5, sample_size=None):
        path = Path.cross_validation_split(language)
        super().__init__(path)
        self.folds = _split(language, folds, sample_size)
        self.completed_folds = []
        self.current_fold = None

    def __iter__(self):
        return self

    def __next__(self):
        not_done = self.current_fold is not None and not self.current_fold.is_done
        try:
            if not_done:
                return self.current_fold
            else:
                if self.current_fold is not None:
                    self.completed_folds.append(self.current_fold)
                self.current_fold = self.folds.pop()
            self.persist()
            return self.current_fold
        except IndexError:
            if not_done:
                return self.current_fold
            self.current_fold = None
            self.persist()
            raise StopIteration

    @staticmethod
    def exists(language):
        path = Path.cross_validation_split(language)
        return os.path.isfile(path)

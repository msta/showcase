# -*- coding: utf-8 -*-
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC

SCORING = "f1_micro"
C_VALUES = [1e-2, 1e-1, 1, 10, 1e2]
ALPHA_VALUES = [1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1]
GAMMA_VALUES = [0.1, 1, 10, 1e2, 1e3]
VERBOSE = 0


def get(model_name):
    models = {
        "linear_svc_simple":
        SVC(C=1.0, kernel="linear", probability=True),

        "logistic_regression_simple":
        LogisticRegression(C=1.0, penalty="l1"),

        "linear_svc": GridSearchCV(
            estimator=SVC(verbose=VERBOSE),
            param_grid={"C": C_VALUES, "probability": [True]},
            scoring=SCORING
        ),

        "rbf_svc": GridSearchCV(
            estimator=SVC(verbose=VERBOSE),
            param_grid={
                "kernel": ["rbf"],
                "C": C_VALUES,
                "gamma": GAMMA_VALUES,
                "probability": [True]
            },
            scoring=SCORING
        ),

        "dimreduction": GridSearchCV(
            estimator=Pipeline(
                [
                    ("reduce_dim", SelectKBest(chi2)),
                    ("clf", SVC())
                ]
            ),
            param_grid={
                "reduce_dim__k": [1, 10, 100],
                "clf__probability": [True],
                "clf__kernel": ["linear"],
                "clf__C": C_VALUES
            },
            scoring=SCORING
        ),

        "dimred_nonlinear": GridSearchCV(
            estimator=Pipeline(
                [
                    ("reduce_dim", SelectKBest(chi2)),
                    ("clf", SVC())
                ]
            ),
            param_grid={
                "reduce_dim__k": [10, 20, 100, 500],
                "clf__C": C_VALUES,
                "clf__kernel": ["rbf"],
                "clf__gamma": GAMMA_VALUES,
                "clf__probability": [True]
            }
        )
    }
    try:
        return models[model_name]
    except KeyError:
        raise KeyError('Unknown model: %s' % model_name)

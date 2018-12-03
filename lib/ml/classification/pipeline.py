

def create_classification(prediction, category):
    classification = database.Classification()
    classification.category = category
    classification.classifier_id = prediction.classifier_id
    classification.timestamp = datetime.now()
    classification.validated = False
    classification.confidence = prediction.probability
    return classification


class Pipeline:
    def __init__(self, language):
        self.language = language

    @database.session
    def classify(self, documents, cache=None, titles=None):
        if not type(documents) == list:
            documents = [documents]
        if not type(titles) == list:
            titles = [titles]
        if cache:
            root_classifier = cache.root_classifier_cache.load(self.language)
        else:
            root_classifier = RootClassifier.load(self.language)
        root_predictions = root_classifier.predict(documents, titles)
        for prediction, doc, title in zip(root_predictions, documents, titles):
            category = database.Category[prediction.label]
            classification = create_classification(prediction, category)
            doc.classes.add(classification)
            while CategoryClassifier.exists(category):
                if cache:
                    classifier = cache.category_classifier_cache.load(category)
                else:
                    classifier = CategoryClassifier.load(category)
                prediction = classifier.predict([doc], [title]).pop()
                category = database.Category[prediction.label]
                classification = create_classification(prediction, category)
                doc.classes.add(classification)

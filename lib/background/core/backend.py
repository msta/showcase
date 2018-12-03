import re
from io import BytesIO
import tempfile
from typing import NamedTuple, Sequence
import pickle
from collections import defaultdict

import phonenumbers

import archii.database as db
from archii import config, database
from archii.background.core.exceptions import ExtractionFailed
from archii.background.file_integration.document_meta import DocumentMeta
from archii.background.nlp.cpr_validator import validate_cpr
from archii.database import Classification, Company, Scan
from archii.database.models import (
    UserDocument,
    TrackedFolder,
    Document,
    Mention
)
from archii.files.file import File
from archii.files.storage import StorageFactory
from archii.files.utils import get_lang
from archii.log import Log
from archii.ml.classification.pipeline import Pipeline
from archii.background.core.elasticsearch_queries import (
    GDPRPersonQueryResult,
    CommonNameQueryResult
)
from archii.background.core.gdpr_document import (
    HighRiskDocument,
    RiskDocument
)
from archii.database.queries.gdpr_documents import delete_company_gdpr_results
from archii.database.models.gdpr_document import (
    HighRiskResult,
    LowRiskResult
)

MAX_ENTITY_LENGTH = 150


def _find_regex_entities(doc):
    cpr_pattern = r'\b[0-3][0-9]{5} ?-? ?([0-9]{4}|[xX]{4})\b'
    cpr_entity = db.get_by_id(db.NamedEntity, 'CPR_NUMBER')

    for match in re.finditer(cpr_pattern, doc.text):
        match_str = match.group()
        match_val = match_str.replace('-', "").replace(" ", "")
        if validate_cpr(match_val):
            db.add(
                Mention,
                document=doc,
                entity=cpr_entity,
                validated=False,
                start=match.start(),
                end=match.end(),
                occurrence=match_str
            )

    phone_entity = db.get_by_id(db.NamedEntity, 'PHONE_NUMBER')
    for match in phonenumbers.PhoneNumberMatcher(doc.text, 'DK'):
        db.add(
            Mention,
            document=doc,
            entity=phone_entity,
            validated=False,
            start=match.start,
            end=match.end,
            occurrence=match.raw_string
        )


def ner(document_id):
    def get_occurrence(document, start, end):
        return document.text[start:end]

    doc = db.get_by_id(Document, document_id)
    # entities = nlp.english.ner(doc.text)
    # TODO(Stahl) fix memory leak
    entities = []
    for span in entities:
        span_length = span.end_char - span.start_char
        if span_length > MAX_ENTITY_LENGTH:
            Log().warning("Detected abnormally large entity and skipping it",
                          document_id=document_id)
            continue
        entity = db.get_by_id(db.NamedEntity, span.label_)
        db.add(Mention,
               document=doc,
               entity=entity,
               validated=False,
               start=span.start_char,
               end=span.end_char,
               occurrence=get_occurrence(doc, span.start_char, span.end_char))
    _find_regex_entities(doc)
    Log().info(
        "Finished NER processing.",
        document=document_id,
        count=len(entities)
    )


def _get_file_to_tmp_path(
        storage_manager,
        document_meta: DocumentMeta
):
    stream = BytesIO()
    success, stream = storage_manager.get_file(
        document_meta.storage_key,
        stream
    )

    if not success:
        raise Exception('Failed to read file from the storage manager.')

    ext = '.' + document_meta.ext

    fd, file_path = tempfile.mkstemp(suffix=ext)

    with(open(fd, 'wb')) as file:
        file.write(stream.read())
        file.close()

    return file_path


def read_document(document_meta: DocumentMeta):
    """
    This task should:
        1. Read a document from a file
        2. Extract the text by normal means or OCR
        3. Connect the extracted document to the database entry with
        information about who entered the document into the system
    :param path: The local path of the file
    :param document_meta: Current processing document
    for the user/document relation
    :return: 'doc_exists': a bool indicating whether the document was
    already in the database,  'doc_id': the document int id, 'user_doc_id': the
    user document id
    """
    scan = db.get_by_id(Scan, document_meta.scan_id)
    data_location = scan.data_location
    storage_manager = StorageFactory.get_storage_manager(
        data_location, mode='datasource')

    tmp_path = _get_file_to_tmp_path(storage_manager, document_meta)

    f = File(tmp_path)

    doc_exists = doc = user_doc = None
    company = data_location.user.company
    with db.session:
        try:
            doc = db.get_company_doc_with_identifiers(
                company.id,
                f.md5(),
                document_meta.name
            )
            doc_exists = doc is not None

            if not doc_exists:
                doc = _create_document(f, document_meta)

            user_doc = _create_user_doc(document_meta, doc)
            doc.user_documents.add(user_doc)

            if document_meta.tracked_folder is not None:
                _add_tracked_folders(document_meta.tracked_folder, user_doc)
            scan.user_documents.add(user_doc)
            db.commit()

        except Exception as e:
            # Avoid doc/userdoc inconsistencies
            db.rollback()
            raise e

    return doc_exists, doc.id, user_doc.id


def _add_tracked_folders(tracked_folder_id, user_doc):
    tracked_folder = db.get_by_id(
        TrackedFolder,
        tracked_folder_id
    )
    user_doc.tracked_folders.add(tracked_folder)
    user_doc.private = tracked_folder.private


def _create_user_doc(document_meta: DocumentMeta, doc):
    with db.session:
        user_doc = UserDocument()
        user_doc.path = document_meta.original_path
        user_doc.timestamp = document_meta.timestamp
        user_doc.uuid = document_meta.uuid
        doc.user_documents.add(user_doc)
    return user_doc


def _create_document(file: File, document_meta):
    text = file.extract()
    language, prob = get_lang(text)
    allowed_languages = [lang.code for lang in db.get_languages()]
    if language not in allowed_languages:
        raise ExtractionFailed("Language not allowed")
    if prob < config.get().meta_config.min_lang_confidence:
        raise ExtractionFailed("Language confidence too low!")
    if not text:
        raise ExtractionFailed("No text on this document")
    # if not default language, do another extract
    if language != allowed_languages[0]:
        file.lang = language
        text = file.extract()
        if not text:
            raise ExtractionFailed("No text on this document")

    doc = Document()
    doc.name = document_meta.name
    doc.text = text
    doc.language = db.get_language_by_code(language)
    doc.md5 = file.md5()
    doc.extension = file.extension
    doc.size = file.size
    doc.last_modified = int(file.st_mtime)
    doc.language_probability = prob
    return doc


class LabelResult(NamedTuple):
    name: str
    confidence: float
    clf: str

    @classmethod
    def make(cls, classification: Classification) -> 'LabelResult':
        return LabelResult(
            classification.category.name,
            classification.confidence,
            classification.classifier_id
        )


class ClassifyTaskResult(NamedTuple):
    clazzes: Sequence[LabelResult]  # spelled with zz because of PEP8 bug E701
    md5: str

    @classmethod
    def make(cls, classification_list, md5):
        return ClassifyTaskResult(
            [LabelResult.make(clz)
             for clz in classification_list],
            md5
        )


def classify(document_id, user_doc_id, cache=None):
    doc = db.get_by_id(Document, document_id)

    if not doc:
        Log().warning("Document does not exists", document=document_id)
        raise ValueError("The document is not in the database.")

    if not doc.text:
        raise ValueError("No text on document")

    if doc.is_validated:
        validated = doc.validated_classes
        return ClassifyTaskResult.make(validated, doc.md5)

    default_language = db.get_default_language()
    language = doc.language or default_language
    user_doc = db.get_by_id(db.UserDocument, user_doc_id)
    pipeline = Pipeline(language)

    pipeline.classify(doc, titles=doc.name, cache=cache)
    latest_tracked_folder = user_doc.get_latest_tracked_folder()
    if latest_tracked_folder and latest_tracked_folder.access_groups:
        doc.assign_groups(latest_tracked_folder.access_groups)
    return ClassifyTaskResult.make(doc.classes, doc.md5)


def merge_sensitive_documents(company_id, query_result_list):
    with database.session:
        company = db.get_by_id(Company, company_id)
        cpr_documents = db.get_documents_with_cpr_numbers(company)
        phone_documents = db.get_documents_with_phone_numbers(
            company
        )

        phone_documents = {doc.id for doc in phone_documents if doc.is_fresh}
        cpr_documents = {doc.id for doc in cpr_documents if doc.is_fresh}

        high_risk_documents = defaultdict(
            lambda: HighRiskDocument()
        )
        risk_documents = defaultdict(lambda: RiskDocument())

        def process_high_risk_result(result_):
            document_: HighRiskDocument = high_risk_documents[result_.doc_id]
            document_.process(result_)

        def process_risk_result(result_):
            if result_.doc_id in cpr_documents:
                document_: HighRiskDocument = high_risk_documents[result_.doc_id]
            else:
                document_: RiskDocument = risk_documents[result_.doc_id]
            document_.process(result_)

        def process_common_name_risk_result(result_):
            if result_.doc_id in cpr_documents:
                document_: HighRiskDocument = high_risk_documents[result_.doc_id]
            else:
                document_: RiskDocument = risk_documents[result_.doc_id]
            document_.process_common_name_result(result_)

        def process_common_name_high_risk_result(result_):
            document_: HighRiskDocument = high_risk_documents[result_.doc_id]
            document_.process_common_name_result(result_)

        def process_gdpr_query_result(query_result_):
            for result in query_result_.high_risk_results:
                process_high_risk_result(result)
            for result in query_result_.partial_high_risk_results:
                process_high_risk_result(result)

            for result in query_result.risk_results:
                process_risk_result(result)
            for result in query_result.partial_risk_results:
                process_risk_result(result)

        def process_common_names_query_result(query_result_):
            for result in query_result_.high_risk_results:
                process_common_name_high_risk_result(result)
            for result in query_result_.risk_results:
                process_common_name_risk_result(result)

        for query_result in query_result_list:
            if isinstance(query_result, GDPRPersonQueryResult):
                process_gdpr_query_result(query_result)
            elif isinstance(query_result, CommonNameQueryResult):
                process_common_names_query_result(query_result)
            else:
                raise ValueError(
                    f'Unknown query result type: {type(query_result)}'
                )

        for doc_id in cpr_documents:
            document: HighRiskDocument = high_risk_documents[doc_id]
            document.process_cpr_doc(doc_id)

        for doc_id, doc in high_risk_documents.items():
            if doc_id in phone_documents:
                doc.add_phone_numbers(doc_id)
        for doc_id, doc in risk_documents.items():
            if doc_id in phone_documents:
                doc.add_phone_numbers(doc_id)

    Log().debug('Merging results is finished. Saving results.')

    high_risk_documents = list(high_risk_documents.values())
    risk_documents = list(risk_documents.values())

    with database.session:
        delete_company_gdpr_results(company.id)
        save_gdpr_results(company.id, high_risk_documents, risk_documents)

    Log().debug('Results saved. Finished processing GDPR.')
    return high_risk_documents, risk_documents


def _create_result_if_fresh(company, document: RiskDocument, orm_type):
    db_document = db.get_by_id(db.Document, document.meta['id'])
    if db_document.is_fresh:
        orm_type(
            company=company,
            data=pickle.dumps(document)
        )


def save_gdpr_results(company_id: int,
                      high_risk_documents: Sequence[HighRiskDocument],
                      risk_documents: Sequence[RiskDocument]):
    company = database.get_by_id(Company, company_id)

    for high_risk_document in high_risk_documents:
        _create_result_if_fresh(
            company, high_risk_document, HighRiskResult
        )

    for risk_document in risk_documents:
        _create_result_if_fresh(
            company, risk_document, LowRiskResult
        )

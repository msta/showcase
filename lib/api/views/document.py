from archii.api.permissions import PrivateEditDocumentPermission, authorize, \
    AssignGroupDocumentPermission
from archii.api.schemas.document import (
    DocumentIndexSchema,
    SensitiveDocumentsIndexSchema
)
from .utils import success_response


def similarity_repr(sim_docs):
    return {sim.id: sim.similar for sim in sim_docs}


def get_document_permissions(document, user_document):
    doc_groups = [group.id for group in
                  document.actual_groups]

    private_editable = authorize(
        PrivateEditDocumentPermission(user_document.id),
        silent=True
    )

    group_editable = authorize(
        AssignGroupDocumentPermission(user_document.id),
        silent=True
    )
    return {
        "groups": {
            "editable": group_editable,
            "value": doc_groups
        },
        "private": {
            "editable": private_editable,
            "value": user_document.private
        }
    }


def preprocess_document_schema(document, current_user, user_doc_pick_id=None):

    all_userdocuments = list(document.user_documents)

    if user_doc_pick_id:
        user_doc = [
            udoc for udoc in all_userdocuments
            if udoc.id == user_doc_pick_id
        ][0]
    else:
        this_user_userdocuments = document.user_documents_with_user(current_user)

        user_doc = (this_user_userdocuments[0]
                    if this_user_userdocuments
                    else all_userdocuments[0])

    all_user_names = set(user_doc.data_location.user.username
                         for user_doc in document.user_documents)

    permissions = get_document_permissions(document, user_doc)

    if document.is_validated:
        classifications = document.validated_classes  # also sorted
    else:
        classifications = document.sorted_classes

    return {
        "md5": document.md5,
        "id": document.id,
        "size": document.size,
        "language": document.language.code,
        "extension": document.extension,
        "name": document.name,
        "user_doc_id": user_doc.id,
        "path": user_doc.path,
        "upload_date": user_doc.timestamp,
        "data_location": user_doc.data_location.source_type,
        "users": list(all_user_names),
        "permissions": permissions,
        "ok": document.ok,
        "critical": document.critical,
        "categories": list(classifications)
    }


class View:
    def __init__(self, controllers=None):
        self.controllers = controllers

    def get_all_documents_view(self):
        """
        assumes that all documents have a corresponding user document.
        :return: a JSON view of the company index
        """
        documents = self.controllers.document_index()
        current_user = self.controllers.get_current_user()

        eligible_documents = [
            document for document in documents
            if list(document.user_documents) and document.sorted_classes
        ]

        preprocessed_schemas = [
            preprocess_document_schema(
                document, current_user
            ) for document in eligible_documents
        ]

        return DocumentIndexSchema(many=True).dump_data(
            preprocessed_schemas
        )

    def delete_documents_view(self):
        deleted_doc_count = self.controllers.delete_documents()
        return success_response(deleted_doc_count)

    def sensitive_documents_view(self, start, end):
        result = self.controllers.sensitive_documents(start, end)

        result = result if result else {}
        return SensitiveDocumentsIndexSchema().dump_data(result)

    def get_metadata_view(self, u_document_id):
        res = self.controllers.get_metadata(u_document_id)
        return success_response(res)

    def update_classification_view(self,
                                   document_id,
                                   leaf_category_id):
        rv = self.controllers.update_classification(
            leaf_category_id, document_id)

        return success_response({"updated": rv})

    def search_view(self, terms):
        def hit_repr(hit):
            return {
                "id": hit.meta.id,
                "name": hit.name,
                "score": hit.meta.score,
                "highlight": hit.meta.highlight.to_dict()
            }

        hits = self.controllers.search(terms)
        hits = [hit_repr(hit) for hit in hits]
        hits = list(sorted(hits, key=lambda h: h['score'], reverse=True))
        hits_dict = {
            "hits": hits
        }
        return success_response(hits_dict)

    def get_company_similarity_view(self):
        sim_docs = self.controllers.document_similarity_index()
        _repr = similarity_repr(sim_docs)
        return success_response(_repr)

    def create_company_similarity_view(self):
        task_id = self.controllers.create_company_similarity()
        return success_response({'task_id': task_id})

    def get_allowed_extensions(self):
        (documents,
         presentations,
         spreadsheets,
         hypertext) = self.controllers.get_allowed_extensions()

        def ext_spec(name, ext_list):
            return {
                "name": name,
                "extensions": ext_list
            }

        repr = [
            ext_spec("Document", documents),
            ext_spec("Presentation", presentations),
            ext_spec("Spreadsheet", spreadsheets),
            ext_spec("Hypertext", hypertext)
        ]

        return success_response(repr)

    def set_private_document_view(self, private, userdoc_id):
        document = self.controllers.set_private_document(
            userdoc_id, private
        )
        current_user = self.controllers.get_current_user()
        return DocumentIndexSchema().dump_data(
            preprocess_document_schema(document, current_user, userdoc_id)
        )

    def remove_gdpr_documents_view(self, document_ids):
        self.controllers.remove_gdpr_documents(
            document_ids
        )

        return success_response()

    def set_critical_documents_view(self, document_ids):
        self.controllers.set_critical_documents(
            document_ids
        )

        return success_response()

    def set_ok_documents_view(self, document_ids):
        self.controllers.set_ok_documents(
            document_ids
        )

        return success_response()

    def set_assign_document_groups_view(self, userdoc_id, group_ids):
        document = self.controllers.assign_document_groups(
            userdoc_id, group_ids
        )
        current_user = self.controllers.get_current_user()
        return DocumentIndexSchema().dump_data(
            preprocess_document_schema(document, current_user, userdoc_id)
        )

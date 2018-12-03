from celery import chord


@celery.task(name='process_document',
             bind=True,
             base=TaskLogger)
@db.session
def process(self, document_meta,
            user_id=None, parent_task_id=None):
    """
    This task defines the main flow for document processing:
        1. Extract the text from the document and insert into db
        1a. If in DB, just add user document
        2. In parallel execute:
            2a. Store the file on S3 and ElasticSearch
            2b. Classify the document
            2c. Do NER on the document
    :param self: Celery object
    :param document_meta: Current processing document
    :param user_id: Socket ID of the user who triggered the task
    :param parent_task_id: The integration that starts the process.
    this id is being used to inject in the beginning of the task to the log
    :return:
    """

    document_meta = DocumentMeta(*document_meta)
    original_path = document_meta.original_path
    document_name = document_meta.name
    scan_id = document_meta.scan_id

    scan = db.get_by_id(Scan, document_meta.scan_id)
    data_location = scan.data_location
    source_type = data_location.source_type
    company = data_location.user.company

    Log.set(document=document_name,
            path=original_path,
            integration=source_type,
            company=company.name)

    tasks = []
    # Task 1 - read_document and create it for the DB
    try:
        doc_exists, document_id, user_doc_id \
            = read_document_task(document_meta)
    except Exception as e:
        error_data = {"error": str(e)}
        after_process.delay(scan_id,
                            error_data,
                            False,
                            user_id=user_id)
        Log().exception('Read document failed',
                        exc_info=e)
        return

    data = {'document_id': user_doc_id}

    # Building all tasks after read_document #
    if not doc_exists:
        tasks.append(classify_task.s(document_id, user_doc_id, user_id=user_id))
        tasks.append(ner_task.s(document_id, user_id=user_id))
        tasks.append(store_document_task.s(document_meta.storage_key,
                                           document_id,
                                           data_location.id,
                                           user_id=user_id))
        callback = after_process.si(scan_id,
                                    data,
                                    True,
                                    user_id=user_id)
        error_callback = after_process.si(scan_id,
                                          data,
                                          False,
                                          user_id=user_id)

        callback.set(link_error=[error_callback])
        chord(tasks)(callback)
    else:
        after_process.delay(
            scan_id,
            data,
            True,
            user_id=user_id
        )

    return data


@celery.task(name='read_document',
             bind=True,
             base=TaskLogger)
@db.session
def read_document_task(self, processing):
    return read_document(processing)


def add_integration_data(process_data, success, scan):
    status, payload = scan.status_payload_repr()
    process_data['integration'] = {}
    process_data['integration'].update({
        'name': scan.data_location.source_type,
        'status': status,
        'status_payload': payload
    })
    if not success:
        process_data['error'] = process_data.get('error', 'An error happened')


@celery.task(name='after_process',
             bind=True,
             base=NotifierBase)
@db.session
def after_process(self, scan_id, process_data, success, user_id=None):
    """
    Decrement document counter and notify the client of the
    process task. If counter == 0 also notifies the
    client of the end of an integration.
    """
    scan = db.get_by_id(db.Scan, scan_id, silent=True)
    company = scan.data_location.user.company
    integration_files_remaining = scan.decr_doc_counter()
    no_files_remaining = integration_files_remaining == 0
    """
    This check is not threadsafe. So we have to make sure
    that sensitive_documents is safe to run again
    """
    if no_files_remaining:
        IntegrationProcess.set_state_done(scan.id)

        if not company.pending_integrations:
            # We use revoke and send to cancel any
            # pending sensitive documents tasks
            company = scan.data_location.user.company.id
            user = scan.data_location.user.id
            TaskHandler.revoke_and_send(
                "sensitive_documents",
                track_ids=[
                    TrackID.GDPR_COMPANY_SENSITIVE.format(company),
                    TrackID.GDPR_USER_SENSITIVE.format(user)
                ],
                kwargs={
                    "company_id": company,
                    "user_id": user,
                    "is_scan": True
                }
            )
    # Notifications
    add_integration_data(process_data,
                         success,
                         scan)
    return process_data


@celery.task(name='ner_document',
             bind=True, base=TaskLogger)
@db.session
def ner_task(self, document_id, user_id=None):
    ner(document_id)


class ClassifierCacheTask(TaskLogger):
    cache = ClassifierCache()


@celery.task(name='classify_document',
             bind=True, base=ClassifierCacheTask)
@db.session
def classify_task(self, document_id, user_doc_id, user_id=None):
    return classify(document_id, user_doc_id, cache=self.cache)


@celery.task(name='store_document',
             bind=True,
             base=TaskLogger,
             autoretry_for=(StorageFailed,),
             retry_kwargs={'max_retries': 3})
def store_document_task(
        self,
        file_storage_key,
        document_id,
        data_location_id,
        user_id=None
):
    store_document(file_storage_key, document_id, data_location_id)

    return {'document_id': document_id}

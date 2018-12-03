import os
import zlib
from calendar import timegm
from collections import defaultdict
from datetime import datetime, timedelta
from email.utils import parsedate_tz
from io import BytesIO

import archii.database as db
from archii import config
from archii.background.core.notifier import Notifier
from archii.background.core.similar_process import similar_documents_task
from archii.background.file_integration.document_meta import DocumentMeta
from archii.background.file_integration.services.strategy import \
    IntegrationStrategy, FileMetaData
from archii.database import Scan
from archii.database.models import IntegrationAlreadyDone
from archii.files.storage import StorageFactory
from archii.log import Log
from archii.services.email import EmailFactory
from archii.templates import TEMPLATES


def _convert_timestamp(date):
    tt = parsedate_tz(date)
    timestamp = timegm(tt) - tt[9]
    return datetime(1970, 1, 1) + timedelta(seconds=timestamp)


class IntegrationProcess(object):
    scan_id = -1
    user_id = None
    tracked_folders = None
    uuid_map = None
    scan = None
    data_location = None
    storage_manager = None
    fresh_uuids = None

    # Count how many documents were sent to be stored.
    # It's used in the 'store' method.
    documents_sent_for_processing = 0
    allowed_extensions = config.get().meta_config.allowed_extensions

    general_config = config.get()
    task_config = general_config.task_config

    def __init__(self,
                 strategy: IntegrationStrategy,
                 credentials,
                 scan_id,
                 process_callback=None,
                 download_path=None):
        self.strategy = strategy
        self.credentials = credentials
        self.scan_id = scan_id
        if download_path:
            self.download_path = os.path.abspath(download_path) + os.path.sep
        else:
            self.download_path = self.general_config. \
                meta_config.default_storage_folder

        self.process_callback = process_callback
        self.tracked_folders = []
        self.fresh_uuids = []

    def init_data(self):
        self.scan = db.get_by_id(Scan, self.scan_id)
        self.data_location = self.scan.data_location
        self.user_id = self.data_location.user.id
        self.tracked_folders = [
            t.dict_repr()
            for t in self.scan.tracked_folders]
        self.storage_manager = StorageFactory.get_storage_manager(
            self.data_location, mode='datasource'
        )
        self.uuid_map = defaultdict(list)
        [self.uuid_map[user_doc.uuid].append(user_doc.id)
         for user_doc in self.data_location.user_documents]

    def authenticate(self):
        self.strategy.authenticate()

    def run_process(self):
        self.authenticate()

        with db.session:
            self.init_data()
            self.set_state_started(self.scan_id)
        try:
            self.crawl()
        except Exception as e:
            # TODO(Stahl) Proper error handling for internal process
            raise e
        finally:
            self.strategy.close()

    def crawl(self):
        """
        Main method for an integration. Is called
        when the setup in the backend is completed.
        Should download all necessary files and call
        store_file for each relevant file.
        """
        self.strategy.check_connection()
        Log.set(integration_name=self.strategy.name,
                scan_id=self.scan_id,
                data_location_id=self.data_location.id)
        Log().info("Crawling integration")
        if self.tracked_folders:
            for tracked_folder in self.tracked_folders:
                try:
                    meta_data = self.strategy.meta_data_generator(
                        tracked_folder
                    )
                    for meta_datum in meta_data:
                        self._try_download_files(
                            meta_datum,
                            tracked_folder=tracked_folder
                        )
                except Exception as e:
                    Log().exception(
                        "Error when crawling tracked folder",
                        tracked_folder=tracked_folder
                    )
        else:
            meta_data = self.strategy.meta_data_generator()
            for meta_datum in meta_data:
                self._try_download_files(meta_datum)

    def _try_download_files(self, meta_datum, tracked_folder=None):
        # TODO(Stahl) refactor this into separate processes
        if isinstance(meta_datum, Exception):
            Log().exception("Error happened while "
                            "yielding file",
                            exc_info=meta_datum)
            return
        if not self.is_relevant(meta_datum):
            return

        file_uuid = self.get_identifier_hash(
            self.strategy.get_identifier(meta_datum)
        )
        # we'll wait and add all these fresh_uuids in
        # a session under finalize
        if file_uuid in self.uuid_map:
            Log().info('Adding file to fresh uuids', uuid=file_uuid)
            self.fresh_uuids.append((file_uuid, tracked_folder))
            return
        try:
            downloaded_files = self.strategy.get_files_as_bytes(meta_datum)
            for downloaded_file in downloaded_files:
                file_bytes, metadata = downloaded_file
                self.storage_manager.store_file(
                    BytesIO(file_bytes), self.get_identifier_hash(metadata.iuuid)
                )
                self.init_process_document(
                    metadata,
                    tracked_folder=tracked_folder
                )
        except Exception as e:
            Log().exception("Error happened while "
                            "processing file",
                            exc_info=e)
            raise e

    def is_relevant(self, file):
        extension = self.strategy.try_get_file_extension(file)
        # TODO(Magnus, Sune, Felipe) add logging statements
        # once we implement a type for file
        if not extension:
            return False

        return not self.is_too_big(file) \
            and extension in self.allowed_extensions

    def is_too_big(self, file):
        max_size = config.get().integration_config.max_file_size_mb
        return self.strategy.get_file_size_mb(file) > max_size

    def get_identifier_hash(self, identifier: str) -> str:
        # TODO(Magnus, Sune, Felipe) add integration test
        # that tests if documents are correctly added/ignored
        number = zlib.crc32(identifier.encode())
        return str(number)

    def init_process_document(self,
                              file_meta_data: FileMetaData,
                              tracked_folder=None):
        identifier_hash = self.get_identifier_hash(file_meta_data.iuuid)
        date: str = file_meta_data.created.strftime("%Y-%m-%d %H:%M:%S")
        tracked_folder_id = tracked_folder['id'] if tracked_folder else None

        document_meta = DocumentMeta(identifier_hash,
                                     file_meta_data.path,
                                     identifier_hash,
                                     date,
                                     file_meta_data.name,
                                     self.scan_id,
                                     file_meta_data.ext,
                                     tracked_folder=tracked_folder_id)
        Log().info(
            "Processing Document",
            original_path=file_meta_data.path,
            timestamp=date,
            name=file_meta_data.name
        )
        self.process_callback(
            document_meta,
            user_id=self.user_id
        )
        self.documents_sent_for_processing += 1

    def finalize(self):
        # needs a session
        scan = db.get_by_id(db.Scan, self.scan_id)
        for iuuid, tracked_folder_dict in self.fresh_uuids:
            Log().info('Adding fresh uuid', iuuid=iuuid)
            for user_doc_id in self.uuid_map[iuuid]:
                Log().info('Adding uuid to user_doc',
                           iuuid=iuuid,
                           user_doc_id=user_doc_id)
                user_doc = db.get_by_id(db.UserDocument, user_doc_id)
                scan.user_documents.add(user_doc)
                if tracked_folder_dict:
                    # refresh tracked folder
                    tracked_folder = db.get_by_id(db.TrackedFolder,
                                                  tracked_folder_dict['id'])
                    user_doc.tracked_folders.add(tracked_folder)
        total = self.documents_sent_for_processing
        Log().info('Documents sent for processing', count=total)
        db.commit()
        is_done = total == 0
        status, payload = None, None
        try:
            status, payload = self.scan.set_state_counting_done(total)
        except IntegrationAlreadyDone:
            is_done = True
        if is_done:
            Log().info("Integration finished in integration_process",
                       total=total)
            status, payload = self.set_state_done(self.scan_id)
        self.strategy.cleanup()
        self.strategy.close()
        Log().info("Integration complete")

        return {
            'name': self.strategy.name,
            'status': status,
            'status_payload': payload,
            'is_done': is_done
        }

    @classmethod
    @db.session
    def set_state_done(cls, scan_id):
        """
        1. Sets the integration state to 'done'
        2. If 'all_integrations_done' send an email and create a notification
        3. Notifies the data_location.user that the integration is done
        """
        scan = db.get_by_id(Scan, scan_id)
        data_location = scan.data_location

        user_id = data_location.user.id

        status, payload = scan.set_state_done()
        db.Notification.create_notification_integration(
            db.NotificationTypes.INTEGRATION_DONE,
            data_location
        )

        user = db.get_by_id(db.User, user_id)

        all_integrations_done = db.DataLocation.check_integrations_done(user)
        if all_integrations_done:
            Log().info("All integrations finished")
            if int(payload['total']) > 0:
                similar_documents_task.delay(user_id=user_id)

            cls._send_integrations_done_email(user)
            db.Notification(
                type_id=db.NotificationTypes.ALL_INTEGRATIONS_DONE,
                user=user,
                creation_date=datetime.now()
            )

        cls._send_integration_response(scan, user_id)
        return status, payload

    @staticmethod
    def set_state_started(scan_id):
        scan = db.get_by_id(Scan, scan_id)
        status, payload = scan.set_state_started()
        user_id = scan.data_location.user.id

        db.Notification.create_notification_integration(
            db.NotificationTypes.INTEGRATION_STARTED,
            scan.data_location
        )
        started_notification_data = {
            'name': scan.data_location.source_type,
            'status': status,
            'status_payload': payload
        }

        Notifier.send_notifier_response(
            'integration', started_notification_data, user_id)

        return status, payload

    @staticmethod
    def _send_integrations_done_email(user):
        if not user.is_gdpr:
            EmailFactory.send_email(TEMPLATES.INTEGRATIONS_DONE,
                                    {},
                                    user.email)

    @staticmethod
    def _send_integration_response(scan, user_id):
        status, payload = scan.status_payload_repr()
        integration_data = {
            'name': scan.data_location.source_type,
            'status': status,
            'status_payload': payload,
        }

        Notifier.send_notifier_response(
            'integration', integration_data, user_id)

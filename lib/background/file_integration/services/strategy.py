import datetime
from typing import Sequence, NamedTuple, Optional

class FileMetaData(NamedTuple):
    name: str
    path: str
    iuuid: str
    ext: str
    created: datetime.datetime


class FileByteMetaDataPair(NamedTuple):
    file_bytes: bytes
    metadata: FileMetaData


class IntegrationStrategy(object):
    @property
    def name(self):
        raise NotImplementedError()

    @property
    def credential_attributes(self):
        raise NotImplementedError()

    verbose = False
    connected = False

    general_config = config.get()

    def __init__(self, credentials):
        self.credentials = credentials

    def trim_dots(self, string):
        return string.strip('.')

    def verify_credentials(self, silent=False):
        for attr in self.credential_attributes:
            if attr not in self.credentials:
                if silent:
                    return False
                error_msg = 'Missing credentials'
                Log().error(error_msg,
                            credentials=self.credentials,
                            expected_attr=self.credential_attributes)
                raise exceptions.BadIntegrationCredentials(error_msg)
        return True

    def authenticate(self):
        """
        1. verify credential format
        2. test credentials against integration with connnection
        """
        self.verify_credentials()
        self._authenticate()
        self.connected = True

    def _authenticate(self):
        """
        The actual implementation of authenticate
        :return:
        """
        raise NotImplementedError

    def get_account_identifier(self):
        return self._get_account_identifier()

    def _get_account_identifier(self) -> str:
        raise NotImplementedError

    def get_identifier(self, file) -> str:
        raise NotImplementedError

    def meta_data_generator(self, tracked_folder=None):
        raise NotImplementedError

    def get_files_as_bytes(self, file) -> Sequence[FileByteMetaDataPair]:
        # TODO(Stahl) in mixed strategies, this can be
        # get_file as bytes and get_files as bytes separately
        raise NotImplementedError

    def get_file_size_mb(self, file) -> float:
        raise NotImplementedError

    def close(self):
        self.connected = False

    def check_connection(self):
        if not self.connected:
            error_msg = "Trying to crawl before connecting"
            Log().exception(error_msg)
            raise exceptions.NotConnectedError(error_msg)

    def try_get_file_extension(self, file) -> Optional[str]:
        raise NotImplementedError

    def cleanup(self):
        # TODO(stahl) with separate strategies, only use this for local
        pass

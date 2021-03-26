"""
Base class for computation procedures
"""

from __future__ import annotations

import abc
import logging
from ..interface.models import KVStore, AllResultTypes

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..storage_sockets.sqlalchemy_socket import SQLAlchemySocket


class BaseTasks(abc.ABC):
    def __init__(self, storage: SQLAlchemySocket):
        self.storage = storage
        self.logger = logging.getLogger(type(self).__name__ + "_procedure")

    def submit_tasks(self, data):
        """
        Creates results/procedures and tasks in the database
        """

        results_ids, existing_ids = self.parse_input(data)
        submitted_ids = [x for x in results_ids if x not in existing_ids and x is not None]

        n_inserted = 0
        missing = []
        for num, x in enumerate(results_ids):
            if x is None:
                missing.append(num)
            else:
                n_inserted += 1

        results = {
            "meta": {
                "n_inserted": n_inserted,
                "duplicates": [],
                "validation_errors": [],
                "success": True,
                "error_description": False,
                "errors": [],
            },
            "data": {"ids": results_ids, "submitted": submitted_ids, "existing": existing_ids},
        }

        return results

    def retrieve_outputs(self, rdata):
        """
        Retrieves (possibly compressed) outputs from an AtomicResult (that has been converted to a dictionary)

        This function modifies the rdata dictionary in-place
        """

        # Get the compressed outputs if they exist
        stdout = rdata["extras"].pop("_qcfractal_compressed_stdout", None)
        stderr = rdata["extras"].pop("_qcfractal_compressed_stderr", None)
        error = rdata["extras"].pop("_qcfractal_compressed_error", None)

        # Create KVStore objects from these
        if stdout is not None:
            stdout = KVStore(**stdout)
        if stderr is not None:
            stderr = KVStore(**stderr)
        if error is not None:
            error = KVStore(**error)

        # This shouldn't happen, but if they aren't compressed, check for
        # uncompressed
        if stdout is None and rdata.get("stdout", None) is not None:
            self.logger.warning(f"Found uncompressed stdout for result id {rdata['id']}")
            stdout = KVStore(data=rdata["stdout"])
        if stderr is None and rdata.get("stderr", None) is not None:
            self.logger.warning(f"Found uncompressed stderr for result id {rdata['id']}")
            stderr = KVStore(data=rdata["stderr"])
        if error is None and rdata.get("error", None) is not None:
            self.logger.warning(f"Found uncompressed error for result id {rdata['id']}")
            error = KVStore(data=rdata["error"])

        # Now add to the database and set the ids in the diction
        if stdout is not None:
            rdata["stdout"] = self.storage.output_store.add([stdout])[0]
        if stderr is not None:
            rdata["stderr"] = self.storage.output_store.add([stderr])[0]
        if error is not None:
            rdata["error"] = self.storage.output_store.add([error])[0]

    @abc.abstractmethod
    def verify_input(self, data):
        pass

    @abc.abstractmethod
    def parse_input(self, data):
        pass

    @abc.abstractmethod
    def handle_completed_output(self, task_id: int, base_result_id: int, manager_name: str, result: AllResultTypes):
        pass

from __future__ import annotations
import os
import tempfile
import time
import multiprocessing
from queue import Empty # Just for exception handling
import logging
import logging.handlers
from concurrent.futures import ProcessPoolExecutor
from .qc_queue import QueueManager

from .interface import FractalClient
from .postgres_harness import TemporaryPostgres
from .port_util import find_port
from .config import FractalConfig, DatabaseConfig, updated_nested_dict
from .periodics import PeriodicsProcess
from .app.flask_app import FlaskProcess
from .process_runner import ProcessBase, ProcessRunner

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Dict, Any, List, Optional


def attempt_client_connect(uri: str, **client_args) -> FractalClient:
    """
    Attempt to obtain a FractalClient for a host and port

    This will make several attempts in case the server hasn't been completely booted yet

    If a connection is successful, the FractalClient is returned. Otherwise an exception
    is raised representing the exception raised from the last attempt at FractalClient construction.

    Parameters
    ----------
    uri: str
        URI to the rest server (ie, http://127.0.01:1234)
    **client_args
        Additional arguments to pass to the FractalClient constructor

    Returns
    -------
    FractalClient
        A client connected to the given host and port
    """

    # Try to connect 20 times (~2 seconds). If it fails after that, raise the last exception
    for i in range(21):
        try:
            return FractalClient(uri, **client_args)
        except Exception:
            if i == 20:
                # Out of attempts. Just give the last exception
                raise
            else:
                time.sleep(0.2)

    raise RuntimeError("PROGRAMMER ERROR - should never get here")


class SnowflakeComputeProcess(ProcessBase):
    """
    Runs  a compute manager in a separate process
    """

    def __init__(
            self,
            qcf_config: FractalConfig,
            max_workers: int = 2
    ):
        self._qcf_config = qcf_config
        self._max_compute_workers = max_workers

        # We cannot instantiate these here. The .run() function will be run in a separate process
        # and so instantiation must happen there
        self.worker_pool = None
        self.queue_manager = None

    def run(self) -> None:
        host = self._qcf_config.flask.bind
        port = self._qcf_config.flask.port
        uri = f'http://{host}:{port}'
        client = attempt_client_connect(uri)

        self.worker_pool = ProcessPoolExecutor(self._max_compute_workers)
        self.queue_manager = QueueManager(client, self.worker_pool, manager_name="snowflake_compute")
        self.queue_manager.start()

    def finalize(self) -> None:
        if self.worker_pool is not None:
            self.worker_pool.shutdown()
        if self.queue_manager is not None:
            self.queue_manager.stop()


class FractalSnowflake:
    def __init__(
        self,
        start: bool = True,
        max_compute_workers: Optional[int] = 2,
        enable_watching: bool = True,
        database_config: Optional[DatabaseConfig] = None,
        flask_config: str = "snowflake",
        extra_config: Optional[Dict[str, Any]] = None
    ):
        """A temporary FractalServer that can be used to run complex workflows or try new computations.

        ! Warning ! All data is lost when the server is shutdown.
        """

        self._logger = logging.getLogger('fractal_snowflake')

        # Create a temporary directory for everything
        self._tmpdir = tempfile.TemporaryDirectory()

        # db is in a subdir of that
        db_dir = os.path.join(self._tmpdir.name, 'db')

        if database_config is None:
            self._storage = TemporaryPostgres(data_dir=db_dir)
            self._storage.harness.create_database()
            self._storage_uri = self._storage.database_uri(safe=False)
            db_config = self._storage.config
        else:
            self._storage = None
            self._storage_uri = database_config.uri
            db_config = database_config

        fractal_host = "127.0.0.1"
        fractal_port = find_port()
        self._fractal_uri = f'http://{fractal_host}:{fractal_port}'

        # Create a configuration for QCFractal
        # Assign the log level for subprocesses. Use the same level as what is assigned for this object
        loglevel = self._logger.getEffectiveLevel()

        qcf_cfg = {}
        qcf_cfg["base_directory"] = self._tmpdir.name
        qcf_cfg["loglevel"] = logging.getLevelName(loglevel)
        qcf_cfg["database"] = db_config.dict()
        qcf_cfg["enable_views"] = False
        qcf_cfg["flask"] = {'config_name': flask_config, 'bind': fractal_host, 'port': fractal_port}
        qcf_cfg["enable_security"] = False

        # Add in any options passed to this Snowflake
        if extra_config is None:
            extra_config = {}

        updated_nested_dict(qcf_cfg, extra_config)
        self._qcf_config = FractalConfig(**qcf_cfg)
        self._max_compute_workers = max_compute_workers


        # Do we want to enable watching/waiting for finished tasks?
        self._completed_queue = None
        if enable_watching:
            # We use fork inside ProcessRunner, so we must use for here to set up the Queues
            # This must be changed if the ProcessRunner is ever changed to use seomthing else
            mp_ctx = multiprocessing.get_context('fork')
            self._completed_queue = mp_ctx.Queue()
            self._all_completed = set()

        ######################################
        # Now start the various subprocesses #
        ######################################
        flask = FlaskProcess(self._qcf_config, self._completed_queue)
        periodics = PeriodicsProcess(self._qcf_config, self._completed_queue)

        self._flask_proc = ProcessRunner('snowflake_flask', flask, start)
        self._periodics_proc = ProcessRunner('snowflake_periodics', periodics, start)

        if self._max_compute_workers > 0:
            compute = SnowflakeComputeProcess(self._qcf_config, self._max_compute_workers)
            self._compute_proc = ProcessRunner('snowflake_compute', compute, start)

    def stop(self):
        # Send all our processes SIGTERM
        if self._max_compute_workers > 0:
            self._compute_proc.stop()

        self._flask_proc.stop()
        self._periodics_proc.stop()

    def start(self):
        if self._max_compute_workers > 0 and not self._compute_proc.is_alive():
            self._compute_proc.start()
        if not self._flask_proc.is_alive():
            self._flask_proc.start()
        if not self._periodics_proc.is_alive():
            self._periodics_proc.start()


    def __del__(self):
        self.stop()

    def get_uri(self) -> str:
        """
        Obtain the URI/address of the REST interface of this server

        Returns
        -------
        str
            Address/URI of the rest interface (ie, 'http://127.0.0.1:1234')
        """

        return f'http://{self._qcf_config.flask.bind}:{self._qcf_config.flask.port}'

    def await_results(self, ids: Optional[List[int]] = None, timeout: float = None) -> bool:
        """
        Wait for computations to complete

        This function will block until the specified computations are complete (either success for failure).
        If timeout is given, that is the maximum amount of time to wait for a result. This timer is reset
        after each completed result.

        Parameters
        ----------
        ids: Optional[List[int]]
            Result/Procedure IDs to wait for. If not specified, all currently incomplete tasks
            will be waited for.

        timeout: float
            Maximum time to wait for a single result.


        Returns
        -------
        bool
            True if all the results were received, False if timeout has elapsed without receiving a completed computation
        """
        logger = logging.getLogger(__name__)

        if self._completed_queue is None:
            raise RuntimeError("Cannot wait for results when the completed queue is not enabled. See the 'enable_watching' argument to the constructor")

        if ids is None:
            c = self.client()
            proc = c.query_tasks(status=["WAITING", "RUNNING"])
            ids = [x.base_result for x in proc]

        ids = set(int(x) for x in ids)

        # Remove any we have already marked as completed
        ids = ids - self._all_completed

        if len(ids) == 0:
            logger.debug("All tasks are already finished")
            return True

        logger.debug("Waiting for ids: " + str(ids))

        while len(ids) > 0:
            # The queue stores a tuple of (id, type, status)
            try:
                base_result_info = self._completed_queue.get(True, timeout)
            except Empty:
                logger.warning(f'No tasks finished in {timeout} seconds')
                return False

            logger.debug("Task finished: id={}, status={}".format(*base_result_info))
            finished_id = base_result_info[0]

            # Add it to the list of all completed results we have seen
            self._all_completed.add(finished_id)

            # We may not be watching for this id, but if we are, remove it from the list
            # we are watching
            if finished_id in ids:
                ids.remove(finished_id)
                logger.debug(f"Removed id={finished_id}. Remaining ids: " + "None" if len(ids) == 0 else str(ids))

        return True

    def client(self) -> FractalClient:
        '''
        Obtain a FractalClient connected to this server
        '''

        return attempt_client_connect(self.get_uri())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.stop()

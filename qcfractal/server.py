"""
The FractalServer class
"""

import logging
import ssl

import tornado.ioloop
import tornado.web

from . import db_sockets
from . import queue_handlers
from . import web_handlers

myFormatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

def _build_ssl():
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    import sys
    import socket
    import datetime
    import ipaddress
    import random

    hostname = socket.gethostname()
    public_ip = ipaddress.ip_address(socket.gethostbyname(hostname))

    key = rsa.generate_private_key(public_exponent=65537, key_size=1024, backend=default_backend())

    alt_name_list = [x509.DNSName(hostname), x509.IPAddress(ipaddress.ip_address(public_ip))]
    alt_names = x509.SubjectAlternativeName(alt_name_list)

    # Basic data
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])
    basic_contraints = x509.BasicConstraints(ca=True, path_length=0)
    now = datetime.datetime.utcnow()

    # Build cert
    cert = (x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(int(random.random() * sys.maxsize))
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=10*365))
        .add_extension(basic_contraints, False)
        .add_extension(alt_names, False)
        .sign(key, hashes.SHA256(), default_backend())) # yapf: disable

    # Build and return keys
    cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ) # yapf: disable

    return (cert_pem, key_pem)

class FractalServer(object):
    def __init__(
            self,

            # Server info options
            port=8888,
            io_loop=None,

            security=None,
            ssl_options=None,

            # Database options
            db_ip="127.0.0.1",
            db_port=27017,
            db_username=None,
            db_password=None,
            db_type="mongo",
            db_project_name="molssidb",

            # Queue options
            queue_socket=None,

            # Log options
            logfile_name=None):

        # Save local options
        self.port = port
        if ssl_options is False:
            self._address = "http://localhost:" + str(self.port) + "/"
        else:
            self._address = "https://localhost:" + str(self.port) + "/"

        # Setup logging.
        self.logger = logging.getLogger("FractalServer")
        self.logger.setLevel(logging.INFO)

        app_logger = logging.getLogger("tornado.application")
        if logfile_name is not None:
            handler = logging.FileHandler(logfile_name.logfile)
            handler.setLevel(logging.INFO)

            handler.setFormatter(myFormatter)

            self.logger.addHandler(handler)
            app_logger.addHandler(handler)

            self.logger.info("Logfile set to {}\n".format(logfile_name))
        else:
            app_logger.addHandler(logging.StreamHandler())
            self.logger.addHandler(logging.StreamHandler())
            self.logger.info("No logfile given, setting output to stdout\n")

        # Build security layers
        if security is None:
            db_bypass_security = True
        elif security == "local":
            db_bypass_security = False
        else:
            raise KeyError("Security option '{}' not recognized.".format(security))

        # Handle SSL
        ssl_ctx = None
        if ssl_options is None:
            self.logger.warning("No SSL files passed in, generating self-signed SSL certificate.")
            self.logger.warning("Clients must use `verify=False` when connecting.\n")

            cert, key = _build_ssl()

            # Add quick names
            cert_name = db_project_name + "_ssl.crt"
            key_name = db_project_name + "_ssl.key"

            ssl_options = {"crt": cert_name, "key": key_name}

            with open(cert_name, "wb") as handle:
                handle.write(cert)

            with open(key_name, "wb") as handle:
                handle.write(key)

            ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_ctx.load_cert_chain(ssl_options["crt"], ssl_options["key"])

            # Destroy keyfiles upon close
            import atexit
            import os
            atexit.register(os.remove, cert_name)
            atexit.register(os.remove, key_name)
        elif ssl_options is False:
            ssl_ctx = None
        elif isinstance(ssl_options, dict):
            if ("crt" not in ssl_options) or ("key" not in ssl_options):
                raise KeyError("'crt' (SSL Certificate) and 'key' (SSL Key) fields are required for `ssl_options`.")

            ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_ctx.load_cert_chain(ssl_options["crt"], ssl_options["key"])
        else:
            raise KeyError("ssl_options not understood")

        # Setup the database connection
        self.db = db_sockets.db_socket_factory(
            db_ip,
            db_port,
            project_name=db_project_name,
            username=db_username,
            password=db_password,
            db_type=db_type,
            bypass_security=db_bypass_security)

        # Pull the current loop if we need it
        if io_loop is None:
            self.loop = tornado.ioloop.IOLoop.current()
        else:
            self.loop = io_loop

        # Build up the application
        self.objects = {
            "db_socket": self.db,
            "logger": self.logger,
        }

        endpoints = [
            (r"/molecule", web_handlers.MoleculeHandler, self.objects),
            (r"/option", web_handlers.OptionHandler, self.objects),
            (r"/collection", web_handlers.CollectionHandler, self.objects),
            (r"/result", web_handlers.ResultHandler, self.objects),
            (r"/service", web_handlers.ServiceHandler, self.objects),
        ]

        # Queue handlers
        if queue_socket is not None:

            queue_nanny, queue_scheduler, service_scheduler = queue_handlers.build_queue(
                queue_socket, self.objects["db_socket"])

            # Add the socket to passed args
            self.objects["queue_socket"] = queue_socket
            self.objects["queue_nanny"] = queue_nanny

            # Add the endpoint
            endpoints.append((r"/scheduler", queue_scheduler, self.objects))
            endpoints.append((r"/service_scheduler", service_scheduler, self.objects))

        # Build the app
        app_settings = {
            "compress_response": True,
            "serve_traceback": True,
            # "debug": True,
        }
        self.app = tornado.web.Application(endpoints, **app_settings)

        self.http_server = tornado.httpserver.HTTPServer(self.app, ssl_options=ssl_ctx)

        self.http_server.listen(self.port)

        # Add in periodic callbacks

        self.logger.info("DQM Server successfully initialized at {}\n".format(self._address))

        self.periodic = {}

    def start(self):
        """
        Starts up all IOLoops and processes
        """

        self.logger.info("DQM Server successfully started. Starting IOLoop.\n")

        # Add canonical queue callback
        nanny = tornado.ioloop.PeriodicCallback(self.objects["queue_nanny"].update, 2000)
        nanny.start()
        self.periodic["queue_nanny_update"] = nanny

        # Add services callback
        nanny_services = tornado.ioloop.PeriodicCallback(self.objects["queue_nanny"].update_services, 2000)
        nanny_services.start()
        self.periodic["queue_nanny_services"] = nanny_services

        # Soft quit with a keyboard interupt
        try:
            self.loop.start()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """
        Shuts down all IOLoops
        """
        self.loop.stop()
        for cb in self.periodic.values():
            cb.stop()

        self.logger.info("DQM Server stopping gracefully. Stopped IOLoop.\n")

    def get_address(self, function=""):
        return self._address + function


if __name__ == "__main__":

    server = FractalServer()
    server.start()

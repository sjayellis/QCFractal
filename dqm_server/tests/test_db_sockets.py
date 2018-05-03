"""
Tests the database wrappers
"""

import pytest
import numpy as np

# Import the DQM collection
import dqm_server as dserver
import dqm_server.interface as dclient


@pytest.fixture(scope="module", params=["mongo"])
def db_socket(request):
    print("")
    db_name = "dqm_local_values_test"

    # IP/port/drop table is specific to build
    if request.param == "mongo":
        db = dserver.db_socket_factory("127.0.0.1", 27017, db_name, db_type=request.param)

        # Clean and re-init the databse
        db.client.drop_database(db._project_name)
        db.init_database()
    else:
        raise KeyError("DB type %s not understood" % request.param)

    yield db

    if request.param == "mongo":
        db.client.drop_database(db_name)
    else:
        raise KeyError("DB type %s not understood" % request.param)


def test_molecules_add(db_socket):

    water = dclient.data.get_molecule("water_dimer_minima.psimol")

    # Add once
    ret = db_socket.add_molecules(water.to_json())
    assert ret["nInserted"] == 1

    # Try duplicate adds
    ret = db_socket.add_molecules(water.to_json())
    assert ret["nInserted"] == 0
    assert ret["errors"][0] == (water.get_hash(), 11000)

    # Pull molecule from the DB for tests
    db_json = db_socket.get_molecules(water.get_hash(), index="hash")[0]
    water_db = dclient.Molecule.from_json(db_json)
    water_db.compare(water)

    # Cleanup adds
    ret = db_socket.del_molecules(water.get_hash(), index="hash")
    assert ret == 1


def test_molecules_add_many(db_socket):
    water = dclient.data.get_molecule("water_dimer_minima.psimol")
    water2 = dclient.data.get_molecule("water_dimer_stretch.psimol")

    ret = db_socket.add_molecules([water.to_json(), water2.to_json()])
    assert ret["nInserted"] == 2

    # Cleanup adds
    ret = db_socket.del_molecules([water.get_hash(), water2.get_hash()], index="hash")
    assert ret == 2

    ret = db_socket.add_molecules([water.to_json(), water2.to_json()])
    assert ret["nInserted"] == 2

    # Cleanup adds
    ret = db_socket.del_molecules(ret["ids"], index="id")
    assert ret == 2


def test_molecules_get(db_socket):

    water = dclient.data.get_molecule("water_dimer_minima.psimol")

    # Add once
    ret = db_socket.add_molecules(water.to_json())
    assert ret["nInserted"] == 1
    water_id = ret["ids"][0]

    # Pull molecule from the DB for tests
    db_json = db_socket.get_molecules(water_id, index="id")[0]
    water_db = dclient.Molecule.from_json(db_json)
    water_db.compare(water)

    # Cleanup adds
    ret = db_socket.del_molecules(water_id, index="id")
    assert ret == 1


def test_options_add(db_socket):

    opts = dclient.data.get_options("psi_default")

    ret = db_socket.add_options(opts)
    assert ret["nInserted"] == 1

    ret = db_socket.add_options(opts)
    assert ret["nInserted"] == 0

    del opts["_id"]
    assert opts == db_socket.get_options({"name": opts["name"], "program": opts["program"]})[0]


def test_options_error(db_socket):
    opts = dclient.data.get_options("psi_default")

    del opts["name"]
    ret = db_socket.add_options(opts)
    assert ret["nInserted"] == 0
    assert len(ret["validation_errors"]) == 1


def test_databases_add(db_socket):

    db = {"category": "OpenFF", "name": "Torsion123", "something": "else", "array": ["54321"]}

    ret = db_socket.add_database(db)
    del db["_id"]
    assert ret["nInserted"] == 1

    new_db = db_socket.get_database(db["category"], db["name"])
    assert db == new_db

    ret = db_socket.del_database(db["category"], db["name"])
    assert ret == 1


def test_results_add(db_socket):

    # Add two waters
    water = dclient.data.get_molecule("water_dimer_minima.psimol")
    water2 = dclient.data.get_molecule("water_dimer_stretch.psimol")
    mol_insert = db_socket.add_molecules([water.to_json(), water2.to_json()])

    page1 = {
        "molecule_id": mol_insert["ids"][0],
        "method": "M1",
        "basis": "B1",
        "option": "default",
        "program": "P1",
        "other_data": 5
    }

    page2 = {
        "molecule_id": mol_insert["ids"][1],
        "method": "M1",
        "basis": "B1",
        "option": "default",
        "program": "P1",
        "other_data": 10
    }

    ret = db_socket.add_results([page1, page2])
    assert ret["nInserted"] == 2

    # assert page1 == db_socket.get_results({"_id": ret["ids"][0]})

    ret = db_socket.del_molecules(mol_insert["ids"], index="id")
    assert ret == 2


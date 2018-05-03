"""
Database connection class which directly calls the PyMongo API to capture
cammon subroutines.
"""



try:
    import pymongo
except ImportError:
    raise ImportError("Mongo db_socket requires pymongo, please install this python module or try a different db_socket.")

import pandas as pd
import numpy as np
from bson.objectid import ObjectId
import copy

# Pull in the hashing algorithms from the client
from .. import interface

def _translate_molecule_index(index):
    if index in ["id", "ids"]:
        return "_id"
    elif index == "hash":
        return "molecule_hash"
    elif index in ["_id", "molecule_hash"]:
        return index
    else:
        raise KeyError("Molecule Index '{}' not understood".format(index))

def _str_to_indices(ids):
    for num, x in enumerate(ids):
        if isinstance(x, str):
            ids[num] = ObjectId(x)


class MongoSocket:
    """
    This is a Mongo QCDB socket class.
    """

    def __init__(self, url, port, project="molssidb", username=None, password=None, authMechanism="SCRAM-SHA-1", authSource=None):
        """
        Constructs a new socket where url and port points towards a Mongod instance.

        """

        # Static data
        self._valid_collections = {"molecules", "databases", "results", "options"}
        self._collection_indices = {
            "databases": ["category", "name"],
            "options": ["name", "program"],
            "results": ["molecule_id", "method", "basis", "option", "program"],
            "molecules": ["molecule_hash"]
        }

        self._url = url
        self._port = port

        # Are we authenticating?
        if username:
            self.client = pymongo.MongoClient(url, port, username=username, password=password, authMechanism=authMechanism, authSource=authSource)
        else:
            self.client = pymongo.MongoClient(url, port)

        # Isolate objects to this single project DB
        self._project_name = project
        self._project = self.client[project]

        new_collections = self.init_database()
        for k, v in new_collections.items():
            if v:
                print("New collection '%s' for database!" % k)


    def __repr__(self):
        return "<MongoSocket: address='%s:%d:%s'>" % (self._url, self._port, self._project_name)

    def init_database(self):
        """
        Builds out the initial project structure.
        """
        # Try to create a collection for each entry
        collection_creation = {}
        for col in self._valid_collections:
            try:
                self._project.create_collection(col)
                collection_creation[col] = True

            except pymongo.errors.CollectionInvalid:
                collection_creation[col] = False

        # Build the indices
        for col, indices in self._collection_indices.items():
            idx = [(x, pymongo.ASCENDING) for x in indices]
            self._project[col].create_index(idx)

        # Return the success array
        return collection_creation

    def get_project_name(self):
        return self._project_name

    def add_molecules(self, data):
        """
        Adds molecules to the database.

        Parameters
        ----------
        data : dict or list of dict
            Structured instance of the molecule.

        Returns
        -------
        bool
            Whether the operation was successful.
        """

        # If only a single promote it to a list
        if isinstance(data, dict):
            data = [data]

        # Build a dictionary of new molecules
        new_mols = {}
        for dmol in data:
            mol = interface.Molecule(dmol, dtype="json", orient=False)
            new_mols[mol.get_hash()] = mol

        # We need to filter out what is already in the database
        old_mols = self.get_molecules(list(new_mols.keys()), index="hash")

        # Run a comparison against hash collisions, can be sped up
        errors = []
        for old_mol in old_mols:
            old_hash = old_mol["molecule_hash"]
            old_mol = interface.Molecule(old_mol, dtype="json", orient=False)

            if old_mol.compare(new_mols[old_hash]):
                del new_mols[old_hash]
                errors.append((old_hash, 11000))

        new_inserts = []
        for new_hash, new_mol in new_mols.items():
            data = new_mol.to_json()
            data["molecule_hash"] = new_hash
            new_inserts.append(data)

        ret = self._add_generic(new_inserts, "molecules")
        ret["errors"].extend(errors)
        return ret

    def add_options(self, data):
        """
        Adds options to the database.

        Parameters
        ----------
        data : dict or list of dict
            Structured instance of the options.

        Returns
        -------
        bool
            Whether the operation was successful.
        """

        # If only a single promote it to a list
        if isinstance(data, dict):
            data = [data]

        new_options = []
        validation_errors = []
        for dopt in data:

            error = interface.schema.validate(dopt, "options", return_errors=True)
            if error is True:
                new_options.append(dopt)
            else:
                validation_errors.append((dopt, error))

        ret = self._add_generic(new_options, "options")
        ret["validation_errors"] = validation_errors
        return ret

    def add_database(self, data):
        """
        Adds a database to the database.

        Parameters
        ----------
        data : dict
            Structured instance of the database.

        Returns
        -------
        bool
            Whether the operation was successful.
        """

        return self._add_generic([data], "databases")

    def add_results(self, data):
        """
        Adds a page to the database.

        Parameters
        ----------
        data : dict
            Structured instance of the page.

        Returns
        -------
        bool
            Whether the operation was successful.
        """

        return self._add_generic(data, "results")

    def _add_generic(self, data, collection):
        """
        Helper function that facilitates adding a record.
        """

        ret = {"errors": [], "ids":[], "nInserted": 0, "success": False}
        if len(data) == 0:
            return ret

        try:
            tmp = self._project[collection].insert_many(data, ordered=False)
            ret["success"] = tmp.acknowledged
            ret["ids"] = [str(x) for x in tmp.inserted_ids]
            ret["nInserted"] = len(tmp.inserted_ids)
            ret["errors"] = []
        except pymongo.errors.BulkWriteError as tmp:
            ret["success"] = False
            # ret["ids"] = [str(x) for x in tmp.inserted_ids]
            ret["nInserted"] = tmp.details["nInserted"]
            ret["errors"] = [(x["op"]["_id"], x["code"]) for x in tmp.details["writeErrors"]]
        return ret

    def del_by_index(self, collection, hashes, index="_id"):
        """
        Helper function that facilitates deletion based on hash.
        """

        if isinstance(hashes, str):
            hashes = [hashes]

        if index == "_id":
            _str_to_indices(hashes)

        return (self._project[collection].delete_many({index: {"$in" : hashes}})).deleted_count


    def del_molecules(self, values, index="id"):
        """
        Removes a molecule from the database from its hash.

        Parameters
        ----------
        hash_val : str or list of strs
            The hash of a molecule.

        Returns
        -------
        bool
            Whether the operation was successful.
        """

        index = _translate_molecule_index(index)

        return self.del_by_index("molecules", values, index=index)

    def del_database(self, category, name):
        """
        Removes a database from the database from its hash.

        Parameters
        ----------
        hash_val : str or list of strs
            The hash of a database.

        Returns
        -------
        bool
            Whether the operation was successful.
        """

        return (self._project["databases"].delete_one({"category": category, "name": name})).deleted_count


    def del_page_by_index(self, hash_val):
        """
        Removes a page from the database from its hash.

        Parameters
        ----------
        hash_val : str or list of strs
            The hash of a page.

        Returns
        -------
        bool
            Whether the operation was successful.
        """

        return self.del_by_index("results", hash_val)

    def evaluate(self, hashes, methods, field="return_value"):
        """
        Queries monogod for all results containing a molecule specified in
        `hashes` and a method specified in `methods`. For all matches, finds
        their `field` value and populates the relevant dataframe cell.

        Parameters
        ----------
        hashes : list
            A list of molecules hashes.
        methods : list
            A list of methods (modelchems).
        field : "return_value", optional
            A page field.

        Returns
        -------
        dataframe
            Returns a dataframe with your results. The rows will have the
            molecule hashes and the columns will have the method names. Each
            dataframe[molecule][method] cell contains the respective field
            value.

        Notes
        -----
        Empty cells will contain NaN.

        """
        hashes = list(hashes)
        methods = list(methods)
        command = [{"$match": {"molecule_hash": {"$in": hashes}, "modelchem": {"$in": methods}}}]
        results = list(self.project["results"].aggregate(command))
        d = {}
        for mol in hashes:
            for method in methods:
                d[mol] = {}
                d[mol][method] = np.nan
        for item in results:
            scope = item
            try:
                for name in field.split("."):
                    scope = scope[name]
                d[item["molecule_hash"]][item["modelchem"]] = scope
            except KeyError:
                pass
        if isinstance(methods, str):
            methods = [methods]
        return pd.DataFrame(data=d, index=methods).transpose()


    def list_methods(self, hashes):
        """
        Displays all methods that are used by each molecule in `hashes`.

        Parameters
        ----------
        hashes : list
            A list of molecules hashes.

        Returns
        -------
        dataframe
            Returns a dataframe with your results. The rows will have the
            molecule hashes and the columns will be numbered. Each cell contains
            a method used by the molecule in that row.

        """
        d = {}
        for mol in hashes:
            records = list(self.project["results"].find({"molecule_hash": mol}))
            d[mol] = []
            for rec in records:
                d[mol].append(rec["modelchem"])

        df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in d.items()])).transpose()
        return df

    def search_qc_variable(self, hashes, field):
        """
        Displays the first `field` value for each molecule in `hashes`.

        Parameters
        ----------
        hashes : list
            A list of molecules hashes.
        field : str
            A page field.

        Returns
        -------
        dataframe
            Returns a dataframe with your results. The rows will have the
            molecule hashes and the column will contain the name. Each cell
            contains the field value for the molecule in that row.

        """
        d = {}
        for mol in hashes:
            command = [{
                "$match": {
                    "molecule_hash": mol
                }
            }, {
                "$group": {
                    "_id": {},
                    "value": {
                        "$push": "$" + field
                    }
                }
            }]
            results = list(self.project["results"].aggregate(command))
            if len(results) == 0 or len(results[0]["value"]) == 0:
                d[mol] = None
            else:
                d[mol] = results[0]["value"][0]
        return pd.DataFrame(data=d, index=[field]).transpose()


    def get_value(self, field, db, rxn, stoich, method, do_stoich=True, debug_level=1):
        command = [{
            "$match": {
                "name": db
            }
        }, {
            "$project": {
                "reactions": 1
            }
        }, {
            "$unwind": "$reactions"
        }, {
            "$match": {
                "reactions.name": rxn
            }
        }, {
            "$group": {
                "_id": {},
                "stoich": {
                    "$push": "$reactions.stoichiometry." + stoich
                }
            }
        }]
        records = list(self.project["databases"].aggregate(command))

        if len(records) > 0:
            success = True
            molecules = records[0]["stoich"][0]
            res = []
            stoich_encoding = []

            for mol in molecules:
                stoich_encoding.append(molecules[mol])
                command = [{
                    "$match": {
                        "molecule_hash": mol,
                        "modelchem": method
                    }
                }, {
                    "$group": {
                        "_id": {},
                        "value": {
                            "$push": "$" + field
                        }
                    }
                }]
                page = list(self.project["results"].aggregate(command))
                if len(page) == 0 or len(page[0]["value"]) == 0:
                    success = False
                    break
                res.append(page[0]["value"][0])
                # debug.log(debug_level, 2, (stoich_encoding))

            if success:
                if do_stoich:
                    acc = 0
                    for i in range(0, len(stoich_encoding)):
                        acc += float(res[i] * stoich_encoding[i])
                    return acc
                return res

        # debug.log(debug_level, 2, ("Fallback attempt"))
        if field == "return_value":
            command = [{
                "$match": {
                    "name": db
                }
            }, {
                "$project": {
                    "reactions": 1
                }
            }, {
                "$unwind": "$reactions"
            }, {
                "$match": {
                    "reactions.name": rxn
                }
            }, {
                "$group": {
                    "_id": {},
                    "reaction_results": {
                        "$push": "$reactions.reaction_results." + stoich
                    }
                }
            }]
            page = list(self.project["databases"].aggregate(command))
            if len(page) > 0 and method in page[0]["reaction_results"][0]:
                return page[0]["reaction_results"][0][method]
        return None

    def get_series(self, field, db, stoich, method, do_stoich=True, debug_level=1):
        database = self.project["databases"].find_one({"name": db})
        if database == None:
            return None
        res = []
        index = []
        for item in database["reactions"]:
            res.append(
                self.get_value(field, db, item["name"], stoich, method, do_stoich, debug_level))
            index.append(item["name"])
        print("I am getting methods", method)
        return pd.DataFrame(data={method: res}, index=index)

    def get_dataframe(self, field, db, stoich, methods, do_stoich=True, debug_level=1):
        database = self.project["databases"].find_one({"name": db})
        if database == None:
            return None

        names = []
        for item in database["reactions"]:
            names.append(item["name"])

        count = 0
        res = []

        for name in names:
            res.append([])
            for m in methods:
                val = self.get_value(field, db, name, stoich, m, do_stoich, debug_level)
                res[count].append(val)
            count += 1

        return pd.DataFrame(data=res, index=names, columns=methods)


    # Do a lookup on the results collection using a <molecule, method> key.
    def get_results(self, query, projection={}):

        parsed_query = {}

        # We are querying via id
        if "_id" in query:
            if len(query) > 1:
                raise KeyError("ID was provided, cannot use other indices")

            if not isinstance(parsed_query, (list, tuple)):
                parsed_query["_id"] = [query["_id"]]
            else:
                parsed_query["_id"] = query["_id"]

            _str_to_indices(parsed_query["_id"])

        else:
            # Check if there are unknown keys
            remain = set(query) - set(self._collection_indices["results"])
            if remain:
                raise KeyError("Results query found unkown keys {}".format(list(remain)))

            for key, value in query:
                if isinstance(value, (list, tuple)):
                    parsed_query[key] = {"$in": value}
                else:
                    parsed_query[key] = value

        proj = copy.deepcopy(projection)
        proj["_id"] = False
        ret = self._project["results"].find_one(query, projection=proj)
        if ret is None:
            ret = []

        return list(ret)

    def get_database(self, category, name):
        return self._project["databases"].find_one({"category": category, "name": name}, projection={"_id": False})

    def get_options(self, data):

        if isinstance(data, dict):
            data = [data]

        ret = []
        for d in data:
            tmp = self._project["options"].find_one(
                {
                    "name": d["name"],
                    "program": d["program"]
                }, projection={"_id": False})
            ret.append(tmp)

        return ret

    def get_molecules(self, molecule_ids, index="id"):
        index = _translate_molecule_index(index)

        if not isinstance(molecule_ids, (list, tuple)):
            molecule_ids = [molecule_ids]

        if index == "_id":
            _str_to_indices(molecule_ids)

        ret = self._project["molecules"].find({index: {"$in": molecule_ids}})
        if ret is None:
            ret = []

        return list(ret)

    def json_query(self, json_data):
        """
        Wraps the MongoSocket in a JSON query.

        Parameters
        ----------
        json_data : dict
            Dictionary of data has function, args, and kwargs arguments

        Returns
        -------
        result : anytime
            Return the requested MongoSocket call.

        """

        keys = list(json_data)
        if "function" not in keys:
            raise KeyError("MongoSocket:json_query: 'funciton' are not found in keys")

        function = getattr(self, json_data["function"])

        if "args" in keys:
            args = json_data["args"]
        else:
            args = []

        if "kwargs" in keys:
            kwargs = json_data["kwargs"]
        else:
            kwargs = {}

        return function(*args, **kwargs)

    def mongod_query(self, *args, **kwargs):
        """
        Bad hack to make inserting a MongoSocket or Client transparent.
        Should revisit this!
        """

        json_data = {}
        json_data["function"] = args[0]
        json_data["args"] = args[1:]
        json_data["kwargs"] = kwargs

        return self.json_query(json_data)

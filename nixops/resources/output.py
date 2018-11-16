# -*- coding: utf-8 -*-

# Arbitrary JSON.

import os
import nixops.util
import nixops.resources

import tempfile
import shutil
import subprocess

class OutputDefinition(nixops.resources.ResourceDefinition):
    """Definition of an Output."""

    @classmethod
    def get_type(cls):
        # type: () -> (str)
        return "output"

    @classmethod
    def get_resource_type(cls):
        # type: () -> (str)
        return "output"

    def __init__(self, xml):
        # type: (xml.etree.ElementTree.Element) -> None
        nixops.resources.ResourceDefinition.__init__(self, xml)
        self.script = xml.find("attrs/attr[@name='script']/string").get("value")
        self.name = xml.find("attrs/attr[@name='name']/string").get("value")

    def show_type(self):
        # type: () -> (str)
        return "{0}".format(self.get_type())

class OutputState(nixops.resources.ResourceState):
    """State of an output."""
    state = nixops.util.attr_property("state", nixops.resources.ResourceState.MISSING, int)
    script = nixops.util.attr_property("script",None)
    value = nixops.util.attr_property("value",None)
    name =  nixops.util.attr_property("name",None)

    @classmethod
    def get_type(cls):
        # type: () -> (str)
        return "output"

    @property
    def resource_id(self):
        # type: () -> Optional[str]
        if self.value is not None:
            # Avoid printing any potential secret information
            return "{0}/{1}".format(self.name,hash(self.value))
        else:
            return None

    def __init__(self, depl, name, id):
        # type: (nixops.deployment.Deployment,str,int) -> None
        self.id = id
        nixops.resources.ResourceState.__init__(self, depl, name, id)

    def create(self, defn, check, allow_reboot, allow_recreate):
        # type: (nixops.resources.output.OutputDefinision,bool,bool,bool) -> None
        if (self.script != defn.script) or self.value is None:
            self.name = defn.name
            try:
                output_dir = tempfile.mkdtemp(prefix="nixops-output-tmp")
                self.log("Running shell function for output ‘{0}’...".format(defn.name))
                env = {}
                env.update(os.environ)
                env.update({"out":output_dir})
                res = subprocess.check_output(
                        [defn.script],
                        env=env,
                        shell=True)
                with self.depl._db:
                    self.value = res
                    self.state = self.UP
                    self.script = defn.script
            finally:
                shutil.rmtree(output_dir)

    def prefix_definition(self, attr):
        # type: (Dict[str,Any]) -> Dict[str,Any]
        return {('resources', 'output'): attr}

    def get_physical_spec(self):
        # type: () -> (Optional[str])
        return {'value': self.value}

    def destroy(self, wipe=False):
        # type: (bool) -> bool
        if self.depl.logger.confirm("are you sure you want to destroy {0}?".format(self.name)):
            self.log("destroying...")
        else:
            raise Exception("can't proceed further")
            return False
        self.value = None
        self.state = self.MISSING
        return True

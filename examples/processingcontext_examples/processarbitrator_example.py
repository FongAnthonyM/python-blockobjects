#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""processarbitrator_example.py
An example of how to use the ProcessArbitrator class.
"""

# Header #
__package_name__ = "blockobjects"

__author__ = "Anthony Fong"
__credits__ = ["Anthony Fong"]
__copyright__ = "Copyright 2022, Anthony Fong"
__license__ = "MIT"

__version__ = "0.1.0"


# Imports #
# Standard Libraries #
from os import getpid

# Third-Party Packages #
from blockobjects.process import DEFAULT_PROCESS_CONTEXT, ProcessArbitrator


# Definitions #
# Classes #
class ProcessArbitratorExample(ProcessArbitrator):
    # Class Attributes #
    public_exposed = True  # Setting this was unnecessary but illustrates its use
    exposed = {"_available"}
    unexposed = {"unavailable"}
    local_methods = {"local_method"}

    # Attributes #
    untransmittable = {"secret"}

    number: int = 1
    item: int = 10
    secret: int = 100

    def __init__(self, number=1, item=10, secret=100, *args, **kwargs):
        self.number = number
        self.item = item
        self.secret = secret

        super().__init__(*args, **kwargs)

    # Exposed Methods #
    def running_pid(self):
        return getpid()

    def multiply(self, num) -> float:
        return float(self.number * num)

    def available(self):
        return "available"

    def _available(self):
        return "available"

    # Unexposed Methods #
    def unavailable(self):
        return getpid()

    def _unavailable(self):
        return getpid()

    # Local Methods #
    # Running local methods which can invoke their server version can be useful, especially for manual arbitration
    # Unexposed Methods run methods locally but cannot invoke the server version of the method
    # Local Methods run method locally and can invoke server version of the method
    def _unavailable_interface(self):
        """Checks if the method the unexposed method can invoke the server version of the method."""
        # Unexposed methods cannot invoke the server version of the method
        # Unsuitable for manual arbitration
        if self.is_proxy():
            return hasattr(self._proxy, "_unavailable_interface")  # This will always be False
        else:
            return True

    def local_method(self):
        """Gets the process id of the proxy and the server if the server is alive."""
        # Local methods can invoke the server version of the method
        # Suitable for manual arbitration
        # Great for controlling proxy recursion (if server also creates another server to proxy from)
        proxy_pid = getpid()
        if self.is_proxy():
            server_pid, _ = self._proxy.local_method()  # Evoke the server version of the method
            return proxy_pid, server_pid
        else:
            return proxy_pid, None


# Functions #
def method_execution_overview():
    print(f"Method Execution Overview: \n")

    # Create Process Arbitrate
    arbitrate = ProcessArbitratorExample(2)

    # Local Calls #
    pid = arbitrate.running_pid()
    public_result = arbitrate.multiply(2)  # Is public
    private_result = arbitrate._unavailable()  # Is private
    exposed_call_result = arbitrate._available()  # Name in exposed list
    unexposed_call_result = arbitrate.unavailable()  # Name in unexposed list
    unexposed_server_invocation = arbitrate._unavailable_interface()  # Unexposed method trying to invoke server method
    local_pid, server_pid = arbitrate.local_method()  # Local method invoking server method

    # Print Results
    print(f"Local Calls:")
    print(f"Same Process: {pid} == {getpid()}")
    print(f"Public Call: {public_result} == 4.0")
    print(f"Private Call: {private_result} == {getpid()}")
    print(f"Exposed Call: {exposed_call_result} == available")
    print(f"Unexposed Call: {unexposed_call_result} == {getpid()}")
    print(f"Unexposed Local Call Only: {unexposed_server_invocation} == True")
    print(f"Local Method: {local_pid} == {getpid()} and {server_pid} == None")
    print(f"")

    # Sever Calls #
    # Start Server
    arbitrate.start_server()

    # Check Server Status
    assert arbitrate.is_proxy()
    assert arbitrate.is_alive()

    # Run the same methods
    pid = arbitrate.running_pid()
    public_result = arbitrate.multiply(2)  # Is public
    private_result = arbitrate._unavailable()  # Is private
    exposed_call_result = arbitrate._available()  # Name in exposed list
    unexposed_call_result = arbitrate.unavailable()  # Name in unexposed list
    unexposed_server_invocation = arbitrate._unavailable_interface()  # Unexposed method trying to invoke server method
    local_pid, server_pid = arbitrate.local_method()  # Local method invoking server method

    # Stop Server
    arbitrate.stop_server()

    # Check Server Status
    assert not arbitrate.is_proxy()
    assert not arbitrate.is_alive()

    # Print Results
    print(f"Server Calls:")
    print(f"Different Processes: {pid} != {getpid()}")
    print(f"Public Call: {public_result} == 4.0")
    print(f"Private Call: {private_result} == {getpid()}")
    print(f"Exposed Call: {exposed_call_result} != available")
    print(f"Unexposed Call: {unexposed_call_result} == {getpid()}")
    print(f"Unexposed Sever Invocation: {unexposed_server_invocation} == False")
    print(f"Local Method: {local_pid} == {getpid()} and {server_pid} == {pid}")
    print(f"")


def arbitrate_state_overview():
    print(f"Arbitrate State Overview: \n")

    # Create Process Arbitrate
    arbitrate = ProcessArbitratorExample(2, secret=-1)

    # Check Values
    print(f"Default Values:")
    print(f"number: {arbitrate.number} == 2")
    print(f"item: {arbitrate.item} == 10")
    print(f"secret: {arbitrate.secret} == -1")
    print(f"")

    # Start Server
    arbitrate.start_server()  # All attributes are sent to the server (including untransmittable attributes)

    # Check Server Status
    assert arbitrate.is_proxy()
    assert arbitrate.is_alive()

    # Make a local change which will not be reflected in the server
    arbitrate.number = 1
    arbitrate.item = 50
    arbitrate.secret = -20

    print(f"Local Changes:")
    print(f"Local vs Server number: {arbitrate.number} != {arbitrate.get_attribute('number')}")
    print(f"Local vs Server item: {arbitrate.item} != {arbitrate.get_attribute('item')}")
    print(f"Local vs Server secret: {arbitrate.secret} != {arbitrate.get_attribute('secret')}")
    print(f"")

    # Update local values from the server (except for untransmittable attributes)
    arbitrate.update()

    print(f"Local Update:")
    print(f"Local vs Server number: {arbitrate.number} == {arbitrate.get_attribute('number')}")
    print(f"Local vs Server item: {arbitrate.item} == {arbitrate.get_attribute('item')}")
    print(f"Local vs Server secret: {arbitrate.secret} != {arbitrate.get_attribute('secret')}")
    print(f"")

    # Update server values from the local (except for untransmittable attributes)
    arbitrate.number = 1
    arbitrate.item = 50
    arbitrate.secret = -20
    arbitrate.update_server()

    print(f"Sever Update:")
    print(f"Local vs Server number: {arbitrate.number} == {arbitrate.get_attribute('number')}")
    print(f"Local vs Server item: {arbitrate.item} == {arbitrate.get_attribute('item')}")
    print(f"Local vs Server secret: {arbitrate.secret} != {arbitrate.get_attribute('secret')}")
    print(f"")

    # Stop Server
    arbitrate.stop_server()

    # Check Server Status
    assert not arbitrate.is_proxy()
    assert not arbitrate.is_alive()


# Main #
if __name__ == "__main__":
    # Set Default Process Context
    DEFAULT_PROCESS_CONTEXT.select_context("multiprocessing")

    method_execution_overview()
    arbitrate_state_overview()

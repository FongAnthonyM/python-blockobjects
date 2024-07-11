#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" proxy_example.py
An example of how to create proxies using a process context.
"""
# Imports #
# Standard Libraries #
from os import getpid

# Third-Party Packages #
from blockobjects.process import ManagerContext, MultiProcessingContext


# Definitions #
# Classes #
class ExampleClass:
    # Class Attributes #
    exposed = {"_available"}
    unexposed = {"unavailable"}

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


# Functions #
def method_execution_overview():
    print(f"Method Execution Overview: \n")

    # Create a ManagerContext
    manager_context = ManagerContext(contexts={"multiprocessing": MultiProcessingContext()}, select="multiprocessing")

    # Create a proxy object
    proxy = manager_context.create_proxy(cls=ExampleClass, args=(2,), kwargs={"secret": -1})

    # Proxy Calls #
    pid = proxy.running_pid()
    public_result = proxy.multiply(2)  # Is public
    private_result = hasattr(proxy, "_unavailable")  # Is private
    exposed_call_result = proxy._available()  # Name in exposed list
    unexposed_call_result = hasattr(proxy, "unavailable")  # Name in unexposed list

    # Print Results
    print(f"Proxy Calls:")
    print(f"Different Processes: {pid} != {getpid()}")
    print(f"Public Call: {public_result} == 4.0")
    print(f"Private Call: {private_result} == False")
    print(f"Exposed Call: {exposed_call_result} == available")
    print(f"Unexposed Call: {unexposed_call_result} == False")
    print(f"")

    # Create Local #
    not_proxy = ExampleClass(2, secret=-1)

    # Local Calls #
    pid = not_proxy.running_pid()
    public_result = not_proxy.multiply(2)  # Is public
    private_result = hasattr(not_proxy, "_unavailable")  # Is private
    exposed_call_result = not_proxy._available()  # Name in exposed list
    unexposed_call_result = hasattr(not_proxy, "unavailable")  # Name in unexposed list

    # Print Results
    print(f"Local Calls:")
    print(f"Same Processes: {pid} == {getpid()}")
    print(f"Public Call: {public_result} == 4.0")
    print(f"Private Call: {private_result} == True")
    print(f"Exposed Call: {exposed_call_result} == available")
    print(f"Unexposed Call: {unexposed_call_result} == True")
    print(f"")


# Main #
if __name__ == "__main__":
    # Set Default Process Context
    method_execution_overview()

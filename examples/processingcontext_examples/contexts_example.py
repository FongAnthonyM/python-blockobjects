#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""contexts_example.py
An example of how to use the processing contexts.

"""

# Header #
__package_name__ = "blockobjects"

__author__ = "Anthony Fong"
__credits__ = ["Anthony Fong"]
__copyright__ = "Copyright 2022, Anthony Fong"
__license__ = "MIT"

__version__ = "0.1.0"


# Imports #
# Third-Party Packages #
from blockobjects.process import ManagerContext, AsyncContext, MultiProcessingContext
from blockobjects.process import ContextualQueue


# Definitions #
# Functions #
def contexts():
    print("Contexts")

    # Create a MultiProcessingContext to showcase contexts
    multiprocessing_context = MultiProcessingContext()

    # Contexts return several multiprocessing primitive object types which have their own implementations
    # Each context can list which objects it can spawn
    context_object_categories = multiprocessing_context.object_categories
    print(f"Context Objects: {context_object_categories}")

    # Also any objects that are spawned by the context have a weak reference tracked within the context
    print(f"Object Register :{multiprocessing_context.object_register}")

    # Create a queue object
    spawned_queue = multiprocessing_context.create_queue()
    print(f"Queue Type Spawned: {type(spawned_queue).__name__}")

    # View the object register
    print(f"Object Register: {tuple(multiprocessing_context.object_register['queues'].items())}")

    # Delete the queue object and it will not be in the object register
    del spawned_queue
    print(f"Object Register After Deletion: {tuple(multiprocessing_context.object_register['queues'].items())}")

    # Contextual Objects can be provided a context when created to define which context they are using
    new_queue = ContextualQueue(context=multiprocessing_context)
    print(f"ContextualQueue Inner Type: {type(new_queue.queue).__name__}")

    print("")


def manager_contexts():
    print("Manager Contexts")

    # Create a ManagerContext
    # It can be created without any arguments, but arguments can be provided to load some contexts
    manager_context = ManagerContext(contexts={"async": AsyncContext()}, select="async")

    # Contexts are stored in the contexts attribute as a dictionary
    print(f"Initial Contexts: {tuple(manager_context.contexts.keys())}")

    # New contexts can be added by assigning them to the contexts attribute
    manager_context.contexts["multiprocessing"] = MultiProcessingContext()
    print(f"Contexts: {tuple(manager_context.contexts.keys())}")

    # Selecting a context is done by calling the select_context method with the name of the context
    manager_context.select_context("multiprocessing")
    print(f"New Selected Context: {manager_context.selected}")

    print(f"\nSpawned Contextual Objects")
    # The ManagerContext can be used to create Contextual Objects
    spawned_queue = manager_context.create_queue()
    print(f"Queue Type Spawned: {type(spawned_queue).__name__}")

    # Given that the queue is a ContextualQueue, we can check which queue it is arbitrating to
    inner_queue = spawned_queue.queue
    print(f"Queue Arbitrating to: {type(inner_queue).__name__}")

    # Alternatively, when a Contextual Object is created, it can be provided a context
    new_queue = ContextualQueue(context=manager_context)
    print(f"New ContextualQueue: {new_queue.context is manager_context}")
    # This does mean that Contextual Objects will arbitrate to another Contextual Object
    print(f"ContextualQueue Inner Type: {type(new_queue.queue).__name__}")
    print(f"ContextualQueue Inner Inner Type: {type(new_queue.queue.queue).__name__}")
    # This can be useful for creating layers of contexts for dynamically creating conditions for specific contexts

    print("")


def default_context():
    print("Default Context")

    # The DEFAULT_PROCESS_CONTEXT is the default context which all Contextual Objects use if not provided a context
    # It is a ManagerContext all concepts from the ManagerContext apply to the DEFAULT_PROCESS_CONTEXT
    # It can be imported from directly from the processcontext module
    from blockobjects.process import DEFAULT_PROCESS_CONTEXT

    # The DEFAULT_PROCESS_CONTEXT has "async" and "multiprocessing" contexts available but may have more if more were
    # added during importing
    print(f"Default Available Contexts: {tuple(DEFAULT_PROCESS_CONTEXT.contexts.keys())}")

    # "async" is selected by default.
    # It does not provide true multiprocessing capabilities but allows emulating multiprocessing in a single process
    print(f"Default Selected Context: {DEFAULT_PROCESS_CONTEXT.selected}")

    print(f"\nDefault Contextual Objects")
    # If a Contextual Object is created without a context, it will use the DEFAULT_PROCESS_CONTEXT
    new_queue = ContextualQueue()
    print(f"New ContextualQueue is Using Default: {new_queue.context is DEFAULT_PROCESS_CONTEXT}")

    print("")


# Main #
if __name__ == "__main__":
    contexts()
    manager_contexts()
    default_context()

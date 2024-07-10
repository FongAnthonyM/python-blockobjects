from blockobjects.process import ProcessDelegate, DEFAULT_PROCESS_CONTEXT


class Printer(ProcessDelegate):
    def print(self, a: int) -> None:
        print(a, end=" ")


class Fibonacci(ProcessDelegate):
    def __init__(self, printer=None, **kwargs):
        self.printer = printer
        super().__init__(**kwargs)

    def sequence(self, n) -> None:
        if n >= 0:
            previous_number = 0
            next_number = 1

            self.printer.print(0)  # Runs in a separate process
            for _ in range(n):
                self.printer.print(next_number)  # Runs in a separate process
                previous_number, next_number = next_number, previous_number + next_number


# Main #
if __name__ == "__main__":
    # Set Default Process Context
    DEFAULT_PROCESS_CONTEXT.select_context("multiprocessing")

    # Create Actors
    printer = Printer()
    fibonacci = Fibonacci(printer)

    # Start Actors
    printer.start_server()
    fibonacci.start_server()

    # Execute Method (Pass Message)
    fibonacci.sequence(10)  # Evaluates is a separate process

    # Stop Actors
    printer.stop_server()
    fibonacci.stop_server()

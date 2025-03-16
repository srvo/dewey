from prefect import flow


@flow(log_prints=True)
def hello() -> None:
    pass


if __name__ == "__main__":
    hello.serve(name="hello-flow")

from trainwatch import monitor


def train_model(epochs: int = 3) -> None:
    for epoch in range(1, epochs + 1):
        # Dummy metrics for illustration.
        loss = 0.5 / epoch
        val_acc = 0.8 + (epoch * 0.02)
        monitor.log(epoch=epoch, loss=loss, val_acc=val_acc)


if __name__ == "__main__":
    # Either set TRAINWATCH_CONFIG to point to your config file
    # or pass config directly to monitor.end()/monitor.fail().
    monitor.start()
    try:
        train_model(epochs=5)
        monitor.end()
    except Exception as exc:
        monitor.fail(exc)
        raise

import time

from trainwatch import add_email, monitor


# One-time cloud setup (run once, then comment out):
# add_email("you@example.com")


def train_model(epochs: int = 3) -> None:
    for epoch in range(1, epochs + 1):
        time.sleep(1)
        loss = 0.6 / epoch
        val_acc = 0.75 + (epoch * 0.03)
        monitor.log(epoch=epoch, loss=loss, val_acc=val_acc)
        monitor.step(notify_every=2, message=f"Epoch {epoch} completed")


if __name__ == "__main__":
    monitor.start()
    monitor.heartbeat(interval_seconds=60, message="Training still running")
    try:
        train_model(epochs=5)
        monitor.end()
    except Exception as exc:
        monitor.fail(exc)
        raise

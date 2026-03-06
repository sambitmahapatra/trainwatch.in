from trainwatcher import add_email

# If you self-host, set TRAINWATCHER_BASE_URL to your Worker URL.
# Example:
#   export TRAINWATCHER_BASE_URL="https://your-worker.workers.dev"

if __name__ == "__main__":
    add_email("you@example.com")

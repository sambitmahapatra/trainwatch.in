from trainwatch import add_email

# Ensure TRAINWATCH_BASE_URL is set to your Cloudflare Worker URL.
# Example:
#   export TRAINWATCH_BASE_URL="https://your-worker.workers.dev"

if __name__ == "__main__":
    add_email("you@example.com")

# Security

- Never commit `.env` or `.streamlit/secrets.toml`.
- Keep `LSE_API_KEY` on the Python backend only.
- Never expose the LSE key through `NEXT_PUBLIC_*`, browser JavaScript, logs, or API responses.
- The browser connects only to the FastAPI HTTP and WebSocket endpoints.
- This project is a market-data monitor. It has no order execution or broker connection.

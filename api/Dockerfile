FROM python:3.12-slim

# PyMuPDF needs these; keeping the layer small matters for cold starts.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e . || pip install --no-cache-dir \
    fastapi uvicorn[standard] "psycopg[binary,pool]" pydantic python-multipart pyjwt pymupdf

COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

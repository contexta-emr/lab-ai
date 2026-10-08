FROM python:3.12-slim

# Native libs for the imaging stack; keeping the layer small matters for cold starts.
# (These predate the PyMuPDF removal and are left in place deliberately - opencv, via
# the OCR stack, wants libgl1. Removing them is a separate, testable change.)
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
# [dev] as well as the runtime deps. This image backs a local compose stack, and
# api/tests/ held fifteen test files with no pytest in the environment to run
# them - a suite that cannot run where the code runs is not a suite.
RUN pip install --no-cache-dir -e ".[dev]" || pip install --no-cache-dir \
    fastapi uvicorn[standard] "psycopg[binary,pool]" pydantic python-multipart pyjwt \
    pytest httpx ruff

COPY app ./app
COPY tests ./tests
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

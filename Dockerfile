# 98138.world web app (feature 008). Two stages:
#   build:   install the CLI library, fetch the pinned datasets, prebuild every map variant
#   runtime: FastAPI/uvicorn only (no NumPy/SciPy/scikit-image/ReportLab), serves the files as a
#            non-root user on port 8080.
# Python 3.11: the CLI pins scikit-image 0.21, which has wheels only for Python <= 3.11.
# Not affiliated with or endorsed by The LEGO Group.
ARG PYTHON_IMAGE=python:3.11.18-slim-bookworm

FROM ${PYTHON_IMAGE} AS build
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LEGO_IMAGE_PROCESSOR_CACHE=/tmp/dataset-cache
WORKDIR /src
# Pinned (hashed) dependencies of the CLI library first, for layer caching.
COPY web/requirements-build.txt web/requirements-build.txt
RUN pip install --require-hashes -r web/requirements-build.txt
COPY cli/ cli/
COPY web/ web/
RUN pip install --no-deps ./cli \
 && pip wheel --no-deps --wheel-dir /wheels ./web \
 && pip install --no-deps /wheels/*.whl
# Optional: record the source commit in the manifest (fly deploy --build-arg GIT_COMMIT=...).
ARG GIT_COMMIT=""
ENV GIT_COMMIT=${GIT_COMMIT}
# Downloads the four pinned public datasets (~10.8 MB, SHA-256 verified), then builds
# 6 maps x 5 combinations A-E (~185 MB, ~75 s, peak ~400 MB RAM on the builder).
RUN python -m web98138.prebuild --fetch --out /site

FROM ${PYTHON_IMAGE} AS runtime
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WEB98138_SITE_DIR=/site
COPY web/requirements.txt /tmp/requirements.txt
RUN pip install --require-hashes -r /tmp/requirements.txt && rm /tmp/requirements.txt
COPY --from=build /wheels /tmp/wheels
RUN pip install --no-deps /tmp/wheels/*.whl && rm -rf /tmp/wheels \
 && useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app
# Read-only to the app user (owned by root).
COPY --from=build /site /site
USER 10001
EXPOSE 8080
CMD ["uvicorn", "web98138.app:app", "--host", "0.0.0.0", "--port", "8080", \
     "--proxy-headers", "--forwarded-allow-ips", "*", "--no-server-header", "--no-access-log"]

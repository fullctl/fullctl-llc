FROM python:3.12.0a1-alpine as base

ARG virtual_env=/venv
ARG install_to=/srv/service
ARG build_deps=" \
    postgresql-dev \
    g++ \
    git \
    libffi-dev \
    libjpeg-turbo-dev \
    linux-headers \
    make \
    openssl-dev \
    curl \
    rust \
    cargo \
    "
ARG run_deps=" \
    libgcc \
    postgresql-libs \
    "
# env to pass to sub images
ENV RUN_DEPS=$run_deps
ENV SERVICE_HOME=$install_to
ENV VIRTUAL_ENV=$virtual_env
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV POETRY_VERSION=1.1.13

# build container
FROM base as builder

RUN apk upgrade --nocache --available && apk --no-cache add $build_deps

# Use Pip to install Poetry
RUN pip install "poetry==$POETRY_VERSION"

# Create a VENV
RUN python3 -m venv "$VIRTUAL_ENV"

WORKDIR /build

# individual files here instead of COPY . . for caching
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

# Need to upgrade pip and wheel within Poetry for all its installs
RUN poetry run pip install --upgrade pip wheel
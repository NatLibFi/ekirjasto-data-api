
ARG PYTHON_VERSION=3.11.17
ARG PIP_VERSION=26.2.2
ARG SETUPTOOLS_VERSION=84.2.1

FROM python:${PYTHON_VERSION}-slim-bookworm AS requirements-stage
ARG PIP_VERSION
ARG SETUPTOOLS_VERSION
ARG POETRY_VERSION=2.5.1
ARG POETRY_PLUGIN_EXPORT_VERSION=1.10.0
WORKDIR /tmp
RUN pip install --no-cache-dir --upgrade \
    "pip==${PIP_VERSION}" \
    "setuptools==${SETUPTOOLS_VERSION}" \
    "poetry==${POETRY_VERSION}" \
    "poetry-plugin-export==${POETRY_PLUGIN_EXPORT_VERSION}"
COPY ./pyproject.toml ./poetry.lock* /tmp/
RUN poetry export --only main -f requirements.txt --output requirements.txt --without-hashes

FROM python:${PYTHON_VERSION}-slim-bookworm
ARG PIP_VERSION
ARG SETUPTOOLS_VERSION
WORKDIR /code
COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade \
    "pip==${PIP_VERSION}" \
    "setuptools==${SETUPTOOLS_VERSION}" \
    && pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY . /code
EXPOSE 80

CMD ["uvicorn", "main:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "80"]

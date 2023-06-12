FROM python:3.9.2-buster
LABEL name=housing-data-ingest

RUN useradd -m vaccine && mkdir housing-data-ingest && chown vaccine:vaccine housing-data-ingest

COPY ./ /housing-data-ingest/

USER vaccine

WORKDIR /housing-data-ingest

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
ENV PATH "/home/vaccine/.poetry/bin:$PATH"
RUN /home/vaccine/.poetry/bin/poetry config virtualenvs.create false && \
    /home/vaccine/.poetry/bin/poetry install --extras lint --no-interaction --no-ansi

CMD ["bash"]

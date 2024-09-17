FROM python:3.9.2-buster
LABEL name=event-data-ingest

RUN useradd -m scraper && mkdir event-data-ingest && chown scraper:scraper event-data-ingest

COPY ./ /event-data-ingest/

USER scraper

WORKDIR /event-data-ingest

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN curl -sSL https://install.python-poetry.org/ | python -
ENV PATH "/home/vaccine/.poetry/bin:$PATH"
RUN /home/vaccine/.poetry/bin/poetry config virtualenvs.create false && \
    /home/vaccine/.poetry/bin/poetry install --extras lint --no-interaction --no-ansi

CMD ["bash"]

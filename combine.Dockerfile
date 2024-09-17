FROM alpine

# RUN echo '@community http://dl-cdn.alpinelinux.org/alpine/edge/community' >> /etc/apk/repositories && \
# 	echo '@edge http://dl-cdn.alpinelinux.org/alpine/edge/main' >> /etc/apk/repositories && \
# 	apk add --upgrade --no-cache --update ca-certificates curl gcc musl-dev libffi-dev g++

# find out -type f -mtime -1 -exec ls -lt {} + | grep "normalized" | awk '{print $NF}' 2> /dev/null |xargs cat > "$(date +'%Y-%m-%d')_concatenated_events.parsed.normalized.ndjson"


# TODO: automate the copying of the normalized output from the output dir to the dir that is being watched in the API

# Then create a composefile to run this and the main scraper dockerfile together

ARG CRON_SCHEDULE="*/10 * * * *"
RUN echo "$(crontab -l 2>&1; echo "${CRON_SCHEDULE} /root/.local/bin/poetry run event-data-ingest all-stages")" | crontab -

CMD ["crond", "-f", "2>&1"]

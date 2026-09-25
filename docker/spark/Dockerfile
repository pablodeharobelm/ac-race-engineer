FROM apache/spark:4.2.0-java21-python3

USER root

COPY docker/spark/requirements.txt /tmp/ac-race-requirements.txt

RUN python3 -m pip install \
    --no-cache-dir \
    -r /tmp/ac-race-requirements.txt

USER spark
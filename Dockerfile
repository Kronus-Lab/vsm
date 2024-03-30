FROM cgr.dev/chainguard/python:latest-dev as builder
WORKDIR /app
COPY requirements .
RUN pip install -r requirements --user

FROM cgr.dev/chainguard/python:latest
WORKDIR /app
COPY --from=builder /home/nonroot/.local/lib/python3.12/site-packages /home/nonroot/.local/lib/python3.12/site-packages
COPY static/ static/
COPY templates/ templates/
COPY vsm.py .
COPY LICENSE .

ENTRYPOINT [ "python", "vsm.py" ]

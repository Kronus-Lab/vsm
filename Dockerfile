FROM cgr.dev/chainguard/python:latest-dev AS builder
WORKDIR /app
COPY requirements.txt .
COPY config/vsm/app.json .
RUN pip install -r requirements.txt --user

FROM cgr.dev/chainguard/python:latest
WORKDIR /app
COPY --from=builder /home/nonroot/.local/lib/python3.13/site-packages /home/nonroot/.local/lib/python3.13/site-packages
COPY static/ static/
COPY templates/ templates/
COPY vsm.py .
COPY LICENSE .

ENTRYPOINT [ "python", "vsm.py" ]
